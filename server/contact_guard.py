"""
Server-side protection for the ShamaTech contact endpoint (``/cgi-bin/api?meth=api_contact_add``).

Drop-in module for the existing CGI backend. Call :func:`guard_contact_request` at the very start of the
``api_contact_add`` handler — before the submission is stored or any email is sent. It:

1. counts the attempt against the client's IP (max 3 attempts per rolling 60 minutes) and rejects the
   4th with HTTP 429 + ``Retry-After``;
2. rejects submissions that filled the hidden honeypot field;
3. validates and normalises every field.

Rate-limit state lives in SQLite: ``BEGIN IMMEDIATE`` serialises writers across concurrent CGI processes,
the data survives restarts, and only HMAC-hashed client keys are stored (never raw IP addresses), purged
once they leave the window. Standard library only; Python 3.8+.

See README.md in this directory for the exact integration steps and configuration.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass, field as dataclass_field
from typing import IO, Callable, Dict, Mapping, Optional, Sequence, Tuple, Union

LIMIT = 3
WINDOW_SECONDS = 3600
MAX_BODY_BYTES = 16 * 1024
DEFAULT_DB_PATH = "/var/lib/shamatech/contact-rate-limit.sqlite3"
ALLOWED_ORIGINS = ("https://shama-tech.com", "https://www.shama-tech.com")

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]

# --------------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------------
# Read from the process environment (Apache: SetEnv). Request headers reach CGI only as HTTP_* variables,
# so a client cannot set any of these names.


@dataclass(frozen=True)
class Settings:
    db_path: str
    secret: bytes
    limit: int = LIMIT
    window: int = WINDOW_SECONDS
    trusted_proxies: Tuple[IPNetwork, ...] = ()


def load_settings(environ: Mapping[str, str] = os.environ) -> Settings:
    db_path = environ.get("SHAMATECH_RATE_LIMIT_DB") or DEFAULT_DB_PATH
    window = WINDOW_SECONDS
    # A shorter window exists only for automated tests and requires an explicit test switch.
    if environ.get("SHAMATECH_RATE_LIMIT_TEST_MODE") == "1" and environ.get("SHAMATECH_RATE_LIMIT_WINDOW_SECONDS"):
        window = max(1, int(environ["SHAMATECH_RATE_LIMIT_WINDOW_SECONDS"]))
    return Settings(
        db_path=db_path,
        secret=_load_secret(environ, db_path),
        window=window,
        trusted_proxies=_parse_networks(environ.get("SHAMATECH_TRUSTED_PROXIES", "")),
    )


def _parse_networks(value: str) -> Tuple[IPNetwork, ...]:
    return tuple(ipaddress.ip_network(part.strip(), strict=False) for part in value.split(",") if part.strip())


def _load_secret(environ: Mapping[str, str], db_path: str) -> bytes:
    """HMAC key for client identifiers: env var, else a key file created once with mode 0600."""
    value = environ.get("SHAMATECH_RATE_LIMIT_SECRET", "")
    if value:
        return value.encode("utf-8")
    path = environ.get("SHAMATECH_RATE_LIMIT_SECRET_FILE") or os.path.join(os.path.dirname(db_path), "contact-rate-limit.key")
    for _ in range(50):
        try:
            with open(path, "rb") as fh:
                data = fh.read().strip()
            if len(data) >= 32:
                return data
        except FileNotFoundError:
            os.makedirs(os.path.dirname(path) or ".", mode=0o700, exist_ok=True)
            tmp = "%s.%d.tmp" % (path, os.getpid())
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(os.urandom(32).hex().encode("ascii"))
            try:
                os.link(tmp, path)  # atomic publish; fails if another process won the race
            except FileExistsError:
                pass
            finally:
                os.unlink(tmp)
            continue
        time.sleep(0.01)  # another process is mid-write
    raise RuntimeError("rate-limit secret unavailable: %s" % path)


# --------------------------------------------------------------------------------------------------
# Client identification
# --------------------------------------------------------------------------------------------------


def _in_networks(addr: IPAddress, networks: Sequence[IPNetwork]) -> bool:
    return any(addr in net for net in networks)


def client_ip(environ: Mapping[str, str], trusted_proxies: Sequence[IPNetwork] = ()) -> Optional[str]:
    """
    The connecting peer (REMOTE_ADDR, set by Apache from the TCP connection).

    X-Forwarded-For is ignored unless REMOTE_ADDR is a configured trusted proxy; then the right-most
    address that is not itself a trusted proxy is used (entries further left are client-supplied).
    """
    try:
        peer = ipaddress.ip_address((environ.get("REMOTE_ADDR") or "").strip())
    except ValueError:
        return None
    if trusted_proxies and _in_networks(peer, trusted_proxies):
        chain = [p.strip() for p in environ.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        for candidate in reversed(chain):
            try:
                addr = ipaddress.ip_address(candidate)
            except ValueError:
                break
            if not _in_networks(addr, trusted_proxies):
                return str(addr)
    return str(peer)


def normalize_ip(ip: str) -> str:
    """IPv4 as-is; IPv4-mapped IPv6 as IPv4; other IPv6 grouped by /64 (one subscriber's prefix)."""
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped:
            return str(addr.ipv4_mapped)
        return str(ipaddress.ip_network("%s/64" % addr, strict=False))
    return str(addr)


def client_key(ip: Optional[str], secret: bytes) -> str:
    """Pseudonymous, non-reversible identifier stored instead of the IP address."""
    material = normalize_ip(ip) if ip else "unknown"
    return hmac.new(secret, material.encode("ascii"), hashlib.sha256).hexdigest()[:32]


# --------------------------------------------------------------------------------------------------
# Rate limiter
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0
    remaining: int = 0


class RateLimiter:
    """Rolling-window limiter: at most ``limit`` attempts per key in any ``window`` seconds."""

    def __init__(self, db_path: str, limit: int = LIMIT, window: int = WINDOW_SECONDS, clock: Callable[[], float] = time.time):
        self.db_path = db_path
        self.limit = limit
        self.window = window
        self.clock = clock

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, mode=0o700, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 15000")
        for attempt in range(20):  # first-time setup can race with another process
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = FULL")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS contact_attempts ("
                    " client_key TEXT NOT NULL,"
                    " attempted_at REAL NOT NULL)"
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_key_time ON contact_attempts (client_key, attempted_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_time ON contact_attempts (attempted_at)")
                return conn
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc) or attempt == 19:
                    conn.close()
                    raise
                time.sleep(0.05)
        raise sqlite3.OperationalError("could not initialise rate-limit store")

    def hit(self, key: str) -> Decision:
        """Atomically check the window and, if under the limit, record this attempt."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")  # write lock held until COMMIT: no two workers interleave here
            try:
                now = self.clock()
                cutoff = now - self.window
                conn.execute("DELETE FROM contact_attempts WHERE attempted_at <= ?", (cutoff,))
                count, oldest = conn.execute(
                    "SELECT COUNT(*), MIN(attempted_at) FROM contact_attempts WHERE client_key = ? AND attempted_at > ?",
                    (key, cutoff),
                ).fetchone()
                if count >= self.limit:
                    conn.execute("COMMIT")
                    return Decision(False, retry_after=max(1, math.ceil(oldest + self.window - now)))
                conn.execute("INSERT INTO contact_attempts (client_key, attempted_at) VALUES (?, ?)", (key, now))
                conn.execute("COMMIT")
                return Decision(True, remaining=self.limit - count - 1)
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()


# --------------------------------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------------------------------

# name: (required, max length). Matches the fields the website sends.
FIELDS: Dict[str, Tuple[bool, int]] = {
    "full_name": (True, 120),
    "email": (True, 255),
    "company_name": (False, 160),
    "phone": (False, 40),
    "service_interest": (True, 120),
    "budget_range": (False, 60),
    "message": (True, 2000),
    "source_page": (False, 200),
}
HONEYPOT_FIELD = "website"

_CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f‪-‮⁦-⁩]")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_PHONE = re.compile(r"^[0-9+()\-.\s]{3,40}$")


def clean_text(value: str, multiline: bool = False) -> str:
    text = _CONTROL.sub("", unicodedata.normalize("NFC", value))
    if multiline:
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = re.sub(r"\s+", " ", text)
    return text.strip()


def validate_contact(data: object) -> Tuple[Dict[str, str], Optional[Tuple[Optional[str], str]]]:
    """Returns (clean fields, None) or ({}, (field or None, safe message))."""
    if not isinstance(data, dict):
        return {}, (None, "Invalid request.")
    clean: Dict[str, str] = {}
    for name, (required, max_len) in FIELDS.items():
        raw = data.get(name)
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            return {}, (name, "Invalid value.")
        value = clean_text(raw, multiline=(name == "message"))
        if len(value) > max_len:
            return {}, (name, "Value is too long.")
        if required and not value:
            return {}, (name, "This field is required.")
        clean[name] = value
    if not _EMAIL.match(clean["email"]):
        return {}, ("email", "Invalid email address.")
    if clean["phone"] and not _PHONE.match(clean["phone"]):
        return {}, ("phone", "Invalid phone number.")
    if clean["source_page"] and not clean["source_page"].startswith("/"):
        clean["source_page"] = ""
    return clean, None


# --------------------------------------------------------------------------------------------------
# Guard + responses
# --------------------------------------------------------------------------------------------------


@dataclass
class Rejection:
    status: int
    reason: str
    code: str
    message: str
    field: Optional[str] = None
    headers: Dict[str, str] = dataclass_field(default_factory=dict)

    def envelope(self, method: str = "api_contact_add") -> dict:
        error = {"code": self.code, "message": self.message}
        if self.field:
            error["field"] = self.field
        return {"server": {"method": method, "allow": 1, "success": False, "error": error}}


def guard_contact_request(
    environ: Mapping[str, str],
    input_data: object,
    settings: Optional[Settings] = None,
    limiter: Optional[RateLimiter] = None,
) -> Tuple[Optional[Rejection], Dict[str, str]]:
    """
    Run before handling api_contact_add. Returns (rejection, {}) to stop, or (None, clean_fields) to proceed.
    Every call counts as an attempt — including invalid ones — so the limit cannot be probed for free.
    """
    try:
        settings = settings or load_settings(environ)
        limiter = limiter or RateLimiter(settings.db_path, settings.limit, settings.window)
        decision = limiter.hit(client_key(client_ip(environ, settings.trusted_proxies), settings.secret))
    except (sqlite3.Error, OSError, RuntimeError):
        # Fail closed: without a working limiter nothing is accepted (and nothing is emailed).
        return Rejection(503, "Service Unavailable", "unavailable", "The service is temporarily unavailable. Please try again later."), {}
    if not decision.allowed:
        return (
            Rejection(
                429,
                "Too Many Requests",
                "rate_limited",
                "Too many requests. Please try again later.",
                headers={"Retry-After": str(decision.retry_after)},
            ),
            {},
        )
    if isinstance(input_data, dict) and str(input_data.get(HONEYPOT_FIELD) or "").strip():
        return Rejection(400, "Bad Request", "rejected", "The request could not be processed."), {}
    clean, error = validate_contact(input_data)
    if error:
        field_name, message = error
        return Rejection(400, "Bad Request", "validation_error", message, field=field_name), {}
    return None, clean


def read_json_body(environ: Mapping[str, str], stream: IO[bytes], max_bytes: int = MAX_BODY_BYTES) -> object:
    """Parsed JSON body, or None if it is missing, too large or malformed (never raises)."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return None
    if length <= 0 or length > max_bytes:
        return None
    try:
        return json.loads(stream.read(length).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def cors_headers(environ: Mapping[str, str]) -> Dict[str, str]:
    origin = environ.get("HTTP_ORIGIN", "")
    if origin in ALLOWED_ORIGINS:
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin", "Access-Control-Expose-Headers": "Retry-After"}
    return {}


def write_cgi_response(stream: IO[bytes], status: int, reason: str, body: dict, headers: Optional[Dict[str, str]] = None) -> None:
    """Write a CGI response as UTF-8 bytes (pass sys.stdout.buffer: no locale or newline translation)."""
    lines = ["Status: %d %s" % (status, reason), "Content-Type: application/json; charset=utf-8", "Cache-Control: no-store"]
    lines += ["%s: %s" % (k, v) for k, v in (headers or {}).items()]
    stream.write(("\r\n".join(lines) + "\r\n\r\n" + json.dumps(body, ensure_ascii=False)).encode("utf-8"))
    stream.flush()


def write_rejection(stream: IO[bytes], rejection: Rejection, environ: Mapping[str, str]) -> None:
    write_cgi_response(stream, rejection.status, rejection.reason, rejection.envelope(), {**cors_headers(environ), **rejection.headers})


if __name__ == "__main__":  # `python contact_guard.py init` creates the store and key ahead of time
    import sys

    if sys.argv[1:] == ["init"]:
        s = load_settings()
        RateLimiter(s.db_path)._connect().close()
        print("rate-limit store ready at %s" % s.db_path)
