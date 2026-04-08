#!/bin/sh
# =============================================================================
# Grafana Vault entrypoint wrapper
#
# Grafana is a pre-built binary — it cannot call Vault itself.
# This script bridges the gap:
#   1. Calls the Vault HTTPS API with curl (no vault CLI needed)
#   2. Exports GF_SECURITY_ADMIN_USER and GF_SECURITY_ADMIN_PASSWORD
#   3. Hands off to the original Grafana entrypoint
#
# If Vault is unreachable, the values already set via docker-compose
# environment: blocks are used as fallback (GF_SECURITY_ADMIN_USER, etc.)
# =============================================================================

set -e

VAULT_ADDR="${VAULT_ADDR:-https://vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN}"
VAULT_PATH="secret/data/grafana"

echo "[grafana-entrypoint] Fetching credentials from Vault ($VAULT_ADDR)..."

# Call Vault KV-v2 API — use -k to skip TLS verify (dev-tls self-signed cert)
VAULT_RESPONSE=$(curl -sfk \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    "${VAULT_ADDR}/v1/${VAULT_PATH}" 2>/dev/null) || VAULT_RESPONSE=""

if [ -n "$VAULT_RESPONSE" ]; then
    # Parse JSON with sed/awk (no jq dependency)
    GRAFANA_ADMIN_USER=$(echo "$VAULT_RESPONSE" \
        | grep -o '"GRAFANA_ADMIN_USER":"[^"]*"' \
        | sed 's/"GRAFANA_ADMIN_USER":"//;s/"$//')

    GRAFANA_ADMIN_PASSWORD=$(echo "$VAULT_RESPONSE" \
        | grep -o '"GRAFANA_ADMIN_PASSWORD":"[^"]*"' \
        | sed 's/"GRAFANA_ADMIN_PASSWORD":"//;s/"$//')

    if [ -n "$GRAFANA_ADMIN_USER" ]; then
        export GF_SECURITY_ADMIN_USER="$GRAFANA_ADMIN_USER"
        echo "[grafana-entrypoint] GF_SECURITY_ADMIN_USER loaded from Vault."
    fi

    if [ -n "$GRAFANA_ADMIN_PASSWORD" ]; then
        export GF_SECURITY_ADMIN_PASSWORD="$GRAFANA_ADMIN_PASSWORD"
        echo "[grafana-entrypoint] GF_SECURITY_ADMIN_PASSWORD loaded from Vault."
    fi
else
    echo "[grafana-entrypoint] WARNING: Vault unreachable — using fallback env vars."
fi

# Hand off to the original Grafana entrypoint
exec /run.sh "$@"
