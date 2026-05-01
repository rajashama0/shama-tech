import os
from pathlib import Path


server_dir = Path(__file__).resolve().parent
env_path = server_dir / ".env"


def load_env():
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def env_str(name, default=""):
    return os.environ.get(name, default).strip()


def env_int(name, default):
    val = env_str(name, str(default))
    try:
        return int(val)
    except ValueError:
        return int(default)


def env_list(name, default=""):
    val = env_str(name, default)
    if val == "":
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def resolve_root(value):
    if value == "":
        return str(server_dir.parent)
    p = Path(value)
    if p.is_absolute():
        return str(p)
    return str((server_dir.parent / p).resolve())


load_env()

SYS_MODE = env_str("SYS_MODE", "dev")
SYS_ROOT = resolve_root(env_str("SYS_ROOT", "/var/www/shama-tech-backend"))
SYS_URL = env_str("SYS_URL", "http://localhost")

DB_HOST = env_str("DB_HOST", "localhost")
DB_USER = env_str("DB_USER", "sql")
DB_PASSWORD = env_str("DB_PASSWORD", "")
DB_NAME = env_str("DB_NAME", "shama_tech")

FRONTEND_ORIGINS = env_list(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://localhost:5173,https://shama-tech.com,https://www.shama-tech.com",
)
ADMIN_API_KEY = env_str("ADMIN_API_KEY", "")
CONTACT_MESSAGE_MAX = env_int("CONTACT_MESSAGE_MAX", 2000)

# Compatibility aliases used by existing server helpers.
sys_mode = SYS_MODE
sys_root = SYS_ROOT
sys_url = SYS_URL
hostname = DB_HOST
username = DB_USER
password = DB_PASSWORD
database = DB_NAME
frontend_origins = FRONTEND_ORIGINS
admin_api_key = ADMIN_API_KEY
contact_message_max = CONTACT_MESSAGE_MAX


def check_prod_config():
    if SYS_MODE != "prod":
        return
    missing = []
    if DB_PASSWORD in ["", "rajasql", "change_me"]:
        missing.append("DB_PASSWORD")
    if ADMIN_API_KEY in ["", "change_me_to_a_long_random_value", "change_me"]:
        missing.append("ADMIN_API_KEY")
    if not FRONTEND_ORIGINS:
        missing.append("FRONTEND_ORIGINS")
    if SYS_URL in ["", "http://localhost", "localhost"]:
        missing.append("SYS_URL")
    if missing:
        raise RuntimeError("missing production config: " + ",".join(missing))


check_prod_config()
