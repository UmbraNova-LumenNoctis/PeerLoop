#!/bin/sh
# =============================================================================
# Vault custom entrypoint for peerloop
#
# Flow:
#   1. Start vault server -dev in the background
#   2. Wait until the HTTP API responds (ready)
#   3. Check if secrets are already seeded (idempotent via sentinel key)
#   4. If not seeded → source secrets.env and run init-vault.sh
#   5. Re-attach to the vault process so Docker tracks it (PID 1)
# =============================================================================

set -e

export VAULT_ADDR="https://127.0.0.1:8200"
export VAULT_TOKEN="${VAULT_TOKEN}"
export VAULT_SKIP_VERIFY=true

load_secrets_env() {
    path="$1"

    if [ -f "$path" ]; then
        echo "[vault-entrypoint] Loading secrets from $path ..."
        # shellcheck disable=SC1090
        . "$path"
        return 0
    fi

    if [ -d "$path" ]; then
        for candidate in "$path/secrets.env" "$path/.env"; do
            if [ -f "$candidate" ]; then
                echo "[vault-entrypoint] Loading secrets from $candidate ..."
                # shellcheck disable=SC1090
                . "$candidate"
                return 0
            fi
        done

        first_env=$(find "$path" -maxdepth 1 -type f -name "*.env" | head -n 1 || true)
        if [ -n "$first_env" ] && [ -f "$first_env" ]; then
            echo "[vault-entrypoint] Loading secrets from $first_env ..."
            # shellcheck disable=SC1090
            . "$first_env"
            return 0
        fi
    fi

    return 1
}

# ---------------------------------------------------------------------------
# 1. Start vault server in dev mode (background)
# ---------------------------------------------------------------------------
echo "[vault-entrypoint] Starting Vault server (dev mode)..."
mkdir -p /vault/tls
vault server \
    -dev-tls \
    -dev-root-token-id="${VAULT_TOKEN}" \
    -dev-tls-cert-dir="/vault/tls" \
    -dev-listen-address="0.0.0.0:8200" &

VAULT_PID=$!

# ---------------------------------------------------------------------------
# 2. Wait until Vault HTTP API is ready
# ---------------------------------------------------------------------------
echo "[vault-entrypoint] Waiting for Vault to be ready..."
for i in $(seq 1 30); do
    if curl -skf "${VAULT_ADDR}/v1/sys/health" >/dev/null 2>&1; then
        echo "[vault-entrypoint] Vault is ready (attempt $i)."
        break
    fi
    echo "[vault-entrypoint] Not ready yet (attempt $i/30), waiting 1s..."
    sleep 1
done

# ---------------------------------------------------------------------------
# 3. Check if secrets were already seeded (idempotent sentinel)
# ---------------------------------------------------------------------------
ALREADY_SEEDED=$(vault kv get -format=json secret/app 2>/dev/null \
    | grep -o '"GATEWAY_SECRET"' | wc -l | tr -d ' ')

if [ "$ALREADY_SEEDED" -gt 0 ]; then
    echo "[vault-entrypoint] Secrets already seeded — skipping init."
else
    # -----------------------------------------------------------------------
    # 4. Load secrets.env if available, then run init-vault.sh
    #    Priority: /vault/secrets.env (bind-mounted from host) > defaults
    # -----------------------------------------------------------------------
    if ! load_secrets_env /vault/secrets.env; then
        echo "[vault-entrypoint] WARNING: /vault/secrets.env not found — using PLACEHOLDER defaults."
        echo "[vault-entrypoint] Mount a file or directory with a secrets.env file to fix this:"
        echo "[vault-entrypoint]   volumes: - ./secrets.env:/vault/secrets.env:ro"
    fi

    echo "[vault-entrypoint] Seeding secrets into Vault..."
    sh /vault/scripts/init-vault.sh
    echo "[vault-entrypoint] Secrets seeded successfully."
fi

# ---------------------------------------------------------------------------
# 5. Re-attach to Vault so Docker tracks it as PID 1
# ---------------------------------------------------------------------------
echo "[vault-entrypoint] Vault is running (PID $VAULT_PID). Container ready."
wait "$VAULT_PID"
