# Prometheus

## Role
Metrics collection service. Scrapes `/metrics` endpoints for microservices defined in `prometheus/prometheus.yml`, plus host and container metrics.

## Scraped jobs
- `prometheus`
- `api-gateway`
- `auth-service`
- `file-service`
- `users-service`
- `friendship-service`
- `post-service`
- `notification-service`
- `chat-service`
- `llm-service`
- `node-exporter`
- `cadvisor`

## Important note
- The current runtime does not scrape `search_service`.

## Alert rules
Loaded from `prometheus/alerts.yml`.

## Public access
- `https://localhost:8443/services/prometheus/`
- Health endpoint: `https://localhost:8443/services/prometheus/-/healthy`

## Implementation notes
- TSDB retention is set to `30d` in the compose file.
- The service is served behind Nginx under `/services/prometheus`.
- Environment labels are set statically to `production` for scraped targets.
