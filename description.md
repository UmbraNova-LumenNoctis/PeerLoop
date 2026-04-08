# Quick Project Description

**PeerLoop** is a microservices-based social platform orchestrated with Docker Compose.
The React/Vite frontend goes through an Nginx + ModSecurity proxy, then a FastAPI API Gateway that routes requests to domain services (auth, users, files, friendships, posts, notifications, chat, search, llm).

## Goal

The project simulates a continuous loop of user interactions:
- sign-in and authentication
- content creation and social reactions
- real-time messaging
- notifications and re-engagement

## Main Stack

- Frontend: React, Vite, TypeScript, Chakra UI
- Backend: FastAPI (multiple services)
- Data: Supabase/PostgreSQL, ImageKit
- AI: LLM service connected to Gemini
- Security: Nginx, ModSecurity, Vault, Google OAuth, TOTP 2FA
- Observability: Prometheus + Grafana
- Automation: n8n (webhook/cron workflows)

## Project Value

PeerLoop demonstrates a modern production-oriented architecture:
- clear separation of responsibilities across services
- centralized security and secret management
- full monitoring coverage
- operational and business automations via n8n
