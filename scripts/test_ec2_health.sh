#!/usr/bin/env bash
set -euo pipefail

base_url="${BASE_URL:-https://shama-tech.com}"

curl -sS -X POST "$base_url/cgi-bin/api?meth=api_health" \
  -H "Content-Type: application/json" \
  -d '{"info":{"ses":"","uses":"","os":"script"},"input":{}}'

echo ""
