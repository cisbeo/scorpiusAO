# 🧪 Tests RAG Service - PHASE 1: Embedding Engine

## 📋 Vue d'ensemble

Script de test automatisé pour valider les développements de la PHASE 1 (Embedding Engine) du RAG Service.

**3 Use Cases testés** :
1. **Embedding + Cache Redis** : Validation cache (miss → hit)
2. **Batch Embeddings** : Optimisation coûts API (1 appel pour N textes)
3. **Workflow Complet** : Ingestion + Recherche sémantique

---

## 🔧 Prérequis

### 1. Configuration environnement

Créer/éditer `.env` :
```bash
# OpenAI API (OBLIGATOIRE)
OPENAI_API_KEY=sk-proj-...

# Redis (OBLIGATOIRE pour Use Case 1 et 2)
REDIS_URL=redis://localhost:6379/0

# PostgreSQL (OBLIGATOIRE pour Use Case 3)
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db
```

### 2. Infrastructure démarrée

```bash
# Démarrer Redis (Use Case 1 & 2)
docker-compose up -d redis

# Démarrer PostgreSQL avec pgvector (Use Case 3)
docker-compose up -d postgres

# Vérifier que les services sont up
docker-compose ps
```

### 3. Base de données migrée (Use Case 3)

```bash
cd backend
alembic upgrade head
```

### 4. Dépendances Python installées

```bash
cd backend
pip install -r requirements.txt
```

---

## 🚀 Utilisation

### Exécuter tous les tests

```bash
python backend/tests/run_rag_tests.py --all
```

### Exécuter un test spécifique

```bash
# Use Case 1 uniquement
python backend/tests/run_rag_tests.py --use-case 1

# Use Case 2 uniquement
python backend/tests/run_rag_tests.py --use-case 2

# Use Case 3 uniquement
python backend/tests/run_rag_tests.py --use-case 3
```

### Aide

```bash
python backend/tests/run_rag_tests.py --help
```

---

## 📊 Use Cases détaillés

### ✅ Use Case 1: Embedding + Cache Redis

**Objectif** : Valider création embedding + cache Redis

**Ce qui est testé** :
- ✓ Appel OpenAI Embeddings API
- ✓ Création embedding (1536 dimensions)
- ✓ Stockage dans Redis avec TTL 30 jours
- ✓ Cache hit sur 2ème appel (pas de nouvel appel API)
- ✓ Gain de performance du cache

**Sortie attendue** :
```
USE CASE 1: EMBEDDING + CACHE REDIS
================================================================================

► Test 1.1: Premier appel (cache miss)
✅ Embedding créé: 1536 dimensions
   Preview: [0.1234, -0.5678, 0.9012, ...]
   Temps: 245ms (avec appel OpenAI)

► Test 1.2: Deuxième appel (cache hit)
✅ Embedding récupéré du cache
   Temps: 3ms (depuis Redis)
   Gain de performance: 98%

✅ Les embeddings sont identiques (cache fonctionne)

USE CASE 1: ✅ PASSED
  • Embedding Dimensions: 1536
  • Cache Hit Speedup: 98%
  • Api Call Time Ms: 245
  • Cache Time Ms: 3
```

**Prérequis** : Redis running

---

### ✅ Use Case 2: Batch Embeddings

**Objectif** : Valider batch embeddings (optimisation coûts)

**Ce qui est testé** :
- ✓ Batch de 5 textes → 1 seul appel API
- ✓ Tous les embeddings créés (1536 dimensions chacun)
- ✓ Ordre préservé (embeddings correspondent aux textes)
- ✓ Économie de 4 appels API vs. appels individuels

**Sortie attendue** :
```
USE CASE 2: BATCH EMBEDDINGS (OPTIMISATION COÛTS)
================================================================================

► Test 2.1: Batch de 5 textes
ℹ️  Sans batch: 5 appels API
ℹ️  Avec batch: 1 appel API → économie de 4 appels

✅ 5 embeddings créés en 1 appel API
   Temps total: 198ms
   Temps moyen par embedding: 39ms
   [0] 1536 dim - Infrastructure: 147 switchs Cisco...
   [1] 1536 dim - Virtualisation: 54 VMs VMware ESXi...
   [2] 1536 dim - Stockage: SAN Fibre Channel 100 TB...
   [3] 1536 dim - Réseau: Firewall Palo Alto PA-5220...
   [4] 1536 dim - Monitoring: Supervision Zabbix 24/7...

✅ Batch embeddings validé

USE CASE 2: ✅ PASSED
  • Texts Count: 5
  • Api Calls: 1
  • Savings: 4 appels
  • Time Ms: 198
  • Estimated Savings Pct: 80%
```

**Prérequis** : Redis running

---

### ✅ Use Case 3: Workflow Complet

**Objectif** : Valider ingestion + recherche sémantique

**Ce qui est testé** :
- ✓ Chunking du document (texte → chunks)
- ✓ Création embeddings pour chaque chunk
- ✓ Stockage dans pgvector (PostgreSQL)
- ✓ Recherche sémantique (cosine similarity)
- ✓ Tri par score de similarité
- ✓ Scores cohérents (>0.6 pour matches pertinents)

**Sortie attendue** :
```
USE CASE 3: WORKFLOW COMPLET (INGESTION + RECHERCHE)
================================================================================

► Test 3.1: Ingestion du document dans pgvector
ℹ️  Document ID: a1b2c3d4-...
ℹ️  Type: past_proposal
ℹ️  Taille: 456 caractères

✅ 5 chunks créés et stockés avec embeddings
   Temps d'ingestion: 234ms

► Test 3.2: Recherches sémantiques
ℹ️  🔍 Recherche: 'Quelles certifications possédez-vous ?'
   [1] Score: 0.847 - Notre société possède la certification ISO 27001 pour la sécurité...
   [2] Score: 0.723 - Nos datacenters sont certifiés Tier 3 avec redondance N+1...
   Temps de recherche: 87ms

ℹ️  🔍 Recherche: 'Quelle est votre infrastructure réseau ?'
   [1] Score: 0.891 - Nous gérons une infrastructure de 147 switchs Cisco et 54 VMs...
   [2] Score: 0.654 - Notre équipe technique comprend 12 ingénieurs certifiés...
   Temps de recherche: 65ms

ℹ️  🔍 Recherche: 'Quel est votre niveau de supervision ?'
   [1] Score: 0.879 - Nous assurons une supervision 24/7 avec Zabbix et un SLA 99.9%...
   [2] Score: 0.701 - Nos datacenters sont certifiés Tier 3 avec redondance N+1...
   Temps de recherche: 72ms

✅ Workflow complet validé

USE CASE 3: ✅ PASSED
  • Chunks Created: 5
  • Ingestion Time Ms: 234
  • Queries Tested: 3
  • Avg Similarity Score: 0.839
  • Results Found: 6
```

**Prérequis** : Redis + PostgreSQL running, migrations appliquées

---

## 🐛 Dépannage

### Erreur: "OPENAI_API_KEY non configuré"

```bash
# Vérifier .env
cat .env | grep OPENAI_API_KEY

# Ajouter la clé si manquante
echo "OPENAI_API_KEY=sk-proj-..." >> .env
```

### Erreur: "Redis connection refused"

```bash
# Démarrer Redis
docker-compose up -d redis

# Vérifier que Redis est accessible
redis-cli ping  # Doit répondre "PONG"
```

### Erreur: "Database connection failed" (Use Case 3)

```bash
# Démarrer PostgreSQL
docker-compose up -d postgres

# Appliquer migrations
cd backend
alembic upgrade head

# Vérifier connexion
psql -h localhost -p 5433 -U scorpius -d scorpius_db -c "SELECT 1"
```

### Erreur: "pgvector extension not installed"

```bash
# Se connecter à PostgreSQL
psql -h localhost -p 5433 -U scorpius -d scorpius_db

# Installer pgvector
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### Erreur: "Rate limit exceeded"

Si vous atteignez la limite de rate OpenAI :
- Attendez quelques secondes
- Les tests ont un retry automatique (3 tentatives)
- Vérifiez vos quotas OpenAI

---

## 📈 Métriques de succès

### Use Case 1 - Cache
- ✅ Cache hit speedup: >90%
- ✅ Embedding dimensions: 1536
- ✅ Cache time: <10ms

### Use Case 2 - Batch
- ✅ API calls: 1 (au lieu de N)
- ✅ Savings: N-1 appels
- ✅ Time per embedding: <50ms

### Use Case 3 - Workflow
- ✅ Chunks created: >0
- ✅ Avg similarity score: >0.7
- ✅ Search time: <200ms

---

## 🔄 Intégration Continue

Pour intégrer ces tests dans CI/CD :

```yaml
# .github/workflows/test-rag.yml
name: RAG Service Tests

on: [push, pull_request]

jobs:
  test-rag:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379

      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_PASSWORD: scorpius_password
          POSTGRES_DB: scorpius_db
        ports:
          - 5433:5432

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run migrations
        run: |
          cd backend
          alembic upgrade head

      - name: Run RAG tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python backend/tests/run_rag_tests.py --all
```

---

## 📝 Notes

- **Coûts OpenAI** : Les tests coûtent ~$0.001 par exécution complète (embeddings text-embedding-3-small)
- **Cache** : Le cache Redis persiste entre les exécutions (TTL 30 jours)
- **Données de test** : Les données insérées dans PostgreSQL ne sont pas nettoyées automatiquement
- **Logs** : Pour plus de logs, définir `LOG_LEVEL=DEBUG` dans `.env`

---

## 🎯 Prochaines étapes

Après validation de la PHASE 1 :
- PHASE 2 : Smart Chunking (chunking adaptatif par type de document)
- PHASE 3 : Intégration Pipeline Celery
- PHASE 4 : API Endpoints REST
- PHASE 5 : Reranking

Voir [RAG_SERVICE_IMPLEMENTATION_PLAN.md](../../RAG_SERVICE_IMPLEMENTATION_PLAN.md) pour le plan complet.
