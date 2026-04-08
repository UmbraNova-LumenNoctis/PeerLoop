#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT_WEBHOOK=false

for arg in "$@"; do
  case "$arg" in
    --strict-webhook)
      STRICT_WEBHOOK=true
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--strict-webhook]"
      exit 1
      ;;
  esac
done

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "FAIL: docker compose (or docker-compose) is required."
  exit 1
fi

pass_count=0
warn_count=0
fail_count=0

pass() { echo "PASS: $*"; pass_count=$((pass_count + 1)); }
warn() { echo "WARN: $*"; warn_count=$((warn_count + 1)); }
fail() { echo "FAIL: $*"; fail_count=$((fail_count + 1)); }

echo "== n8n workflow verification =="

# 1) Service health through nginx
health_code="$(curl -sk -o /dev/null -w '%{http_code}' "https://localhost:8443/services/n8n/healthz" || true)"
if [ "$health_code" = "200" ]; then
  pass "n8n health endpoint reachable (HTTP 200)."
else
  fail "n8n health endpoint failed (HTTP $health_code)."
fi

# 2) n8n container and CLI access
if "${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.yml" ps --status running --services | awk '$1=="n8n"{found=1} END{exit !found}'; then
  pass "n8n container is running."
else
  fail "n8n container is not running."
fi

active_workflows="$("${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.yml" exec -T n8n n8n list:workflow --active=true 2>/dev/null || true)"
active_count="$(printf "%s\n" "$active_workflows" | awk 'NF{count++} END{print count+0}')"
if [ "$active_count" -ge 7 ]; then
  pass "active workflows detected ($active_count)."
else
  fail "expected at least 7 active workflows, got $active_count."
fi

# 3) Spot-check production webhook registration
req_id="verify-incident-$(date +%s)"
incident_response="$(curl -sk -X POST "https://localhost:8443/services/n8n/webhook/peers/incident-events" \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"verify-script\",\"eventType\":\"health_check\",\"severity\":\"high\",\"summary\":\"n8n verify run\",\"correlationId\":\"$req_id\"}" || true)"

if printf "%s" "$incident_response" | sed -n '1,1p' | grep -q '"webhook.*not registered"\|"not registered"'; then
  if [ "$STRICT_WEBHOOK" = true ]; then
    fail "incident webhook is not registered in production mode."
  else
    warn "incident webhook returned 'not registered' (use --strict-webhook to fail hard)."
  fi
else
  pass "incident webhook responded without 'not registered'."
fi

echo
echo "Summary: PASS=$pass_count WARN=$warn_count FAIL=$fail_count"

if [ "$fail_count" -gt 0 ]; then
  exit 1
fi

exit 0
