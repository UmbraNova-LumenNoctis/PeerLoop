# Grafana

## Role
Prometheus metrics visualization UI. Served behind Nginx under a subpath and auto-provisioned with a datasource and dashboards.

## Public access
- `https://localhost:8443/services/grafana/`

## Credentials
- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`

## Provisioning
- Datasource: `grafana/provisioning/datasources/prometheus.yml`
- Dashboard provider: `grafana/provisioning/dashboards/dashboard.yml`
- Versioned dashboards: `grafana/provisioning/dashboards/api-gateway.json`, `grafana/provisioning/dashboards/infrastructure.json`

## Security settings
- Anonymous access disabled
- User self-signup disabled
- Embedding disabled
- Root URL fixed to `/services/grafana/`

## Implementation notes
- `docker-compose.yml` builds the image from `grafana/Dockerfile`.
- `entrypoint.sh` calls Vault over HTTPS to load `GF_SECURITY_ADMIN_USER` and `GF_SECURITY_ADMIN_PASSWORD` from `secret/grafana`.
- If Vault is unavailable, existing container environment variables are used.
- The provisioned datasource points to `http://prometheus:9090` on the Docker network.
