# n8n Workflows - Documentation complete (PeerLoop)

Cette documentation explique le fonctionnement, la configuration, les entrees/sorties
et l'utilisation de tous les workflows n8n du projet.

## 1) Vue d'ensemble

Objectif des workflows:
- automatiser des actions metier et ops depuis des evenements webhook ou cron
- centraliser la logique de routage (standard vs escalade)
- notifier des systemes externes (Slack, CRM, support, audit, etc.)
- garder une trace de correlation via `correlationId`

Workflows disponibles:
- `workflows/professional_incident_triage.json`
- `workflows/professional_daily_ops_report.json`
- `workflows/professional_user_onboarding_automation.json`
- `workflows/professional_user_onboarding_crm_support.json`
- `workflows/professional_content_moderation_escalation.json`
- `workflows/professional_failed_login_guard.json`
- `workflows/professional_user_reactivation_campaign.json`

## 2) Prerequis

- Stack lancee avec Docker Compose (`make up`)
- n8n accessible sur `https://localhost:8443/services/n8n/`
- Variables n8n configurees dans `.env` (pas dans `secrets.env`)
- Certificat local self-signed: utiliser `curl -k` pour les tests HTTPS

Variables importantes (exemples):
- `N8N_EDITOR_BASE_URL`
- `N8N_WEBHOOK_URL`
- `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`
- `N8N_ALERT_WEBHOOK_URL`
- `N8N_ONBOARDING_*`
- `N8N_MODERATION_*`
- `N8N_SECURITY_*`
- `N8N_REACTIVATION_*`

## 3) Importer et activer un workflow

1. Ouvrir `https://localhost:8443/services/n8n/`
2. Se connecter avec `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`
3. Aller dans **Workflows** -> **Import from File**
4. Choisir un JSON dans `n8n/workflows/`
5. **Save**
6. **Activate**
7. Copier l'URL webhook generee si besoin

Bonnes pratiques:
- garder les workflows versionnes dans Git (source of truth)
- ne pas hardcoder de secrets dans les nodes
- utiliser les variables d'env pour les endpoints externes

## 4) Convention commune des flows

Pattern technique recurrent:
1. Trigger (`Webhook` ou `Cron`)
2. Validation/normalisation (`Function`)
3. Conditions de routage (`If`)
4. Actions externes (`HTTP Request`, `continueOnFail=true` souvent actif)
5. Reponse webhook (quand `responseMode=responseNode`)

Comportement en erreur:
- validation invalide => erreur d'execution (visible dans n8n Execution)
- endpoint optionnel non configure => etape skippee, flow continue
- endpoint externe en erreur => marque comme tentative failed, flow continue

## 5) Reference detaillee par workflow

### A. Incident triage & alerting
Fichier: `professional_incident_triage.json`

Trigger:
- `POST /services/n8n/webhook/peers/incident-events`

Payload minimum:
- `source`, `eventType`, `severity`, `summary`

Payload optionnel:
- `details`, `metadata`, `occurredAt`, `correlationId`

Regles metier:
- severite `high`/`critical` => route `escalation` (HTTP 202)
- severite `info`/`low`/`medium` => route `standard` (HTTP 200)
- envoi externe optionnel via `N8N_ALERT_WEBHOOK_URL`

Exemple test:
```bash
curl -sk -X POST "https://localhost:8443/services/n8n/webhook/peers/incident-events" \
  -H "Content-Type: application/json" \
  -d '{
    "source":"api-gateway",
    "eventType":"rate_limit_spike",
    "severity":"high",
    "summary":"Burst de 429 detecte"
  }'
```

### B. Daily ops report + archive
Fichier: `professional_daily_ops_report.json`

Trigger:
- Cron quotidien (07:00)

Checks:
- `api-gateway`, `auth_service`, `search_service`, `prometheus`

Sorties:
- rapport consolide (`overallStatus`, `failedChecks`, `recommendedAction`)
- notification optionnelle `N8N_DAILY_REPORT_WEBHOOK_URL`
- archivage optionnel `N8N_REPORT_ARCHIVE_WEBHOOK_URL`
- alerte degradee optionnelle `N8N_ALERT_WEBHOOK_URL`

Usage:
- workflow autonome cron, pas de webhook entrant
- verifier l'heure cron selon `N8N_TIMEZONE`

### C. User onboarding automation
Fichier: `professional_user_onboarding_automation.json`

Trigger:
- `POST /services/n8n/webhook/peers/user-onboarding`

Payload minimum:
- `userId`, `username`

Payload optionnel:
- `email`, `locale`, `registeredAt`, `correlationId`

Regles:
- notification in-app seulement si `N8N_ONBOARDING_NOTIFICATION_WEBHOOK_URL` est configure
- email seulement si:
  - `N8N_ONBOARDING_EMAIL_WEBHOOK_URL` est configure
  - et `email` est present/valide
- reponse webhook structuree (`status`, `flow`, `userId`, `correlationId`)

Exemple:
```bash
curl -sk -X POST "https://localhost:8443/services/n8n/webhook/peers/user-onboarding" \
  -H "Content-Type: application/json" \
  -d '{
    "userId":"u_123",
    "username":"alice",
    "email":"alice@example.com",
    "locale":"fr-FR"
  }'
```

### D. User onboarding pro (CRM + support)
Fichier: `professional_user_onboarding_crm_support.json`

Trigger:
- `POST /services/n8n/webhook/peers/user-onboarding-pro`

Actions optionnelles:
- `N8N_ONBOARDING_NOTIFICATION_WEBHOOK_URL`
- `N8N_ONBOARDING_EMAIL_WEBHOOK_URL`
- `N8N_ONBOARDING_CRM_WEBHOOK_URL`
- `N8N_ONBOARDING_SUPPORT_WEBHOOK_URL`
- `N8N_ONBOARDING_AUDIT_WEBHOOK_URL`

Usage recommande:
- utiliser ce flow pour les users "business" (plan, source, CRM lifecycle)
- exploiter l'audit pour tracer les integrations executees/skipped

### E. Content moderation escalation
Fichier: `professional_content_moderation_escalation.json`

Trigger:
- `POST /services/n8n/webhook/peers/moderation-events`

Payload minimum:
- `reportId`, `contentType`, `contentId`, `reason`, `severity`

Regles severite:
- `low`/`medium`: traitement standard
- `high`: escalade moderation
- `critical`: escalade + auto-action possible

Integrations optionnelles:
- `N8N_MODERATION_NOTIFICATION_WEBHOOK_URL`
- `N8N_MODERATION_CASE_WEBHOOK_URL`
- `N8N_MODERATION_ACTION_WEBHOOK_URL`

Reponse webhook:
- payload structure avec `status`, `reportId`, `severity`, `correlationId`

### F. Failed login guard & security escalation
Fichier: `professional_failed_login_guard.json`

Trigger:
- `POST /services/n8n/webhook/peers/security/auth-events`

Payload minimum:
- `eventType` (`failed_login`, `bruteforce_detected`, `account_locked`)
- `username`
- `ipAddress`

Payload optionnel:
- `failedAttempts`, `userId`, `userAgent`, `occurredAt`, `correlationId`

Regles:
- calcule une severite normalisee (`low`, `medium`, `high`, `critical`)
- escalade automatique sur `high`/`critical`
- blocage recommande sur `critical`

Integrations optionnelles:
- alerte securite: `N8N_SECURITY_ALERT_WEBHOOK_URL`
- blocage auto: `N8N_SECURITY_BLOCK_WEBHOOK_URL`

### G. Weekly user reactivation campaign
Fichier: `professional_user_reactivation_campaign.json`

Trigger:
- Cron hebdomadaire (lundi 09:00)

Pipeline:
1. recupere les candidats inactifs via `N8N_REACTIVATION_SOURCE_WEBHOOK_URL`
2. normalise la liste (userId, username, email, locale, inactiveDays)
3. envoie les messages via `N8N_REACTIVATION_CAMPAIGN_WEBHOOK_URL`
4. pousse un audit optionnel via `N8N_REACTIVATION_AUDIT_WEBHOOK_URL`

Format attendu de la source (recommande):
```json
{
  "candidates": [
    {
      "userId": "u_1",
      "username": "alice",
      "email": "alice@example.com",
      "locale": "fr-FR",
      "inactiveDays": 21
    }
  ]
}
```

## 6) Catalogue des variables d'environnement (n8n)

Variables socle:
- `N8N_EDITOR_BASE_URL`: URL de l'UI n8n derriere nginx
- `N8N_WEBHOOK_URL`: base publique des webhooks
- `N8N_ENCRYPTION_KEY`: cle de chiffrement n8n
- `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`
- `N8N_TIMEZONE`, `N8N_LOG_LEVEL`

Variables d'integration:
- global alerting: `N8N_ALERT_WEBHOOK_URL`
- daily ops: `N8N_DAILY_REPORT_WEBHOOK_URL`, `N8N_REPORT_ARCHIVE_WEBHOOK_URL`
- onboarding: `N8N_ONBOARDING_NOTIFICATION_WEBHOOK_URL`, `N8N_ONBOARDING_EMAIL_WEBHOOK_URL`, `N8N_ONBOARDING_CRM_WEBHOOK_URL`, `N8N_ONBOARDING_SUPPORT_WEBHOOK_URL`, `N8N_ONBOARDING_AUDIT_WEBHOOK_URL`
- moderation: `N8N_MODERATION_NOTIFICATION_WEBHOOK_URL`, `N8N_MODERATION_CASE_WEBHOOK_URL`, `N8N_MODERATION_ACTION_WEBHOOK_URL`
- security: `N8N_SECURITY_ALERT_WEBHOOK_URL`, `N8N_SECURITY_BLOCK_WEBHOOK_URL`
- reactivation: `N8N_REACTIVATION_SOURCE_WEBHOOK_URL`, `N8N_REACTIVATION_CAMPAIGN_WEBHOOK_URL`, `N8N_REACTIVATION_AUDIT_WEBHOOK_URL`

## 7) Validation rapide (checklist)

- workflow importe et active
- endpoint webhook teste avec `curl -k`
- execution visible dans n8n (status success/failed)
- `correlationId` present dans les payloads sortants
- endpoints optionnels en place ou explicitement vides

## 8) Troubleshooting

Si le webhook retourne 404:
- verifier que le workflow est **active**
- verifier le path exact (`/webhook/...`) et le prefix nginx (`/services/n8n/`)

Si aucune notification externe:
- verifier la variable `.env` correspondante
- verifier que l'URL commence par `http://` ou `https://`
- verifier les logs de l'execution n8n (`continueOnFail` peut masquer l'erreur en bloquant pas le flow)

Si les crons ne partent pas:
- verifier timezone (`N8N_TIMEZONE`)
- verifier que le container n8n est up
- verifier que le workflow cron est active

## 9) Securite et exploitation

- ne jamais commiter de webhook prive ou token
- garder les endpoints externes en HTTPS
- activer des endpoint cibles idempotents cote receveur (dedupe par `correlationId`)
- conserver les audits pour les flows critiques (onboarding pro, security, reactivation)

## 10) Emplacements utiles

- Workflows JSON: `n8n/workflows/`
- Doc projet globale: `README.md`
- Variables compose/n8n: `.env`
- Secrets Vault bootstrap: `secrets.env`

## 11) Guide de test complet (n8n UI + frontend UI)

### 11.1 Preparation (obligatoire)

1. Lancer la stack:
```bash
make up
```
2. Ouvrir n8n: `https://localhost:8443/services/n8n/`
3. Verifier que les workflows sont en statut **Active**.
4. Ouvrir le frontend (application web) sur son URL locale habituelle.
5. Dans n8n, activer l'historique d'execution:
   - `Settings` -> `Execution` -> save success + failed executions.

### 11.2 Comment lire le resultat dans n8n (pour tous les tests)

- Ouvrir le workflow -> `Executions`
- Lancer `Execute workflow` (ou declencher via frontend/webhook)
- Cliquer la derniere execution
- Verifier:
  - statut global: `Success` / `Error`
  - chaque node: onglets `Input`, `Output`, `Error`
  - presence de `correlationId` dans les donnees

### 11.3 Tests par workflow (n8n + frontend)

#### A) Incident triage & alerting
- n8n:
  - envoyer le `curl` de la section 5.A avec `severity=high`
  - attendu: route escalation + notification optionnelle
- frontend:
  - provoquer une action qui genere un incident ops (ex: surcharge/requetes invalides)
  - attendu: execution visible dans n8n avec `source` frontend/API gateway

#### B) Daily ops report + archive
- n8n:
  - executer manuellement le workflow cron depuis l'UI
  - attendu: checks des services + rapport consolide
- frontend:
  - consulter l'app pendant le test (elle doit rester disponible)
  - attendu: aucun impact utilisateur, workflow purement ops

#### C) User onboarding automation
- n8n:
  - envoyer le `curl` de la section 5.C
  - attendu: notification in-app et/ou email selon variables configurees
- frontend:
  - creer un nouvel utilisateur depuis l'UI d'inscription
  - attendu: execution onboarding + message de bienvenue cote UI si integration active

#### D) User onboarding pro (CRM + support)
- n8n:
  - appeler webhook `user-onboarding-pro` avec payload business
  - attendu: CRM/support/audit executes ou `skipped` proprement
- frontend:
  - creer un compte avec scenario "pro" (si parcours existe)
  - attendu: audit d'integration dans l'execution n8n

#### E) Content moderation escalation
- n8n:
  - poster un event moderation `medium` puis `critical`
  - attendu: medium -> standard, critical -> escalade + auto-action possible
- frontend:
  - signaler un contenu depuis l'UI (post/commentaire)
  - attendu: execution avec `reportId`, `contentId`, severite calculee

#### F) Failed login guard & security escalation
- n8n:
  - poster un event `failed_login`, puis `bruteforce_detected`
  - attendu: severite montee, alertes envoyees selon config
- frontend:
  - faire plusieurs tentatives de login invalides
  - attendu: workflow lance, event securite trace dans n8n

#### G) Weekly user reactivation campaign
- n8n:
  - lancer manuellement le workflow
  - attendu:
    - node `Reactivation Source Configured?` ne doit plus echouer sur env access
    - fetch candidats -> envoi campagne -> audit
- frontend:
  - verifier cote UI (notifications/messages) si un canal de reactivation est branche
  - attendu: aucun crash UI, execution terminee dans n8n

### 11.4 Matrice de validation finale

Pour chaque workflow:
- Trigger recu (webhook/cron/manual)
- Execution `Success` (ou erreur explicite et exploitable)
- Retries HTTP visibles en cas de cible indisponible
- Pas d'erreur `access to env vars denied`
- Donnees metier minimales presentes (`userId`, `reportId`, `severity`, etc.)

### 11.5 Commandes utiles de debug

```bash
# Logs n8n
docker compose logs -f n8n

# Logs nginx (proxy)
docker compose logs -f nginx

# Lister les workflows connus par n8n
docker compose exec -T n8n n8n list:workflow
```

## 12) Verification des resultats (preuve de fonctionnement)

Cette section sert de preuve objective que les workflows fonctionnent en conditions reelles.

### 12.1 Preuves a collecter pour chaque workflow

Pour chaque workflow teste, conserver:
- **Execution ID** n8n
- **Statut final** (`Success` ou `Error`)
- **Horodatage** debut/fin
- **Node critique** avec output valide (JSON)
- **Preuve externe** (si integration): code HTTP, payload recu, ou log cible

### 12.2 Criteres de succes minimum

Un workflow est considere "fonctionnel" si:
- le trigger est bien recu (webhook/cron/manual)
- l'execution est `Success` ou une erreur metier explicite et attendue
- les nodes HTTP ont un comportement robuste (retry/timeout)
- les champs metier attendus sont presents (`correlationId`, `userId`, `severity`, etc.)
- aucun `access to env vars denied`

### 12.3 Procedure de preuve dans n8n UI

1. Ouvrir le workflow -> `Executions`
2. Ouvrir la derniere execution
3. Capturer:
   - bandeau statut global
   - output d'un node cle (ex: `Validate ...`, `Send ...`, `Respond ...`)
4. Noter l'`Execution ID`
5. Verifier les donnees metier en sortie

### 12.4 Verification technique par logs

```bash
# Preuve execution n8n (erreurs/alerts)
docker compose logs --since=10m n8n

# Preuve passage proxy nginx (codes HTTP)
docker compose logs --since=10m nginx
```

Verifier dans les logs:
- webhook entrant present
- reponses HTTP attendues (200/202 selon workflow)
- absence d'erreurs bloquantes repetitives

### 12.5 Modele de rapport de preuve (a copier)

```text
Workflow: <nom>
Execution ID: <id>
Trigger: <webhook|cron|manual>
Resultat: <Success|Error attendue>
Donnees clefs verifiees: <liste>
Integrations appelees: <oui/non + status HTTP>
Preuve logs: <ligne/horodatage>
Conclusion: <OK fonctionnel | KO a corriger>
```

### 12.6 Definition de "ca fonctionne"

On valide "ca fonctionne" quand:
- 1 execution nominale reussie par workflow
- 1 execution avec cas degrade (endpoint externe indisponible ou payload incomplet) geree proprement
- les preuves (UI + logs) sont archivees pour les 7 workflows

## 13) Publication UI forcee (cas "webhook not registered")

Dans certains cas n8n peut afficher des workflows "actifs" mais ne pas enregistrer les webhooks
de production (symptome: `404 The requested webhook ... is not registered`), souvent avec
un demarrage indiquant `0 published workflows`.

### 13.1 Procedure recommandee (workflow par workflow)

Pour chaque workflow:
1. Ouvrir le workflow dans l'UI n8n.
2. Modifier un detail non fonctionnel (ex: ajouter un espace dans la description).
3. Cliquer **Save**.
4. Basculer **Active** sur OFF puis ON (re-activation).
5. Verifier dans `Executions` qu'une nouvelle version est bien prise en compte.

Objectif: forcer la creation d'une version publiee cote n8n, puis l'enregistrement des webhooks prod.

### 13.2 Verification immediate apres publication

Executer un test webhook de production:

```bash
curl -sk -X POST "https://localhost:8443/services/n8n/webhook/peers/incident-events" \
  -H "Content-Type: application/json" \
  -d '{
    "source":"frontend",
    "eventType":"proof_test",
    "severity":"high",
    "summary":"post-publish verification",
    "correlationId":"proof-ui-publish-1"
  }'
```

Attendu:
- plus de `404 webhook not registered`
- reponse metier du workflow (`200` ou `202` selon la logique du flow)

### 13.3 Validation technique complementaire

```bash
# verifier en temps reel pendant le test
docker compose logs -f n8n nginx
```

Attendu dans les logs:
- requete webhook recue sans message "unknown webhook"
- execution associee visible dans n8n

### 13.4 Sequence rapide a appliquer aux 7 workflows

Appliquer la procedure 13.1 sur:
- PeerLoop - Incident Triage & Alerting
- PeerLoop - Daily Ops Health & Archive Report
- PeerLoop - User Onboarding Automation
- PeerLoop - User Onboarding (CRM + Support)
- PeerLoop - Content Moderation Escalation
- PeerLoop - Failed Login Guard & Security Escalation
- PeerLoop - Weekly User Reactivation Campaign
