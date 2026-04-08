#!/bin/sh
# =============================================================================
# Vault initialization + secrets bootstrap for peerloop
#
# This script:
#   1. Waits for Vault to be ready
#   2. Enables the KV-v2 secrets engine
#   3. Pushes all application secrets into Vault
#
# Secret values are read (in priority order) from:
#   a) Environment variables already exported in the shell
#   b) /run/secrets/secrets.env  (mounted file – preferred in prod)
#   c) /vault/secrets.env        (volume-mounted file – alternative)
#   d) Empty fallbacks            (no hardcoded credentials — sensitive values MUST come from secrets.env)
#
# Vault path layout:
#   secret/supabase      → SUPABASE_URL, SUPABASE_KEY
#   secret/google-oauth  → GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
#                          REDIRECT_URI, EMAIL_CONFIRM_REDIRECT_URL,
#                          POST_CONFIRM_APP_URL,
#                          GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK,
#                          GOOGLE_REDIRECT_URIS
#   secret/app           → GATEWAY_SECRET, INTERNAL_SERVICE_TOKEN, ENV,
#                          AUTH_COOKIE_SECURE, AUTH_COOKIE_SAMESITE,
#                          REFRESH_TOKEN_COOKIE_NAME, REFRESH_COOKIE_MAX_AGE,
#                          MAX_FILE_SIZE_MB, INTERNAL SERVICE URLS
#   secret/llm           → GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL,
#                          LLM_TIMEOUT_SECONDS, LLM_TEMPERATURE,
#                          LLM_MAX_OUTPUT_TOKENS, LLM_SYSTEM_PROMPT
#   secret/grafana       → GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD
# =============================================================================

set -e

echo "==================================="
echo "  peerloop – Vault Init"
echo "==================================="

# ---------------------------------------------------------------------------
# 1. Load secrets.env if it exists
# ---------------------------------------------------------------------------
load_secrets_env() {
    path="$1"

    if [ -f "$path" ]; then
        echo "Loading secrets from $path ..."
        # shellcheck disable=SC1090
        . "$path"
        return 0
    fi

    if [ -d "$path" ]; then
        for candidate in "$path/secrets.env" "$path/.env"; do
            if [ -f "$candidate" ]; then
                echo "Loading secrets from $candidate ..."
                # shellcheck disable=SC1090
                . "$candidate"
                return 0
            fi
        done

        first_env=$(find "$path" -maxdepth 1 -type f -name "*.env" | head -n 1 || true)
        if [ -n "$first_env" ] && [ -f "$first_env" ]; then
            echo "Loading secrets from $first_env ..."
            # shellcheck disable=SC1090
            . "$first_env"
            return 0
        fi
    fi

    return 1
}

load_secrets_env /run/secrets/secrets.env || load_secrets_env /vault/secrets.env || true

# ---------------------------------------------------------------------------
# 2. Defaults — sensitive values use empty fallback; non-sensitive config uses safe defaults.
#    All credentials MUST be provided via secrets.env (or pre-exported env vars).
# ---------------------------------------------------------------------------
SUPABASE_URL="${SUPABASE_URL:-}"
SUPABASE_KEY="${SUPABASE_KEY:-}"

GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
REDIRECT_URI="${REDIRECT_URI:-https://localhost:8443/auth/google/callback}"
GOOGLE_REDIRECT_URIS="${GOOGLE_REDIRECT_URIS:-https://localhost:8443/auth/google/callback,https://localhost:8443/api/auth/google/callback,https://localhost:8444/auth/google/callback,https://localhost:8444/api/auth/google/callback}"
EMAIL_CONFIRM_REDIRECT_URL="${EMAIL_CONFIRM_REDIRECT_URL:-https://localhost:8443/api/auth/email/confirm}"
POST_CONFIRM_APP_URL="${POST_CONFIRM_APP_URL:-https://localhost:8443}"
GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK="${GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK:-false}"
GOOGLE_OAUTH_AUTO_FALLBACK="${GOOGLE_OAUTH_AUTO_FALLBACK:-true}"
GOOGLE_REQUIRE_VERIFIED_EMAIL="${GOOGLE_REQUIRE_VERIFIED_EMAIL:-true}"
AUTH_STRICT_EMAIL_LINKING="${AUTH_STRICT_EMAIL_LINKING:-true}"

GATEWAY_SECRET="${GATEWAY_SECRET:-REPLACE_ME_gateway_secret_min_32_chars}"
INTERNAL_SERVICE_TOKEN="${INTERNAL_SERVICE_TOKEN:-REPLACE_ME_internal_service_token}"
ENV="${ENV:-production}"
AUTH_COOKIE_SECURE="${AUTH_COOKIE_SECURE:-true}"
AUTH_COOKIE_SAMESITE="${AUTH_COOKIE_SAMESITE:-none}"
REFRESH_TOKEN_COOKIE_NAME="${REFRESH_TOKEN_COOKIE_NAME:-ft_refresh_token}"
REFRESH_COOKIE_MAX_AGE="${REFRESH_COOKIE_MAX_AGE:-2592000}"
MAX_FILE_SIZE_MB="${MAX_FILE_SIZE_MB:-25}"
DEFAULT_AVATAR_URL="${DEFAULT_AVATAR_URL:-https://api.dicebear.com/9.x/identicon/svg?seed=peerloop}"
DEFAULT_COVER_URL="${DEFAULT_COVER_URL:-}"
ENVIRONMENT="${ENVIRONMENT:-production}"
INTERNAL_TLS_VERIFY="${INTERNAL_TLS_VERIFY:-false}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://nginx/_internal/auth_service}"
FILE_SERVICE_URL="${FILE_SERVICE_URL:-https://nginx/_internal/file_service}"
USER_SERVICE_URL="${USER_SERVICE_URL:-https://nginx/_internal/users_service}"
FRIENDSHIP_SERVICE_URL="${FRIENDSHIP_SERVICE_URL:-https://nginx/_internal/friendship_service}"
POST_SERVICE_URL="${POST_SERVICE_URL:-https://nginx/_internal/post_service}"
NOTIFICATION_SERVICE_URL="${NOTIFICATION_SERVICE_URL:-https://nginx/_internal/notification_service}"
CHAT_SERVICE_URL="${CHAT_SERVICE_URL:-https://nginx/_internal/chat_service}"
LLM_SERVICE_URL="${LLM_SERVICE_URL:-https://nginx/_internal/llm_service}"
SEARCH_SERVICE_URL="${SEARCH_SERVICE_URL:-https://nginx/_internal/search_service}"
CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-https://localhost:8443,https://127.0.0.1:8443,https://localhost:8444,https://127.0.0.1:8444,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173}"

GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash-lite}"
LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-30}"
LLM_TEMPERATURE="${LLM_TEMPERATURE:-0.7}"
LLM_MAX_OUTPUT_TOKENS="${LLM_MAX_OUTPUT_TOKENS:-512}"
GEMINI_BASE_URL="${GEMINI_BASE_URL:-https://generativelanguage.googleapis.com/v1beta}"
LLM_SYSTEM_PROMPT="${LLM_SYSTEM_PROMPT:-}"

IMAGEKIT_PRIVATE_KEY="${IMAGEKIT_PRIVATE_KEY:-}"
IMAGEKIT_PUBLIC_KEY="${IMAGEKIT_PUBLIC_KEY:-}"
IMAGEKIT_URL="${IMAGEKIT_URL:-}"

GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-}"
GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-}"

# ---------------------------------------------------------------------------
# 3. Wait for Vault to be ready
# ---------------------------------------------------------------------------
echo "Waiting for Vault to be ready..."
for i in $(seq 1 30); do
    if vault status >/dev/null 2>&1; then
        break
    fi
    echo "  attempt $i/30 – not ready yet, sleeping 2s..."
    sleep 2
done

# ---------------------------------------------------------------------------
# 4. Initialize Vault (only needed when NOT running in -dev mode)
#    In dev mode Vault is always initialized — this block is a no-op.
# ---------------------------------------------------------------------------
INIT_STATUS=$(vault status -format=json 2>/dev/null | grep -o '"initialized":[^,}]*' | grep -o '[a-z]*$' || echo "true")

if [ "$INIT_STATUS" = "false" ]; then
    echo "Initializing Vault..."
    vault operator init -key-shares=1 -key-threshold=1 > /tmp/vault-init.txt

    echo ""
    echo "==================================="
    echo "  IMPORTANT: Save these credentials!"
    echo "==================================="
    cat /tmp/vault-init.txt
    echo "==================================="
    echo ""

    UNSEAL_KEY=$(grep 'Unseal Key 1:' /tmp/vault-init.txt | awk '{print $NF}')
    ROOT_TOKEN=$(grep 'Initial Root Token:' /tmp/vault-init.txt | awk '{print $NF}')

    vault operator unseal "$UNSEAL_KEY"
    vault login "$ROOT_TOKEN"
    echo "Vault initialized and unsealed."
else
    echo "Vault already initialized (dev mode or previously initialized)."
fi

# ---------------------------------------------------------------------------
# 5. Enable KV-v2 secrets engine
# ---------------------------------------------------------------------------
echo "Enabling KV-v2 secrets engine at 'secret/'..."
vault secrets enable -path=secret kv-v2 2>/dev/null && echo "KV-v2 enabled." || echo "KV-v2 already enabled."

# ---------------------------------------------------------------------------
# 6. Push secrets
# ---------------------------------------------------------------------------
echo ""
echo "--- Writing secret/supabase ---"
vault kv put secret/supabase \
    SUPABASE_URL="$SUPABASE_URL" \
    SUPABASE_KEY="$SUPABASE_KEY"

echo "--- Writing secret/google-oauth ---"
vault kv put secret/google-oauth \
    GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
    GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
    REDIRECT_URI="$REDIRECT_URI" \
    GOOGLE_REDIRECT_URIS="$GOOGLE_REDIRECT_URIS" \
    EMAIL_CONFIRM_REDIRECT_URL="$EMAIL_CONFIRM_REDIRECT_URL" \
    POST_CONFIRM_APP_URL="$POST_CONFIRM_APP_URL" \
    GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK="$GOOGLE_OAUTH_ALLOW_SUPABASE_FALLBACK" \
    GOOGLE_OAUTH_AUTO_FALLBACK="$GOOGLE_OAUTH_AUTO_FALLBACK" \
    GOOGLE_REQUIRE_VERIFIED_EMAIL="$GOOGLE_REQUIRE_VERIFIED_EMAIL" \
    AUTH_STRICT_EMAIL_LINKING="$AUTH_STRICT_EMAIL_LINKING"

echo "--- Writing secret/app ---"
vault kv put secret/app \
    GATEWAY_SECRET="$GATEWAY_SECRET" \
    INTERNAL_SERVICE_TOKEN="$INTERNAL_SERVICE_TOKEN" \
    ENV="$ENV" \
    ENVIRONMENT="$ENVIRONMENT" \
    AUTH_COOKIE_SECURE="$AUTH_COOKIE_SECURE" \
    AUTH_COOKIE_SAMESITE="$AUTH_COOKIE_SAMESITE" \
    REFRESH_TOKEN_COOKIE_NAME="$REFRESH_TOKEN_COOKIE_NAME" \
    REFRESH_COOKIE_MAX_AGE="$REFRESH_COOKIE_MAX_AGE" \
    MAX_FILE_SIZE_MB="$MAX_FILE_SIZE_MB" \
    DEFAULT_AVATAR_URL="$DEFAULT_AVATAR_URL" \
    DEFAULT_COVER_URL="$DEFAULT_COVER_URL" \
    INTERNAL_TLS_VERIFY="$INTERNAL_TLS_VERIFY" \
    AUTH_SERVICE_URL="$AUTH_SERVICE_URL" \
    FILE_SERVICE_URL="$FILE_SERVICE_URL" \
    USER_SERVICE_URL="$USER_SERVICE_URL" \
    FRIENDSHIP_SERVICE_URL="$FRIENDSHIP_SERVICE_URL" \
    POST_SERVICE_URL="$POST_SERVICE_URL" \
    NOTIFICATION_SERVICE_URL="$NOTIFICATION_SERVICE_URL" \
    CHAT_SERVICE_URL="$CHAT_SERVICE_URL" \
    LLM_SERVICE_URL="$LLM_SERVICE_URL" \
    SEARCH_SERVICE_URL="$SEARCH_SERVICE_URL" \
    CORS_ALLOW_ORIGINS="$CORS_ALLOW_ORIGINS"

echo "--- Writing secret/imagekit ---"
vault kv put secret/imagekit \
    IMAGEKIT_PRIVATE_KEY="$IMAGEKIT_PRIVATE_KEY" \
    IMAGEKIT_PUBLIC_KEY="$IMAGEKIT_PUBLIC_KEY" \
    IMAGEKIT_URL="$IMAGEKIT_URL"

echo "--- Writing secret/llm ---"
vault kv put secret/llm \
    GEMINI_API_KEY="$GEMINI_API_KEY" \
    GEMINI_MODEL="$GEMINI_MODEL" \
    GEMINI_BASE_URL="$GEMINI_BASE_URL" \
    LLM_TIMEOUT_SECONDS="$LLM_TIMEOUT_SECONDS" \
    LLM_TEMPERATURE="$LLM_TEMPERATURE" \
    LLM_MAX_OUTPUT_TOKENS="$LLM_MAX_OUTPUT_TOKENS" \
    LLM_SYSTEM_PROMPT="$LLM_SYSTEM_PROMPT"

echo "--- Writing secret/grafana ---"
vault kv put secret/grafana \
    GRAFANA_ADMIN_USER="$GRAFANA_ADMIN_USER" \
    GRAFANA_ADMIN_PASSWORD="$GRAFANA_ADMIN_PASSWORD"

echo ""
echo "==================================="
echo "  Vault setup complete!"
echo "==================================="
echo ""
echo "  UI:    https://localhost:8443/services/vault/ui/"
echo "  Token: \$VAULT_TOKEN"
echo ""
echo "  Verify with:  vault kv get secret/supabase"
echo ""
