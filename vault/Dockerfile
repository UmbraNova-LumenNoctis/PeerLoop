FROM hashicorp/vault:latest AS vault-bin

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=vault-bin /bin/vault /usr/local/bin/vault
COPY --chmod=755 scripts/entrypoint.sh /vault/entrypoint.sh
COPY --chmod=755 scripts/init-vault.sh /vault/scripts/init-vault.sh

EXPOSE 8200

ENTRYPOINT ["/vault/entrypoint.sh"]
