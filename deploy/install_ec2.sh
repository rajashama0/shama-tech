#!/usr/bin/env bash
set -euo pipefail

backend_root="${BACKEND_ROOT:-/var/www/shama-tech-backend}"
site_conf="/etc/apache2/sites-available/shama-tech-backend.conf"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing system packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  apache2 \
  mysql-server \
  mysql-client \
  python3 \
  python3-pip \
  rsync

echo "Installing Python requirements"
if python3 -m pip install --help | grep -q -- "--break-system-packages"; then
  sudo python3 -m pip install --break-system-packages -r "$repo_root/requirements.txt"
else
  sudo python3 -m pip install -r "$repo_root/requirements.txt"
fi

echo "Preparing backend directory: $backend_root"
sudo mkdir -p "$backend_root"
sudo rsync -a --delete \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude ".pytest_cache" \
  "$repo_root/" "$backend_root/"

if [ ! -f "$backend_root/server/.env" ]; then
  sudo cp "$backend_root/server/.env.example" "$backend_root/server/.env"
  echo "Created $backend_root/server/.env from .env.example"
fi

sudo chown -R www-data:www-data "$backend_root"
sudo chmod 750 "$backend_root/server"
sudo chmod 640 "$backend_root/server/.env"
sudo chmod +x "$backend_root/server/cgi-bin/api"
sudo chmod +x "$backend_root/server/cgi-bin/p"

echo "Loading environment"
set -a
# shellcheck disable=SC1091
source "$backend_root/server/.env"
set +a

echo "Configuring MySQL database and user"
sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

sudo mysql < "$backend_root/tables.sql"

echo "Configuring Apache"
sudo a2enmod cgi
sudo cp "$backend_root/deploy/apache-shama-tech.conf.example" "$site_conf"
sudo a2ensite shama-tech-backend.conf
sudo apache2ctl configtest
sudo systemctl restart apache2

echo "Install complete"
echo "Health test from the EC2 instance:"
echo "curl -X POST http://localhost/cgi-bin/api?meth=api_health -H 'Content-Type: application/json' -d '{\"info\":{\"ses\":\"\",\"uses\":\"\",\"os\":\"curl\"},\"input\":{}}'"
echo ""
echo "Health test through domain after DNS/CloudFront is ready:"
echo "curl -X POST ${SYS_URL}/cgi-bin/api?meth=api_health -H 'Content-Type: application/json' -d '{\"info\":{\"ses\":\"\",\"uses\":\"\",\"os\":\"curl\"},\"input\":{}}'"
