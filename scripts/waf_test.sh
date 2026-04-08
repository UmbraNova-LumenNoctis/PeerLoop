#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== WAF & Security quick tests =="

DOCKER_COMPOSE="docker compose"

echo "Starting required services (nginx + api-gateway)..."
$DOCKER_COMPOSE up -d --build nginx api-gateway

echo "Waiting for API gateway to be healthy (timeout 60s)..."
for i in {1..30}; do
  if curl -ksS https://localhost:8443/health --insecure >/dev/null 2>&1; then
    echo "API Gateway reachable via Nginx HTTPS"
    break
  fi
  sleep 2
done

echo
echo "-- benign tests --"
echo "HTTP (should redirect to HTTPS):"
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/ || true

echo "HTTPS /health (should return 200):"
curl -sk -o /dev/null -w "HTTP %{http_code}\n" https://localhost:8443/health || true

echo
echo "-- malicious payload tests --"
FAIL=0

test_payload(){
  local name="$1"; shift
  local url="$1"; shift
  local probe_pattern="$1"; shift || true
  echo "Testing $name -> $url"
  code=$(curl -sk -o /tmp/waf_test_resp.txt -w "%{http_code}" "$url" || true)
  body=$(cat /tmp/waf_test_resp.txt || true)
  echo "  HTTP code: $code"

  # Check nginx logs for ModSecurity detection of the probe pattern
  logs=$(docker logs peerloop_nginx --tail 300 || true)
  if echo "$logs" | grep -F "$probe_pattern" >/dev/null 2>&1; then
    echo "  => DETECTED by ModSecurity (log evidence found)"
  else
    if [ "$code" = "200" ]; then
      echo "  => ALLOWED (no detection in logs)"
      FAIL=1
    else
      echo "  => BLOCKED or redirected (no explicit ModSecurity log match)"
    fi
  fi
}

# SQL injection like pattern
test_payload "SQLi (query)" "https://localhost:8443/?id=1'%20OR%20'1'='1" "1' OR '1'='1"

# XSS-like pattern
test_payload "XSS (query)" "https://localhost:8443/?q=<script>alert(1)</script>" "<script>alert(1)</script>"

# Typical remote file inclusion / rfi attempt
test_payload "RFI (path)" "https://localhost:8443/%3Cscript%3Ealert(1)%3C/script%3E" "<script>alert(1)</script>"

echo
echo "-- Nginx / ModSecurity logs (last 100 lines) --"
docker logs peerloop_nginx --tail 100 || true

if [ "$FAIL" -ne 0 ]; then
  echo "\nWAF tests detected ALLOWED malicious payload(s)." >&2
  exit 2
fi

echo "\nAll WAF checks passed (malicious payloads were blocked or not allowed)."
exit 0
