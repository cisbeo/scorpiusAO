# ScorpiusAO

**AI Copilot for French Public Tender Bid Management**

Application IA destinée aux bid managers pour répondre aux appels d'offres publics français, spécialisée dans les infrastructures IT, l'hébergement datacenter et les services de support IT.

## 🚀 Quick Start

### Infrastructure lancée

Les services d'infrastructure Docker sont actuellement démarrés et opérationnels :

| Service | Status | Port | Interface |
|---------|--------|------|-----------|
| **PostgreSQL** (pgvector) | ✅ Healthy | 5433 | - |
| **Redis** | ✅ Healthy | 6379 | - |
| **RabbitMQ** | ✅ Healthy | 5672 | Management UI: http://localhost:15672 |
| **MinIO** | ✅ Healthy | 9000 | Console: http://localhost:9001 |

### Accès aux interfaces

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## 📁 Structure du projet

```
ScorpiusAO/
├── backend/              # API FastAPI + services Python
│   ├── app/
│   │   ├── api/v1/      # Endpoints REST
│   │   ├── services/    # LLM, RAG, Parser
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── tasks/       # Celery async tasks
│   ├── alembic/         # Database migrations
│   ├── tests/
│   └── docker-compose.yml
├── frontend/            # (À venir) Next.js + TypeScript
└── CLAUDE.md           # Documentation pour Claude Code

```

## 🛠️ Technologies

### Backend
- **API**: FastAPI (Python 3.11+)
- **AI**: Claude Sonnet 4.5, OpenAI Embeddings
- **Database**: PostgreSQL 15 + pgvector
- **Cache**: Redis 7
- **Queue**: RabbitMQ + Celery
- **Storage**: MinIO (S3-compatible)
- **OCR**: Tesseract

### Frontend (À venir)
- **Framework**: Next.js 14+
- **Language**: TypeScript
- **UI**: React + TailwindCSS

## 📋 Prochaines étapes

### Backend
1. ✅ Structure du projet créée
2. ✅ Services d'infrastructure lancés
3. ⏳ Créer les migrations de base de données
4. ⏳ Tester les endpoints API
5. ⏳ Implémenter les services (LLM, RAG, Parser)

### Frontend
1. ⏳ Initialiser le projet Next.js
2. ⏳ Créer les composants UI
3. ⏳ Intégrer avec l'API backend

## 🔧 Commandes utiles

### Backend

```bash
cd backend

# Créer et appliquer une migration
alembic revision --autogenerate -m "description"
alembic upgrade head

# Démarrer l'API (développement local)
uvicorn app.main:app --reload --port 8000

# Démarrer Celery worker (DÉVELOPPEMENT - mode solo pour compatibilité asyncio)
celery -A app.core.celery_app worker --pool=solo --loglevel=info

# Démarrer Celery worker (PRODUCTION - voir note ci-dessous)
# celery -A app.core.celery_app worker --loglevel=info

# Tests
pytest
pytest --cov=app
```

### ⚠️ Note importante sur Celery

**Mode actuel (Développement)**: `--pool=solo`
- Une seule tâche à la fois
- Compatible avec le code asyncio actuel
- Idéal pour tests et validation du workflow

**Migration vers Production** (TODO - voir section "Architecture Notes" ci-dessous):
- Refactoriser les tasks Celery en version synchrone
- Utiliser le mode `prefork` pour parallélisme
- Nécessite 2-4h de développement

### Docker

```bash
cd backend

# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down

# Réinitialiser (supprime les données)
docker-compose down -v
```

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - Guide complet pour Claude Code
- [Backend README](backend/README.md) - Documentation backend détaillée
- API Docs: http://localhost:8000/docs (une fois l'API lancée)

## 🎯 Fonctionnalités principales

1. **Analyse d'appels d'offres**
   - Extraction automatique des critères
   - Identification des documents obligatoires
   - Analyse des risques et dates limites

2. **Génération de réponses**
   - Sections générées par IA adaptées au contexte
   - Bibliothèque de réponses réutilisables
   - Vérification de conformité en temps réel

3. **Base de connaissances (RAG)**
   - Recherche sémantique dans les documents
   - Projets antérieurs et certifications
   - Références clients et études de cas

4. **Export de documents**
   - Génération DUME, DC4
   - Formats spécifiques aux plateformes
   - Mémoire technique complet

## 🔐 Configuration

Copiez `.env.example` vers `.env` et configurez vos clés API :

```bash
cd backend
cp .env.example .env
# Éditez .env avec vos clés API
```

Variables essentielles :
- `ANTHROPIC_API_KEY` - Clé API Claude
- `OPENAI_API_KEY` - Clé API OpenAI (pour embeddings)
- `DATABASE_URL` - Connexion PostgreSQL
- `REDIS_URL` - Connexion Redis

## 🏗️ Architecture Notes

### Celery + Asyncio: Migration Production

#### Problème actuel

Les tasks Celery utilisent du code asyncio (AsyncSession, asyncpg) qui n'est pas compatible avec le mode `prefork` multi-processus de Celery.

**Solution temporaire (dev)**: Mode `--pool=solo` (une seule tâche à la fois)

**Solution production**: Refactoriser les tasks en version synchrone

#### Plan de migration vers production

##### 1. Créer une session DB synchrone pour Celery

```python
# app/models/base.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Sync engine pour Celery tasks
sync_engine_celery = create_engine(
    settings.database_url_sync,  # postgresql://... (sans +asyncpg)
    pool_size=10,
    max_overflow=20,
    echo=settings.debug,
)

CelerySessionLocal = sessionmaker(
    sync_engine_celery,
    autocommit=False,
    autoflush=False,
)
```

##### 2. Refactoriser les tasks en sync

```python
# app/tasks/tender_tasks.py

@celery_app.task(bind=True, max_retries=3)
def process_tender_document(self, document_id: str):
    """Sync version - production ready."""
    try:
        # Utiliser session sync
        with CelerySessionLocal() as db:
            stmt = select(TenderDocument).where(TenderDocument.id == document_id)
            document = db.execute(stmt).scalar_one_or_none()

            # Storage service (déjà sync)
            file_content = storage_service.download_file(document.file_path)

            # Parser service (PyPDF2 est sync)
            extraction_result = parser_service.extract_from_pdf_sync(file_content)

            # LLM service - version sync
            if extraction_result["text"].strip():
                # Utiliser httpx ou requests au lieu de AsyncClient
                pass

            document.extracted_text = extraction_result["text"]
            db.commit()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

##### 3. Adapter les services

**LLM Service**: Créer version sync
```python
# app/services/llm_service.py

class LLMService:
    def __init__(self):
        # Version async (pour API FastAPI)
        self.async_client = anthropic.AsyncAnthropic(...)

        # Version sync (pour Celery)
        self.sync_client = anthropic.Anthropic(...)

    async def analyze_tender(self, content: str):
        """Version async pour API."""
        response = await self.async_client.messages.create(...)
        return response

    def analyze_tender_sync(self, content: str):
        """Version sync pour Celery tasks."""
        response = self.sync_client.messages.create(...)
        return response
```

**Parser Service**: Déjà majoritairement sync (PyPDF2)

**Storage Service**: Déjà sync (MinIO SDK)

##### 4. Avantages après migration

- ✅ Parallélisme complet (12+ workers)
- ✅ Scalabilité horizontale
- ✅ Performance production
- ✅ Gestion de charge élevée (50-100+ documents simultanés)

##### 5. Estimation

- **Temps**: 2-4 heures de développement
- **Complexité**: Moyenne
- **Risque**: Faible (pattern standard)
- **Tests**: Nécessaires pour validation

#### Pourquoi deux patterns (async API + sync Celery) ?

1. **API FastAPI** reste async:
   - Performance I/O élevée
   - Gestion efficace de milliers de requêtes HTTP concurrentes
   - Standard moderne Python

2. **Celery tasks** deviennent sync:
   - Compatible avec multiprocessing (prefork)
   - Pattern standard et robuste
   - Pas de problèmes d'event loop

C'est une architecture **hybride courante** dans les applications Python modernes.

## 📝 License

Proprietary - All rights reserved
