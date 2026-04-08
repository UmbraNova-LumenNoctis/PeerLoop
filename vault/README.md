# Vault

## Role
Central secrets service. Runs Vault in dev mode with TLS, seeds secrets from `secrets.env`, and exposes them to services via `shared_schemas/vault_client.py`.

## Public access
- UI proxied: `https://localhost:8443/services/vault/ui/`
- Direct API: `https://localhost:8200`

## Runtime behavior
- Starts from the custom image in `vault/`.
- Custom entrypoint runs `vault server -dev-tls`.
- Persistence volume: `vault_data` at `/vault/file`.
- Auto-seeds secrets at boot when `secret/app` is not initialized.

## Secret paths actually used
- `secret/supabase`
- `secret/google-oauth`
- `secret/app`
- `secret/imagekit`
- `secret/llm`

## Secret paths seeded by bootstrap
- `secret/grafana`

## Useful commands
- `make logs-vault`
- `make init-vault`
- `make vault-push-secrets`
- `make vault-list-secrets`
- `make vault-verify`
- `make unseal-vault`

## Important notes
- The runtime uses `-dev-tls`, so Vault is HTTPS only.
- Services read Vault KV v2 and inject values into environment variables.
- `secret/grafana` is seeded but the current Grafana runtime uses env values if Vault is unavailable.
- Dev mode is not suitable for production deployments.
