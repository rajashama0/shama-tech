# Shama Tech Backend

Server-only Python backend for the Shama Tech website.

This backend uses Apache CGI, Python, and MySQL. It does not use Flask, FastAPI, React, a frontend app, Lovable backend, Lovable storage, or Lovable auth.

## Architecture

```text
server/cgi-bin/api
  -> server/apis/cgi.py
  -> server/apis/api/api_method_name.py
  -> server/apis/tools/db_table.py
  -> MySQL through server/apis/tools/sql.py
```

Repository shape:

```text
server/
  config.py
  .env.example
  cgi-bin/
    api
    p
    p4web.py
  apis/
    cgi.py
    api/
      api_*.py
    tools/
      sql.py
      kicapi.py
      db_*.py
deploy/
  install_ec2.sh
  apache-shama-tech.conf.example
scripts/
  test_local_cgi.sh
  test_ec2_health.sh
tables.sql
lovable_ai_info.txt
requirements.txt
tests/
```

## Environment

Copy the example file and edit real values:

```bash
cp server/.env.example server/.env
```

Required settings:

```env
SYS_MODE=dev
SYS_ROOT=/var/www/shama-tech-backend
SYS_URL=https://shama-tech.com

DB_HOST=localhost
DB_USER=sql
DB_PASSWORD=rajasql
DB_NAME=shama_tech

FRONTEND_ORIGINS=http://localhost:3000,http://localhost:5173,https://shama-tech.com,https://www.shama-tech.com
ADMIN_API_KEY=change_me_to_a_long_random_value
CONTACT_MESSAGE_MAX=2000
```

`server/.env` is ignored by Git. Production secrets must exist only in `server/.env`.

In `SYS_MODE=prod`, `server/config.py` fails clearly if required production secrets are missing or still set to placeholder/local values.

## Database

The database schema is in:

```text
tables.sql
```

It creates and uses:

```text
shama_tech
```

Tables:

- `services`
- `case_studies`
- `contact_submissions`

Import manually:

```bash
mysql -u sql -p < tables.sql
```

The schema is idempotent where reasonable and seeds the services table with web apps, websites, dashboards, MVP/SaaS, backend/API work, AI consulting, AI workflow automation, internal tools, extraction, chatbot integrations, and CRM/ERP automation.

## API Contract

All API calls are `POST` requests:

```text
POST /cgi-bin/api?meth=METHOD_NAME
```

Request body:

```json
{
  "info": {
    "ses": "",
    "uses": "",
    "os": "lovable"
  },
  "input": {}
}
```

Success response:

```json
{
  "server": {
    "method": "api_health",
    "allow": 1,
    "success": true,
    "data": {},
    "server_ver": "shama-tech.1"
  }
}
```

Error response:

```json
{
  "server": {
    "method": "api_contact_add",
    "allow": 0,
    "success": false,
    "error": {
      "code": "validation_error",
      "message": "email is invalid",
      "field": "email"
    },
    "server_ver": "shama-tech.1"
  }
}
```

## Public API Methods

- `api_health`
- `api_services`
- `api_case_studies`
- `api_case_study_get`
- `api_contact_add`

Example:

```bash
curl -X POST "http://localhost/cgi-bin/api?meth=api_health" \
  -H "Content-Type: application/json" \
  -d '{"info":{"ses":"","uses":"","os":"curl"},"input":{}}'
```

Contact example:

```bash
curl -X POST "http://localhost/cgi-bin/api?meth=api_contact_add" \
  -H "Content-Type: application/json" \
  -d '{"info":{"ses":"","uses":"","os":"curl"},"input":{"full_name":"Jane Lead","company_name":"","email":"jane@example.com","phone":"","service_interest":"AI workflow automation","budget_range":"Not sure yet","message":"I want to automate our intake process.","source_page":"/contact"}}'
```

Required contact fields:

- `full_name`
- `email`
- `service_interest`
- `message`

`company_name` is optional to reduce form friction for early leads.

## Admin API Methods

Admin calls require:

```text
X-Admin-Token: ADMIN_API_KEY value
```

Methods:

- `api_admin_contact_list`
- `api_admin_contact_status`
- `api_admin_case_add`
- `api_admin_case_update`
- `api_admin_case_delete`

Allowed contact statuses:

- `new`
- `reviewed`
- `contacted`
- `closed`
- `spam`

Admin example:

```bash
curl -X POST "http://localhost/cgi-bin/api?meth=api_admin_contact_status" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: change_me_to_a_long_random_value" \
  -d '{"info":{"ses":"","uses":"","os":"curl"},"input":{"id":12,"status":"contacted"}}'
```

## EC2 Deployment

Run from the repository root on Ubuntu EC2:

```bash
bash deploy/install_ec2.sh
```

The installer:

- Installs Apache, CGI support, Python 3, pip, MySQL server/client, and Python requirements.
- Copies the backend to `/var/www/shama-tech-backend`.
- Creates `server/.env` from `server/.env.example` if missing.
- Creates the MySQL database and user from `.env`.
- Imports `tables.sql`.
- Makes `server/cgi-bin/api` executable.
- Installs and enables the Apache site config.
- Restarts Apache.
- Prints health-test curl commands.

Apache config example:

```text
deploy/apache-shama-tech.conf.example
```

Required CGI mapping:

```apache
ScriptAlias /cgi-bin/ /var/www/shama-tech-backend/server/cgi-bin/

<Directory "/var/www/shama-tech-backend/server/cgi-bin">
    Options +ExecCGI
    AddHandler cgi-script .py .cgi
    Require all granted
</Directory>
```

## Tests

Run unit tests:

```bash
python -m unittest discover -s tests
```

Run syntax check:

```bash
python -m compileall server tests
```

Local Apache health check after deployment:

```bash
bash scripts/test_local_cgi.sh
```

Domain health check:

```bash
BASE_URL=https://shama-tech.com bash scripts/test_ec2_health.sh
```

## Separate Frontend Contract

The separate frontend project only needs the API contract. See:

```text
lovable_ai_info.txt
```

That file documents how the separate frontend should call this backend. It is not frontend implementation.
