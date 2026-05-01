#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Shama-Tech Backend: Dev-to-Prod Promotion Script
# ============================================================
#
# What it does:
# 1. Tests backend in the current/dev folder
# 2. Copies backend to production path
# 3. Creates/updates production .env safely
# 4. Installs system dependencies
# 5. Creates production Python venv
# 6. Configures MySQL database/user/schema
# 7. Configures Apache CGI
# 8. Tests health/services/contact/admin endpoints
# 9. Installs SSL automatically with Certbot
# 10. Tests HTTPS health endpoint
#
# SSL is enabled by default.
#
# Before running, make sure:
# 1. shama-tech.com points to this EC2 Elastic IP
# 2. www.shama-tech.com points to this EC2 Elastic IP
# 3. AWS Security Group allows inbound 80 and 443
#
# Usage:
#   cd /root/shama-tech
#   sudo bash deploy/promote_to_prod.sh
#
# Optional:
#   sudo DOMAIN=shama-tech.com bash deploy/promote_to_prod.sh
#   sudo DEV_DIR=/root/shama-tech PROD_DIR=/var/www/shama-tech-backend DOMAIN=shama-tech.com bash deploy/promote_to_prod.sh
#
# Emergency/debug only, skip SSL:
#   sudo ENABLE_SSL=0 bash deploy/promote_to_prod.sh
#
# ============================================================

DEV_DIR="${DEV_DIR:-$(pwd)}"
PROD_DIR="${PROD_DIR:-/var/www/shama-tech-backend}"

DOMAIN="${DOMAIN:-shama-tech.com}"
WWW_DOMAIN="${WWW_DOMAIN:-www.${DOMAIN}}"

DB_NAME="${DB_NAME:-shama_tech}"
DB_USER="${DB_USER:-sql}"
DB_HOST="${DB_HOST:-localhost}"

APACHE_SITE_NAME="${APACHE_SITE_NAME:-shama-tech-backend}"
APACHE_CONF="/etc/apache2/sites-available/${APACHE_SITE_NAME}.conf"

RUN_WRITE_TEST="${RUN_WRITE_TEST:-1}"
ENABLE_SSL="${ENABLE_SSL:-1}"

SERVER_DIR="${PROD_DIR}/server"
ENV_FILE="${SERVER_DIR}/.env"
CGI_ENTRYPOINT="${SERVER_DIR}/cgi-bin/api"
VENV_DIR="${PROD_DIR}/.venv"

DB_PASSWORD=""
ADMIN_API_KEY=""

log() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

fail() {
  echo
  echo "ERROR: $1" >&2
  exit 1
}

show_logs_on_failure() {
  echo
  echo "Deployment failed. Last Apache logs:"
  echo

  tail -n 100 /var/log/apache2/shama-tech-backend-error.log 2>/dev/null || true

  echo

  tail -n 100 /var/log/apache2/error.log 2>/dev/null || true
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "Run this script with sudo/root: sudo bash deploy/promote_to_prod.sh"
  fi
}

check_dev_dir() {
  log "Checking dev directory"

  [[ -d "${DEV_DIR}" ]] || fail "DEV_DIR does not exist: ${DEV_DIR}"
  [[ -d "${DEV_DIR}/server" ]] || fail "Missing server/ in ${DEV_DIR}"
  [[ -f "${DEV_DIR}/requirements.txt" ]] || fail "Missing requirements.txt in ${DEV_DIR}"
  [[ -f "${DEV_DIR}/tables.sql" ]] || fail "Missing tables.sql in ${DEV_DIR}"
  [[ -f "${DEV_DIR}/server/cgi-bin/api" ]] || fail "Missing server/cgi-bin/api in ${DEV_DIR}"

  cd "${DEV_DIR}"

  echo "DEV_DIR=${DEV_DIR}"
  echo "PROD_DIR=${PROD_DIR}"
  echo "DOMAIN=${DOMAIN}"
  echo "WWW_DOMAIN=${WWW_DOMAIN}"
}

install_system_dependencies() {
  log "Installing system dependencies"

  apt update

  apt install -y \
    apache2 \
    mysql-server \
    python3 \
    python3-pip \
    python3-full \
    curl \
    rsync \
    openssl \
    dnsutils \
    certbot \
    python3-certbot-apache

  apt install -y python3-venv || true

  PY_MINOR="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  apt install -y "python${PY_MINOR}-venv" || true

  python3 -m venv /tmp/shama_venv_test || fail "Python venv unavailable. Install python3-venv manually."
  rm -rf /tmp/shama_venv_test

  systemctl enable apache2
  systemctl enable mysql
  systemctl start mysql
}

test_dev_code() {
  log "Testing backend code in dev directory"

  cd "${DEV_DIR}"

  rm -rf .venv
  python3 -m venv .venv

  # shellcheck disable=SC1091
  source .venv/bin/activate

  pip install --upgrade pip
  pip install -r requirements.txt

  python -m unittest discover -s tests

  python - <<'PY'
import ast
import pathlib

for p in pathlib.Path(".").rglob("*.py"):
    sp = str(p)
    if ".venv" in sp or "__pycache__" in sp:
        continue
    ast.parse(p.read_text(encoding="utf-8"))

print("syntax ok")
PY

  deactivate
}

backup_existing_prod_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "${ENV_FILE}" "${BACKUP_FILE}"
    chmod 600 "${BACKUP_FILE}" || true
    echo "Backed up existing production env to: ${BACKUP_FILE}"
  fi
}

sync_to_prod() {
  log "Syncing dev code to production directory"

  mkdir -p "${PROD_DIR}"

  backup_existing_prod_env

  rsync -a --delete \
    --exclude ".git/" \
    --exclude ".venv/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude ".pytest_cache/" \
    --exclude "server/.env" \
    "${DEV_DIR}/" "${PROD_DIR}/"

  mkdir -p "${SERVER_DIR}"

  chown -R root:www-data "${PROD_DIR}"
  chmod -R 750 "${PROD_DIR}"

  if [[ -f "${CGI_ENTRYPOINT}" ]]; then
    chmod +x "${CGI_ENTRYPOINT}"
  else
    fail "CGI entrypoint missing after sync: ${CGI_ENTRYPOINT}"
  fi
}

get_env_value() {
  local key="$1"
  local file="$2"

  if [[ -f "${file}" ]]; then
    grep -E "^${key}=" "${file}" | tail -n 1 | cut -d '=' -f2- || true
  fi
}

create_or_update_env() {
  log "Creating/updating production .env"

  local existing_db_password
  local existing_admin_key

  existing_db_password="$(get_env_value "DB_PASSWORD" "${ENV_FILE}")"
  existing_admin_key="$(get_env_value "ADMIN_API_KEY" "${ENV_FILE}")"

  DB_PASSWORD="${DB_PASSWORD:-${existing_db_password:-}}"
  ADMIN_API_KEY="${ADMIN_API_KEY:-${existing_admin_key:-}}"

  if [[ -z "${DB_PASSWORD}" || "${DB_PASSWORD}" == "CHANGE_THIS_TO_REAL_PASSWORD" || "${DB_PASSWORD}" == "rajasql" ]]; then
    DB_PASSWORD="$(openssl rand -base64 32 | tr -d '\n')"
  fi

  if [[ -z "${ADMIN_API_KEY}" || "${ADMIN_API_KEY}" == "CHANGE_THIS_TO_REAL_ADMIN_KEY" || "${ADMIN_API_KEY}" == "change_me_to_a_long_random_value" ]]; then
    ADMIN_API_KEY="$(openssl rand -hex 32 | tr -d '\n')"
  fi

  cat > "${ENV_FILE}" <<EOF
SYS_MODE=prod
SYS_ROOT=${PROD_DIR}
SYS_URL=https://${DOMAIN}

DB_HOST=${DB_HOST}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}

FRONTEND_ORIGINS=https://${DOMAIN},https://${WWW_DOMAIN},http://localhost:3000,http://localhost:5173
ADMIN_API_KEY=${ADMIN_API_KEY}
CONTACT_MESSAGE_MAX=2000
EOF

  chown root:www-data "${ENV_FILE}"
  chmod 640 "${ENV_FILE}"

  echo "Production .env is ready at: ${ENV_FILE}"
  echo "Secrets were generated or preserved. They were not printed."
}

create_prod_venv() {
  log "Creating production Python virtual environment"

  cd "${PROD_DIR}"

  rm -rf "${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"

  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"

  pip install --upgrade pip
  pip install -r requirements.txt

  python -m unittest discover -s tests

  deactivate

  chown -R root:www-data "${VENV_DIR}"
  chmod -R 750 "${VENV_DIR}"
}

patch_cgi_shebang() {
  log "Patching CGI shebang to use production venv"

  local shebang="#!${VENV_DIR}/bin/python"

  python3 - "${CGI_ENTRYPOINT}" "${shebang}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
shebang = sys.argv[2]

text = path.read_text(encoding="utf-8")
lines = text.splitlines()

if lines and lines[0].startswith("#!"):
    lines[0] = shebang
else:
    lines.insert(0, shebang)

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

  chmod +x "${CGI_ENTRYPOINT}"
  chown root:www-data "${CGI_ENTRYPOINT}"

  echo "CGI shebang:"
  head -n 1 "${CGI_ENTRYPOINT}"
}

configure_mysql() {
  log "Configuring MySQL database/user/schema"

  systemctl start mysql

  mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';

ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';

GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';

FLUSH PRIVILEGES;
SQL

  cd "${PROD_DIR}"

  mysql -u "${DB_USER}" -p"${DB_PASSWORD}" < tables.sql

  mysql -u "${DB_USER}" -p"${DB_PASSWORD}" -e "USE \`${DB_NAME}\`; SHOW TABLES;"
  mysql -u "${DB_USER}" -p"${DB_PASSWORD}" -e "USE \`${DB_NAME}\`; SELECT COUNT(*) AS services_count FROM services;" || true
}

configure_apache() {
  log "Configuring Apache CGI site"

  a2enmod cgi
  a2enmod ssl
  a2enmod rewrite
  a2enmod headers

  cat > "${APACHE_CONF}" <<EOF
<VirtualHost *:80>
    ServerName ${DOMAIN}
    ServerAlias ${WWW_DOMAIN}

    ServerAdmin webmaster@localhost

    DocumentRoot ${PROD_DIR}

    ScriptAlias /cgi-bin/ ${SERVER_DIR}/cgi-bin/

    <Directory "${SERVER_DIR}/cgi-bin">
        Options +ExecCGI
        AddHandler cgi-script .cgi .py
        Require all granted
    </Directory>

    <Directory "${PROD_DIR}">
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/shama-tech-backend-error.log
    CustomLog \${APACHE_LOG_DIR}/shama-tech-backend-access.log combined
</VirtualHost>
EOF

  a2dissite 000-default.conf >/dev/null 2>&1 || true
  a2ensite "${APACHE_SITE_NAME}.conf"

  apache2ctl configtest
  systemctl restart apache2
  systemctl status apache2 --no-pager || true
}

test_apache_health() {
  log "Testing Apache CGI health endpoint over HTTP localhost"

  curl -i -X POST "http://localhost/cgi-bin/api?meth=api_health" \
    -H "Content-Type: application/json" \
    --data '{"info":{"ses":"","uses":"","os":"lovable"},"input":{}}' \
    | tee /tmp/shama_health_response.txt

  grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/shama_health_response.txt \
    || fail "api_health did not return success=true"
}

test_apache_services() {
  log "Testing DB-backed services endpoint"

  curl -i -X POST "http://localhost/cgi-bin/api?meth=api_services" \
    -H "Content-Type: application/json" \
    --data '{"info":{"ses":"","uses":"","os":"lovable"},"input":{}}' \
    | tee /tmp/shama_services_response.txt

  grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/shama_services_response.txt \
    || fail "api_services did not return success=true"
}

test_contact_insert() {
  if [[ "${RUN_WRITE_TEST}" != "1" ]]; then
    echo "Skipping write test because RUN_WRITE_TEST=${RUN_WRITE_TEST}"
    return
  fi

  log "Testing contact insert endpoint"

  curl -i -X POST "http://localhost/cgi-bin/api?meth=api_contact_add" \
    -H "Content-Type: application/json" \
    --data '{
      "info":{"ses":"","uses":"","os":"lovable"},
      "input":{
        "full_name":"Backend Smoke Test",
        "company_name":"Shama Tech",
        "email":"test@example.com",
        "phone":"",
        "service_interest":"AI workflow automation",
        "budget_range":"Not sure yet",
        "message":"Automated production smoke test.",
        "source_page":"/backend-smoke-test"
      }
    }' \
    | tee /tmp/shama_contact_response.txt

  grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/shama_contact_response.txt \
    || fail "api_contact_add did not return success=true"

  mysql -u "${DB_USER}" -p"${DB_PASSWORD}" -e "USE \`${DB_NAME}\`; SELECT id, full_name, email, service_interest, status, created_at FROM contact_submissions ORDER BY id DESC LIMIT 5;"
}

test_admin_protection() {
  log "Testing admin protection"

  curl -i -X POST "http://localhost/cgi-bin/api?meth=api_admin_contact_list" \
    -H "Content-Type: application/json" \
    --data '{"info":{"ses":"","uses":"","os":"lovable"},"input":{}}' \
    | tee /tmp/shama_admin_reject_response.txt

  if grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/shama_admin_reject_response.txt; then
    fail "Admin endpoint succeeded without token. This is a security bug."
  fi

  curl -i -X POST "http://localhost/cgi-bin/api?meth=api_admin_contact_list" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Token: ${ADMIN_API_KEY}" \
    --data '{"info":{"ses":"","uses":"","os":"lovable"},"input":{}}' \
    | tee /tmp/shama_admin_success_response.txt

  grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/shama_admin_success_response.txt \
    || fail "Admin endpoint did not succeed with valid token"
}

check_dns_for_ssl() {
  log "Checking DNS before SSL"

  PUBLIC_IP="$(curl -s --max-time 8 http://checkip.amazonaws.com | tr -d '[:space:]' || true)"

  DOMAIN_IP="$(dig +short A "${DOMAIN}" | tail -n 1 | tr -d '[:space:]' || true)"
  WWW_DOMAIN_IP="$(dig +short A "${WWW_DOMAIN}" | tail -n 1 | tr -d '[:space:]' || true)"

  if [[ -z "${WWW_DOMAIN_IP}" ]]; then
    WWW_DOMAIN_IP="$(dig +short CNAME "${WWW_DOMAIN}" | tail -n 1 | sed 's/\.$//' | xargs -r dig +short A | tail -n 1 | tr -d '[:space:]' || true)"
  fi

  echo "EC2 public IP: ${PUBLIC_IP:-unknown}"
  echo "${DOMAIN} resolves to: ${DOMAIN_IP:-not resolved}"
  echo "${WWW_DOMAIN} resolves to: ${WWW_DOMAIN_IP:-not resolved}"

  if [[ -z "${PUBLIC_IP}" ]]; then
    fail "Could not detect EC2 public IP. Cannot safely issue SSL."
  fi

  if [[ "${DOMAIN_IP}" != "${PUBLIC_IP}" ]]; then
    fail "${DOMAIN} does not resolve to this EC2 public IP yet. Point DNS to ${PUBLIC_IP}, wait for propagation, then rerun."
  fi

  if [[ "${WWW_DOMAIN_IP}" != "${PUBLIC_IP}" ]]; then
    fail "${WWW_DOMAIN} does not resolve to this EC2 public IP yet. Point DNS to ${PUBLIC_IP}, wait for propagation, then rerun."
  fi
}

install_ssl() {
  if [[ "${ENABLE_SSL}" != "1" ]]; then
    echo "Skipping SSL because ENABLE_SSL=${ENABLE_SSL}"
    return
  fi

  check_dns_for_ssl

  log "Installing SSL certificate using Certbot"

  certbot --apache \
    -d "${DOMAIN}" \
    -d "${WWW_DOMAIN}" \
    --non-interactive \
    --agree-tos \
    -m "admin@${DOMAIN}" \
    --redirect

  systemctl reload apache2

  log "Testing HTTPS health endpoint"

  curl -i -X POST "https://${DOMAIN}/cgi-bin/api?meth=api_health" \
    -H "Content-Type: application/json" \
    --data '{"info":{"ses":"","uses":"","os":"lovable"},"input":{}}' \
    | tee /tmp/shama_https_health_response.txt

  grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/shama_https_health_response.txt \
    || fail "HTTPS api_health did not return success=true"
}

print_final_summary() {
  log "Production deployment complete"

  echo "Production path:"
  echo "  ${PROD_DIR}"
  echo
  echo "Apache config:"
  echo "  ${APACHE_CONF}"
  echo
  echo "Local backend health:"
  echo "  http://localhost/cgi-bin/api?meth=api_health"
  echo
  echo "Domain backend health:"
  echo "  https://${DOMAIN}/cgi-bin/api?meth=api_health"
  echo
  echo "Frontend/Lovable should call:"
  echo "  https://${DOMAIN}/cgi-bin/api?meth=api_services"
  echo "  https://${DOMAIN}/cgi-bin/api?meth=api_case_studies"
  echo "  https://${DOMAIN}/cgi-bin/api?meth=api_case_study_get"
  echo "  https://${DOMAIN}/cgi-bin/api?meth=api_contact_add"
  echo
  echo "Important files:"
  echo "  ${ENV_FILE}"
  echo "  ${CGI_ENTRYPOINT}"
  echo
  echo "Apache logs:"
  echo "  /var/log/apache2/shama-tech-backend-error.log"
  echo "  /var/log/apache2/shama-tech-backend-access.log"
  echo
  echo "Secrets were not printed."
  echo "To view variable names only:"
  echo "  cut -d= -f1 ${ENV_FILE}"
}

main() {
  trap show_logs_on_failure ERR

  require_root
  check_dev_dir
  install_system_dependencies
  test_dev_code
  sync_to_prod
  create_or_update_env
  create_prod_venv
  patch_cgi_shebang
  configure_mysql
  configure_apache
  test_apache_health
  test_apache_services
  test_contact_insert
  test_admin_protection
  install_ssl
  print_final_summary
}

main "$@"