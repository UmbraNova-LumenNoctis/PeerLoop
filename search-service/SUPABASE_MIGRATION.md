# Migration de PostgreSQL local vers Supabase

## Vue d'ensemble

Ce guide explique comment migrer l'implémentation actuelle utilisant PostgreSQL local vers Supabase en production.

## Étape 1 : Créer un projet Supabase

1. Allez sur [https://supabase.com](https://supabase.com)
2. Créez un nouveau projet
3. Notez les informations de connexion :
   - Project URL
   - Project API URL
   - Database password
   - Connection string

## Étape 2 : Obtenir la chaîne de connexion

Depuis le tableau de bord Supabase :

1. Allez dans **Settings** > **Database**
2. Trouvez la section **Connection string** > **URI**
3. La chaîne de connexion ressemble à :

```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

## Étape 3 : Initialiser le schéma de base de données

### Option A : Via l'éditeur SQL Supabase (Recommandé)

1. Allez dans **SQL Editor** dans Supabase
2. Créez une nouvelle requête
3. Copiez le contenu de `search-service/init-db.sql`
4. Exécutez la requête

### Option B : Via psql

```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" < search-service/init-db.sql
```

### Option C : Via un client de base de données

Utilisez DBeaver, pgAdmin, ou tout autre client PostgreSQL :
- Host: `db.[PROJECT-REF].supabase.co`
- Port: `5432`
- Database: `postgres`
- User: `postgres`
- Password: `[YOUR-PASSWORD]`

Puis exécutez le script `init-db.sql`.

## Étape 4 : Mettre à jour les variables d'environnement

### Pour le développement local

Créez ou modifiez le fichier `.env` à la racine du projet :

```env
# Supabase Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=[YOUR-PASSWORD]
POSTGRES_DB=postgres
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Meilisearch
MEILI_MASTER_KEY=peerloop_meili_master_key

# Vault
VAULT_TOKEN=dev-root-ttkn

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### Pour la production

Stockez les secrets dans HashiCorp Vault :

```bash
# Se connecter à Vault
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-production-token

# Stocker les secrets
vault kv put secret/database \
  url="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

vault kv put secret/meilisearch \
  key="your-production-meili-key"
```

## Étape 5 : Modifier docker-compose.yml

### Supprimer le service PostgreSQL local

Commentez ou supprimez la section `postgres` dans `docker-compose.yml` :

```yaml
# SUPPRIMER OU COMMENTER CETTE SECTION
#  postgres:
#    image: postgres:15-alpine
#    container_name: peerloop_postgres
#    environment:
#      - POSTGRES_USER=${POSTGRES_USER:-peerloop}
#      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-peerloop_password}
#      - POSTGRES_DB=${POSTGRES_DB:-peerloop_db}
#    volumes:
#      - postgres_data:/var/lib/postgresql/data
#      - ./search-service/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
#    networks:
#      - peerloop_net
#    restart: unless-stopped
#    healthcheck:
#      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-peerloop}"]
#      interval: 10s
#      timeout: 5s
#      retries: 5
```

### Mettre à jour les dépendances du Search Service

Modifiez la section `search-service` pour supprimer la dépendance PostgreSQL :

```yaml
  search-service:
    build:
      context: ./search-service
      dockerfile: Dockerfile
    container_name: peerloop_search
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_KEY=${MEILI_MASTER_KEY:-peerloop_meili_master_key}
      - VAULT_ADDR=http://vault:8200
      - VAULT_TOKEN=${VAULT_TOKEN:-}
    networks:
      - peerloop_net
    depends_on:
      meilisearch:
        condition: service_started
      vault:
        condition: service_started
    restart: unless-stopped
```

**Note importante** : Supprimez le `depends_on: postgres` et sa condition `service_healthy`.

### Supprimer le volume PostgreSQL

Dans la section `volumes`, supprimez ou commentez :

```yaml
volumes:
  # ... autres volumes ...
  # postgres_data:  # SUPPRIMER CETTE LIGNE
  #   name: peerloop_postgres_data  # SUPPRIMER CETTE LIGNE
```

## Étape 6 : Redémarrer les services

```bash
# Arrêter tous les services
docker compose down

# Supprimer les volumes locaux (optionnel)
docker volume rm peerloop_postgres_data

# Démarrer avec Supabase
docker compose up --build -d
```

## Étape 7 : Vérifier la connexion

```bash
# Vérifier le health check
curl http://localhost:8001/health | jq .

# Devrait afficher :
# {
#   "status": "healthy",
#   "service": "Search Service",
#   "version": "1.0.0",
#   "database": "healthy",
#   "meilisearch": "healthy"
# }
```

## Étape 8 : Synchroniser les données

```bash
# Synchroniser les données de Supabase vers Meilisearch
curl -X POST http://localhost:8001/sync | jq .

# Vérifier les statistiques
curl http://localhost:8001/stats | jq .
```

## Étape 9 : Tester la recherche

```bash
# Test de recherche simple
curl "http://localhost:8001/search?q=fastapi" | jq .

# Test avec filtres
curl "http://localhost:8001/search?q=docker&visibility=public" | jq .
```

## Configuration avancée : Row Level Security (RLS)

Supabase supporte le Row Level Security de PostgreSQL. Pour l'activer :

```sql
-- Activer RLS sur les tables
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Exemple de politique : les utilisateurs ne peuvent voir que leurs propres posts
CREATE POLICY "Users can view their own posts"
  ON posts
  FOR SELECT
  USING (auth.uid()::text = author_id::text);

-- Politique : les posts publics sont visibles par tous
CREATE POLICY "Public posts are visible to all"
  ON posts
  FOR SELECT
  USING (visibility = 'public');
```

**Note** : Vous devrez ajuster votre Search Service pour gérer l'authentification Supabase si vous utilisez RLS.

## Webhooks Supabase pour synchronisation automatique

Pour une synchronisation en temps réel, configurez des webhooks Supabase :

1. Allez dans **Database** > **Webhooks**
2. Créez un nouveau webhook pour la table `posts`
3. Configurez l'URL : `http://your-search-service/webhook/sync`
4. Événements : `INSERT`, `UPDATE`, `DELETE`

Puis ajoutez un endpoint webhook dans votre Search Service :

```python
@app.post("/webhook/sync")
async def webhook_sync(event: dict):
    """Handle Supabase webhook events"""
    event_type = event.get("type")
    record = event.get("record")
    
    if event_type == "INSERT" or event_type == "UPDATE":
        # Index the new/updated post
        meili_service.index_post(record)
    elif event_type == "DELETE":
        # Remove from index
        meili_service.delete_post(record["id"])
    
    return {"status": "success"}
```

## Rollback vers PostgreSQL local

Si vous devez revenir en arrière :

1. Décommentez le service `postgres` dans `docker-compose.yml`
2. Remettez la `DATABASE_URL` d'origine dans `.env`
3. Restaurez les dépendances du `search-service`
4. Redémarrez : `docker compose up --build -d`

## Checklist de migration

- [ ] Projet Supabase créé
- [ ] Chaîne de connexion obtenue
- [ ] Schéma de base de données initialisé (init-db.sql exécuté)
- [ ] Variables d'environnement mises à jour
- [ ] Service postgres commenté dans docker-compose.yml
- [ ] Dépendances du search-service mises à jour
- [ ] Volume postgres_data supprimé de la configuration
- [ ] Services redémarrés
- [ ] Health check validé
- [ ] Synchronisation testée
- [ ] Recherches testées

## Support et dépannage

### Erreur : "could not connect to server"

Vérifiez :
- Que votre IP est autorisée dans les paramètres Supabase (Database > Settings > Connection pooling)
- Que la chaîne de connexion est correcte
- Que le mot de passe ne contient pas de caractères spéciaux non échappés

### Erreur : "database does not exist"

Assurez-vous d'utiliser `postgres` comme nom de base de données, pas le nom de votre projet.

### Erreur : "tables not found"

Exécutez à nouveau le script `init-db.sql` via l'éditeur SQL de Supabase.

## Ressources

- [Documentation Supabase](https://supabase.com/docs)
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
- [Meilisearch Documentation](https://www.meilisearch.com/docs)

## Architecture finale

```
         Frontend
             |
             v
        API Gateway
             |
             v
      Search Service
          /    \
         /      \
        v        v
   Supabase   Meilisearch
   (Source)   (Search)
```

Cette architecture permet :
- ✅ Scalabilité cloud native
- ✅ Backup automatique (Supabase)
- ✅ Performance de recherche (Meilisearch)
- ✅ Sécurité renforcée (RLS, Vault)
- ✅ Monitoring intégré (Grafana, Prometheus)
