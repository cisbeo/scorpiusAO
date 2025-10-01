# 🧪 Guide de Test - RAG Service PHASE 1

## 📋 Résumé

Ce guide vous permet de tester les développements de la **PHASE 1 : Embedding Engine** du RAG Service.

**3 Use Cases automatisés** :
- ✅ **Use Case 1** : Embedding + Cache Redis
- ✅ **Use Case 2** : Batch Embeddings (optimisation coûts)
- ✅ **Use Case 3** : Workflow complet (ingestion + recherche)

---

## 🚀 Quick Start (3 étapes)

### Étape 1 : Vérifier les prérequis

```bash
python backend/tests/check_prerequisites.py
```

Ce script vérifie automatiquement :
- ✓ Fichier `.env` configuré
- ✓ `OPENAI_API_KEY` valide
- ✓ Redis accessible
- ✓ PostgreSQL + pgvector
- ✓ Migrations appliquées

**Si tout est OK** → Passez à l'étape 2
**Si des erreurs** → Suivez les instructions affichées

---

### Étape 2 : Exécuter les tests

```bash
python backend/tests/run_rag_tests.py --all
```

**Durée** : ~30 secondes
**Coût** : ~$0.001 (OpenAI embeddings)

---

### Étape 3 : Analyser les résultats

Sortie attendue :

```
================================================================================
                  🚀 TESTS RAG SERVICE - PHASE 1: EMBEDDING ENGINE
================================================================================

ℹ️  Date: 2025-10-01 15:30:00
ℹ️  OpenAI Model: text-embedding-3-small
ℹ️  Redis URL: redis://localhost:6379/0
ℹ️  Database: localhost:5433/scorpius_db

[... tests s'exécutent ...]

================================================================================
                               📊 RAPPORT FINAL
================================================================================

USE CASE 1: ✅ PASSED
  • Embedding Dimensions: 1536
  • Cache Hit Speedup: 98%
  • Api Call Time Ms: 245
  • Cache Time Ms: 3

USE CASE 2: ✅ PASSED
  • Texts Count: 5
  • Api Calls: 1
  • Savings: 4 appels
  • Time Ms: 198
  • Estimated Savings Pct: 80%

USE CASE 3: ✅ PASSED
  • Chunks Created: 5
  • Ingestion Time Ms: 234
  • Queries Tested: 3
  • Avg Similarity Score: 0.839
  • Results Found: 6

Résumé:
  • Tests réussis: 3/3
  • Tests échoués: 0/3

🎉 TOUS LES TESTS SONT PASSÉS !
```

---

## 🔧 Configuration détaillée

### Prérequis infrastructure

#### 1. Redis (obligatoire)

```bash
# Démarrer Redis
docker-compose up -d redis

# Vérifier
redis-cli ping  # Doit retourner "PONG"
```

#### 2. PostgreSQL + pgvector (obligatoire pour Use Case 3)

```bash
# Démarrer PostgreSQL
docker-compose up -d postgres

# Appliquer migrations
cd backend
alembic upgrade head

# Vérifier pgvector
psql -h localhost -p 5433 -U scorpius -d scorpius_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 3. Variables d'environnement

Fichier `.env` :

```bash
# Obligatoire
OPENAI_API_KEY=sk-proj-...

# Par défaut (modifiable)
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 🎯 Tests individuels

### Use Case 1 uniquement

```bash
python backend/tests/run_rag_tests.py --use-case 1
```

**Teste** : Embedding + Cache Redis
**Durée** : ~5s
**Prérequis** : Redis

---

### Use Case 2 uniquement

```bash
python backend/tests/run_rag_tests.py --use-case 2
```

**Teste** : Batch embeddings (1 appel pour 5 textes)
**Durée** : ~3s
**Prérequis** : Redis

---

### Use Case 3 uniquement

```bash
python backend/tests/run_rag_tests.py --use-case 3
```

**Teste** : Workflow complet (ingestion + recherche)
**Durée** : ~10s
**Prérequis** : Redis + PostgreSQL

---

## 🐛 Dépannage

### ❌ "OPENAI_API_KEY non configuré"

```bash
# Vérifier .env
cat backend/.env | grep OPENAI_API_KEY

# Ajouter si manquant
echo "OPENAI_API_KEY=sk-proj-..." >> backend/.env
```

### ❌ "Redis connection refused"

```bash
# Démarrer Redis
docker-compose up -d redis

# Vérifier logs
docker-compose logs redis
```

### ❌ "PostgreSQL inaccessible"

```bash
# Démarrer PostgreSQL
docker-compose up -d postgres

# Vérifier connexion
psql -h localhost -p 5433 -U scorpius -d scorpius_db -c "SELECT 1"
```

### ❌ "pgvector extension not found"

```bash
psql -h localhost -p 5433 -U scorpius -d scorpius_db

-- Dans psql
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### ❌ "Table document_embeddings not found"

```bash
cd backend
alembic upgrade head
```

---

## 📊 Que testent ces Use Cases ?

### Use Case 1 : Embedding + Cache

**Fonctionnalités validées** :
- ✓ Appel OpenAI Embeddings API (`text-embedding-3-small`)
- ✓ Retry automatique (3 tentatives avec backoff exponentiel)
- ✓ Gestion erreurs (RateLimitError, APIError)
- ✓ Cache Redis (SHA256 hash du texte)
- ✓ TTL 30 jours
- ✓ Gain de performance cache (>90%)

**Fichiers testés** :
- `backend/app/services/rag_service.py` → `create_embedding()`
- Cache Redis → `_get_cached_embedding()`, `_set_cached_embedding()`

---

### Use Case 2 : Batch Embeddings

**Fonctionnalités validées** :
- ✓ Batch API call (1 appel pour N textes, max 100)
- ✓ Économie coûts (~50% vs appels individuels)
- ✓ Ordre préservé (embeddings correspondent aux textes)
- ✓ Gestion textes vides (filtrés)

**Fichiers testés** :
- `backend/app/services/rag_service.py` → `create_embeddings_batch()`

---

### Use Case 3 : Workflow Complet

**Fonctionnalités validées** :
- ✓ Chunking de texte (split avec overlap)
- ✓ Batch embeddings pour tous les chunks
- ✓ Stockage dans pgvector (PostgreSQL)
- ✓ Recherche sémantique (cosine similarity)
- ✓ Tri par score de similarité
- ✓ Filtrage par `document_type`

**Fichiers testés** :
- `backend/app/services/rag_service.py` → `ingest_document()`, `retrieve_relevant_content()`
- `backend/app/models/document.py` → `DocumentEmbedding`
- PostgreSQL pgvector → requêtes vectorielles

---

## 📈 Métriques de succès

| Métrique | Valeur attendue | Signification |
|----------|-----------------|---------------|
| **Embedding dimensions** | 1536 | text-embedding-3-small |
| **Cache hit speedup** | >90% | Redis plus rapide que API |
| **Batch API calls** | 1 pour N textes | Économie coûts |
| **Similarity score** | >0.7 | Matches pertinents |
| **Search time** | <200ms | Performance recherche |

---

## 📁 Fichiers de test

```
backend/tests/
├── __init__.py
├── check_prerequisites.py    # Vérification prérequis
├── run_rag_tests.py          # Tests automatisés (3 use cases)
└── README_RAG_TESTS.md       # Documentation détaillée
```

---

## 🔄 Progrès implémentation

### ✅ PHASE 1 - Embedding Engine (COMPLÈTE)

- [x] Task 1.1 : OpenAI Embeddings API réel
- [x] Task 1.2 : Version synchrone pour Celery
- [x] Task 1.3 : Batch embeddings
- [x] Task 1.4 : Cache Redis

**Tests disponibles** : ✅ 3 use cases automatisés

### ⏳ PHASE 2 - Smart Chunking (À venir)

- [ ] Task 2.1 : Chunking adaptatif par type de document

### ⏳ PHASE 3 - Pipeline Celery (À venir)

- [ ] Task 3.1 : Version sync ingest_document
- [ ] Task 3.2 : Étape 6 pipeline (suggestions KB)

### ⏳ PHASE 4 - API Endpoints (À venir)

- [ ] Task 4.1 : POST /search/semantic
- [ ] Task 4.2 : GET /criteria/{id}/suggestions

### ⏳ PHASE 5 - Reranking (À venir)

- [ ] Task 5.1 : Reranking métadonnées
- [ ] Task 5.2 : Reranking sémantique optionnel

---

## 🎉 Prochaines étapes

Après validation PHASE 1 :

1. **Commiter les changements**
   ```bash
   git add .
   git commit -m "feat(rag): PHASE 1 Embedding Engine complete with tests"
   git push origin feature/rag-service-implementation
   ```

2. **Passer à PHASE 2**
   - Implémenter chunking intelligent adaptatif
   - Tests pour différents types de documents

3. **Documentation**
   - Mettre à jour [ARCHITECTURE.md](ARCHITECTURE.md)
   - Documenter API embeddings dans OpenAPI

---

## 📞 Support

**Documentation complète** : [backend/tests/README_RAG_TESTS.md](backend/tests/README_RAG_TESTS.md)

**Plan d'implémentation** : [RAG_SERVICE_IMPLEMENTATION_PLAN.md](RAG_SERVICE_IMPLEMENTATION_PLAN.md)

**Questions/Issues** : Ouvrir une issue sur le repo
