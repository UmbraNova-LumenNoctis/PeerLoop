.PHONY: help up up-fg down restart logs clean rebuild status health urls check-env certs logs-n8n shell-n8n n8n-import-workflows verify-n8n verify-n8n-strict

# Load .env for variable substitution (git-ignored; copy from .env.example)
-include .env
export

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m
# No Color

# Docker Compose command: prefer the new `docker compose` plugin when available,
# fall back to the legacy `docker-compose` binary if needed.
DOCKER_COMPOSE := $(shell \
	if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then \
		echo "docker compose"; \
	elif command -v docker-compose >/dev/null 2>&1; then \
		echo "docker-compose"; \
	else \
		echo "docker compose"; \
	fi)

# Public URLs
FRONTEND_URL ?= https://localhost:8443
API_GATEWAY_URL ?= https://localhost:8444
API_DOCS_URL ?= $(API_GATEWAY_URL)/docs
API_OPENAPI_URL ?= $(API_GATEWAY_URL)/openapi.json
PROMETHEUS_URL ?= $(FRONTEND_URL)/services/prometheus/
GRAFANA_URL ?= $(FRONTEND_URL)/services/grafana/
VAULT_URL ?= $(FRONTEND_URL)/services/vault/
N8N_URL ?= $(FRONTEND_URL)/services/n8n/

help: ## Show this help message
	@echo "$(GREEN)peerloop - DevOps Infrastructure$(NC)"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

urls: ## Print configured public URLs
	@echo "$(GREEN)Configured URLs$(NC)"
	@echo "  - Frontend:    $(FRONTEND_URL)"
	@echo "  - API Gateway: $(API_GATEWAY_URL)"
	@echo "  - API Docs:    $(API_DOCS_URL)"
	@echo "  - OpenAPI:     $(API_OPENAPI_URL)"
	@echo "  - Grafana:     $(GRAFANA_URL)"
	@echo "  - Prometheus:  $(PROMETHEUS_URL)"
	@echo "  - Vault:       $(VAULT_URL)"
	@echo "  - n8n:         $(N8N_URL)"

check-env: ## Vérifie que .env et secrets.env existent avant de démarrer
	@if [ ! -f .env ]; then \
		echo "$(RED)Erreur : le fichier .env est introuvable.$(NC)"; \
		echo "Copiez .env.example et remplissez les valeurs :"; \
		echo "  cp .env.example .env"; \
		exit 1; \
	fi
	@if [ ! -f secrets.env ]; then \
		echo "$(RED)Erreur : le fichier secrets.env est introuvable.$(NC)"; \
		echo "Copiez secrets.env.example et remplissez les valeurs :"; \
		echo "  cp secrets.env.example secrets.env"; \
		exit 1; \
	fi
	@if [ ! -f frontend/.env ]; then \
		echo "$(RED)Erreur : le fichier frontend/.env est introuvable.$(NC)"; \
		echo "Copiez frontend/.env.example et remplissez les valeurs :"; \
		echo "  cp frontend/.env.example frontend/.env"; \
		exit 1; \
	fi

certs: ## Génère les certificats TLS auto-signés pour nginx si absents
	@if [ ! -f nginx/certs/localhost.crt ] || [ ! -f nginx/certs/localhost.key ]; then \
		echo "$(YELLOW)Génération des certificats TLS auto-signés...$(NC)"; \
		mkdir -p nginx/certs; \
		openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
			-keyout nginx/certs/localhost.key \
			-out nginx/certs/localhost.crt \
			-subj "/CN=localhost" \
			-addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null; \
		chmod 644 nginx/certs/localhost.key; \
		echo "$(GREEN)Certificats générés dans nginx/certs/$(NC)"; \
	else \
		echo "$(GREEN)Certificats TLS déjà présents.$(NC)"; \
	fi

up: check-env certs ## Start all services
	@echo "$(GREEN)Starting peerloop infrastructure...$(NC)"
	@echo "$(YELLOW)Building images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(YELLOW)Starting services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(YELLOW)Importing + activating n8n workflows...$(NC)"
	@bash scripts/import_n8n_workflows.sh --activate --restart
	@echo "$(GREEN)Services started successfully!$(NC)"
	@echo ""
	@echo "Access points:"
	@echo "  - Frontend:    $(FRONTEND_URL)"
	@echo "  - API Gateway: $(API_GATEWAY_URL)"
	@echo "  - API Docs:    $(API_DOCS_URL)"
	@echo "  - OpenAPI:     $(API_OPENAPI_URL)"
	@echo "  - Grafana:     $(GRAFANA_URL)"
	@echo "  - Prometheus:  $(PROMETHEUS_URL)"
	@echo "  - Vault:       $(VAULT_URL)"
	@echo "  - n8n:         $(N8N_URL)"

n8n-import-workflows: ## Import n8n workflows from n8n/workflows
	@bash scripts/import_n8n_workflows.sh

n8n-sync-workflows: ## Import + activate n8n workflows and restart n8n
	@bash scripts/import_n8n_workflows.sh --activate --restart

verify-n8n: ## Run n8n workflow verification checks
	@bash scripts/verify_n8n_workflows.sh

verify-n8n-strict: ## Run strict n8n verification (fail on webhook registration)
	@bash scripts/verify_n8n_workflows.sh --strict-webhook

up-fg: check-env certs ## Start all services in foreground (with logs)
	@echo "$(GREEN)Starting peerloop infrastructure in foreground...$(NC)"
	$(DOCKER_COMPOSE) build
	$(DOCKER_COMPOSE) up

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Services stopped.$(NC)"

restart: down up ## Restart all services

logs: ## Show logs from all services
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Show API Gateway logs
	$(DOCKER_COMPOSE) logs -f api-gateway

logs-frontend: ## Show Frontend logs
	$(DOCKER_COMPOSE) logs -f frontend

logs-prometheus: ## Show Prometheus logs
	$(DOCKER_COMPOSE) logs -f prometheus

logs-grafana: ## Show Grafana logs
	$(DOCKER_COMPOSE) logs -f grafana

logs-vault: ## Show Vault logs
	$(DOCKER_COMPOSE) logs -f vault

logs-n8n: ## Show n8n logs
	$(DOCKER_COMPOSE) logs -f n8n

clean: ## Stop services and remove volumes
	@echo "$(YELLOW)Cleaning up containers, networks, and volumes...$(NC)"
	$(DOCKER_COMPOSE) down -v
	@echo "$(YELLOW)Removing persistent n8n data volume (hard reset)...$(NC)"
	@docker volume rm -f peerloop_n8n_data >/dev/null 2>&1 || true
	@echo "$(GREEN)Cleanup complete.$(NC)"

fclean: clean ## Full cleanup including images
	@echo "$(RED)Removing all Docker images...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi all
	@echo "$(GREEN)Full cleanup complete.$(NC)"

rebuild: clean up ## Clean rebuild of all services

status: ## Show status of all services
	@echo "$(GREEN)Service Status:$(NC)"
	@$(DOCKER_COMPOSE) ps

health: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(NC)"
	@echo ""
	@echo "$(YELLOW)API Gateway:$(NC)"
	@curl -skf $(API_GATEWAY_URL)/health | jq . || echo "$(RED)Not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Prometheus:$(NC)"
	@curl -skf $(PROMETHEUS_URL)-/healthy && echo "$(GREEN)OK$(NC)" || echo "$(RED)Not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Grafana:$(NC)"
	@curl -skf $(GRAFANA_URL)api/health | jq . || echo "$(RED)Not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Vault:$(NC)"
	@curl -skf $(VAULT_URL)v1/sys/health | jq . || echo "$(RED)Not responding$(NC)"

waf-test: ## Run WAF/security tests through Nginx (scripts/waf_test.sh)
	@echo "$(GREEN)Running WAF/security tests...$(NC)"
	@bash scripts/waf_test.sh

grafana-test: ## Run Grafana API tests (scripts/grafana_test.sh)
	@echo "$(GREEN)Running Grafana API tests...$(NC)"
	@bash scripts/grafana_test.sh

init-vault: ## Initialize Vault (run after first startup)
	@echo "$(GREEN)Initializing Vault...$(NC)"
	@echo "This will output root token and unseal keys - SAVE THEM SECURELY!"
	@echo ""
	@$(DOCKER_COMPOSE) exec -T -e VAULT_ADDR=https://127.0.0.1:8200 -e VAULT_SKIP_VERIFY=true vault sh -c 'if vault status -format=json | grep -Eq '"'"'"initialized"[[:space:]]*:[[:space:]]*true'"'"'; then echo "Vault is already initialized."; else vault operator init -key-shares=1 -key-threshold=1; fi'

vault-push-secrets: ## Push secrets from secrets.env into Vault (run after init-vault)
	@echo "$(GREEN)Pushing secrets into Vault...$(NC)"
	@if [ ! -f secrets.env ] && [ ! -f secrets.env/secrets.env ] && [ ! -f secrets.env/.env ]; then \
		echo "$(RED)Error: secrets.env not found.$(NC)"; \
		echo "Create secrets.env as a file OR create secrets.env/secrets.env and fill in values first:"; \
		echo "  cp secrets.env.example secrets.env"; \
		exit 1; \
	fi
	@$(DOCKER_COMPOSE) exec -T \
		-e VAULT_ADDR=https://127.0.0.1:8200 \
		-e VAULT_SKIP_VERIFY=true \
		-e VAULT_TOKEN=$${VAULT_TOKEN} \
		vault sh < vault/scripts/init-vault.sh
	@echo "$(GREEN)Secrets pushed to Vault successfully.$(NC)"
	@echo "$(YELLOW)You can now delete or gitignore secrets.env$(NC)"

vault-list-secrets: ## List all secret paths stored in Vault
	@echo "$(GREEN)Listing Vault secrets...$(NC)"
	@$(DOCKER_COMPOSE) exec -T \
		-e VAULT_ADDR=https://127.0.0.1:8200 \
		-e VAULT_SKIP_VERIFY=true \
		-e VAULT_TOKEN=$${VAULT_TOKEN} \
		vault vault kv list secret/ 2>/dev/null || echo "$(RED)No secrets found or Vault not ready$(NC)"

vault-verify: ## Show current values in each secret path (values masked)
	@echo "$(GREEN)Verifying Vault secret paths...$(NC)"
	@for path in supabase google-oauth app llm grafana; do \
		echo ""; \
		echo "$(YELLOW)secret/$$path:$(NC)"; \
		$(DOCKER_COMPOSE) exec -T \
			-e VAULT_ADDR=https://127.0.0.1:8200 \
			-e VAULT_SKIP_VERIFY=true \
			-e VAULT_TOKEN=$${VAULT_TOKEN} \
			vault vault kv get -format=json secret/$$path 2>/dev/null \
			| grep -o '"[A-Z_]*"' | tr -d '"' \
			| sed 's/^/  key: /' \
			|| echo "  $(RED)path not found$(NC)"; \
	done

unseal-vault: ## Unseal Vault (requires unseal key)
	@echo "$(YELLOW)Enter unseal key:$(NC)"
	@read UNSEAL_KEY && $(DOCKER_COMPOSE) exec -T -e VAULT_ADDR=https://127.0.0.1:8200 -e VAULT_SKIP_VERIFY=true vault sh -c 'if vault status -format=json | grep -Eq '"'"'"sealed"[[:space:]]*:[[:space:]]*false'"'"'; then echo "Vault is already unsealed."; else vault operator unseal "'"'"'$$UNSEAL_KEY'"'"'"; fi'

shell-api: ## Open shell in API Gateway container
	$(DOCKER_COMPOSE) exec api-gateway sh

shell-frontend: ## Open shell in Frontend container
	$(DOCKER_COMPOSE) exec frontend sh

shell-vault: ## Open shell in Vault container
	$(DOCKER_COMPOSE) exec vault sh

shell-n8n: ## Open shell in n8n container
	$(DOCKER_COMPOSE) exec n8n sh

prune: ## Remove all unused Docker resources
	@echo "$(RED)WARNING: This will remove all unused Docker resources!$(NC)"
	@echo "Press Ctrl+C to cancel, Enter to continue..."
	@read _
	docker system prune -af --volumes

dev: ## Start only essential services for development
	$(DOCKER_COMPOSE) --profile dev up frontend_dev api-gateway nginx vault -d

.DEFAULT_GOAL := help
