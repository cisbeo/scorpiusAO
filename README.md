# ScorpiusAO

**AI Copilot for French Public Tender Bid Management**

Application IA destinée aux bid managers pour répondre aux appels d'offres publics français, spécialisée dans les infrastructures IT, l'hébergement datacenter et les services de support IT.

---

## 🎯 État du Projet

### ✅ Phase 1 - Backend MVP (COMPLÉTÉ)

**Extraction & Analyse de Documents**
- ✅ Upload et stockage PDF (MinIO)
- ✅ Extraction de texte multi-format (PyPDF2, pdfplumber, OCR Tesseract)
- ✅ Détection de structure hiérarchique (sections, TOC, numérotation)
- ✅ Détection automatique de sections clés (critères, processus ITIL, exclusions, pénalités)
- ✅ Optimisation hiérarchique pour LLM (-20% tokens)
- ✅ Analyse IA complète avec Claude Sonnet 4.5
- ✅ Extraction de critères structurés
- ✅ Pipeline asynchrone Celery robuste

**Infrastructure**
- ✅ Base de données PostgreSQL 15 + pgvector
- ✅ Redis cache (API responses + embeddings)
- ✅ RabbitMQ + Celery workers
- ✅ MinIO S3-compatible storage
- ✅ Docker Compose orchestration

**Résultats Validés (Test E2E)**
- 377 sections extraites du tender VSGP-AO
- 106 sections clés détectées (28%)
- 18/18 processus ITIL identifiés
- Analyse LLM: $0.12 (32k tokens input, 1.6k output)
- Économie structurelle: -20% tokens vs approche flat

### 🔨 Phase 2 - Améliorations en Cours

**Parsing Avancé de Tableaux** ([Issue #1](https://github.com/cisbeo/scorpiusAO/issues/1))
- 📋 3 solutions identifiées (enrichissement prompt, post-processing, Camelot)
- 📋 Documentation technique complète
- ⏳ Implémentation planifiée

**Tests & Qualité**
- ✅ Suite de tests E2E documentée ([scripts/tests/](scripts/tests/))
- ✅ Procédure de validation complète
- ✅ Scripts réutilisables pour CI/CD

### 🚧 Phase 3 - Prochaines Étapes

**RAG Service** (Priorité HAUTE)
- ⚠️ Structure implémentée, à compléter
- Embeddings OpenAI à intégrer
- Recherche vectorielle pgvector à tester

**API REST**
- ✅ Endpoints tenders CRUD
- ✅ Upload documents
- ✅ Déclenchement analyse
- ⏳ WebSocket pour notifications temps réel

**Frontend** (Non démarré)
- Dashboard tenders
- Interface upload documents
- Visualisation analyses
- Éditeur de réponses

---

## 🚀 Quick Start

### Prérequis

- Docker & Docker Compose
- Python 3.11+
- Clé API Anthropic (Claude)
- Clé API OpenAI (pour embeddings - optionnel)

### Installation

```bash
# Cloner le repo
git clone https://github.com/cisbeo/scorpiusAO.git
cd ScorpiusAO

# Configurer l'environnement
cd backend
cp .env.example .env
# Éditez .env avec vos clés API

# Démarrer l'infrastructure
docker-compose up -d

# Vérifier que tous les services sont actifs
docker-compose ps
```

### Accès aux Interfaces

- **API Documentation**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Flower (Celery)**: http://localhost:5555

### Test End-to-End

```bash
# Copier les PDFs de test
docker exec scorpius-celery-worker mkdir -p /app/real_pdfs
docker cp Examples/VSGP-AO/CCTP.pdf scorpius-celery-worker:/app/real_pdfs/
docker cp Examples/VSGP-AO/CCAP.pdf scorpius-celery-worker:/app/real_pdfs/
docker cp Examples/VSGP-AO/RC.pdf scorpius-celery-worker:/app/real_pdfs/

# Exécuter le test E2E complet
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_hierarchical_analysis.py
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py
```

Documentation complète: [scripts/tests/TEST_END_TO_END.md](scripts/tests/TEST_END_TO_END.md)

---

## 📁 Structure du Projet

```
ScorpiusAO/
├── backend/                          # API FastAPI + services Python
│   ├── app/
│   │   ├── api/v1/endpoints/        # Routes REST
│   │   │   ├── tenders.py           # CRUD tenders
│   │   │   ├── tender_documents.py  # Upload & gestion docs
│   │   │   ├── tender_analysis.py   # Analyse IA
│   │   │   └── analysis.py          # Status & résultats
│   │   ├── services/
│   │   │   ├── llm_service.py       # ✅ Claude API (async + sync)
│   │   │   ├── parser_service.py    # ✅ Extraction PDF + structure
│   │   │   ├── storage_service.py   # ✅ MinIO S3
│   │   │   └── rag_service.py       # ⚠️ Embeddings (à compléter)
│   │   ├── models/                  # ✅ SQLAlchemy ORM (9 tables)
│   │   ├── schemas/                 # ✅ Pydantic validation
│   │   ├── tasks/                   # ✅ Celery async pipeline
│   │   └── core/
│   │       ├── config.py            # Settings & env vars
│   │       └── prompts.py           # Templates LLM optimisés
│   ├── alembic/                     # Migrations DB (4 versions)
│   ├── docker-compose.yml           # Orchestration services
│   └── SOLUTIONS_PARSING_TABLEAUX.md # Doc technique parsing
├── scripts/tests/                   # ✅ Suite de tests E2E
│   ├── test_fresh_e2e.py
│   ├── test_llm_analysis.py
│   ├── test_hierarchical_analysis.py
│   ├── TEST_END_TO_END.md           # Guide complet
│   └── README.md
├── Examples/VSGP-AO/                # Documents de test réels
│   ├── CCTP.pdf (2.3 MB, 69 pages)
│   ├── CCAP.pdf (486 KB, 38 pages)
│   └── RC.pdf (256 KB, 12 pages)
├── ARCHITECTURE.md                  # Architecture technique détaillée
├── ROADMAP.md                       # Feuille de route
├── IMPLEMENTATION_SUMMARY.md        # Résumé implémentation
└── CLAUDE.md                        # Guide pour Claude Code
```

---

## 🛠️ Stack Technique

### Backend
- **API**: FastAPI (Python 3.11+) avec async/await
- **AI**: Claude Sonnet 4.5 (Anthropic) + prompt caching
- **Database**: PostgreSQL 15 + pgvector extension
- **Cache**: Redis 7 (API responses, embeddings)
- **Queue**: RabbitMQ + Celery workers
- **Storage**: MinIO (S3-compatible)
- **PDF Parsing**: PyPDF2, pdfplumber, Tesseract OCR

### Frontend (À venir)
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS + shadcn/ui
- React Query (cache)

---

## 🔧 Commandes Utiles

### Backend

```bash
cd backend

# Créer une migration
alembic revision --autogenerate -m "description"
alembic upgrade head

# Rollback
alembic downgrade -1

# Démarrer l'API (développement local)
uvicorn app.main:app --reload --port 8000

# Démarrer Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Tests
pytest
pytest --cov=app --cov-report=html
```

### Docker

```bash
cd backend

# Démarrer tous les services
docker-compose up -d

# Voir les logs d'un service
docker-compose logs -f celery-worker

# Rebuild après changements
docker-compose up -d --build

# Arrêter les services
docker-compose down

# Réinitialiser (supprime les données)
docker-compose down -v
```

### Tests E2E

```bash
# Test complet avec reset DB
./scripts/tests/reset_test_env.sh
./scripts/tests/run_e2e_test.sh

# Validation rapide de l'état actuel
./scripts/tests/quick_validate.sh

# Tests individuels
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py
```

---

## 🎯 Fonctionnalités

### ✅ Implémentées

**1. Analyse d'Appels d'Offres**
- Extraction automatique de structure hiérarchique
- Détection intelligente de sections clés (processus ITIL, exclusions, critères)
- Analyse IA complète (résumé, exigences, risques, délais)
- Extraction de critères d'évaluation avec poids
- Optimisation token (-20% via hiérarchie)

**2. Gestion de Documents**
- Upload PDF multi-documents
- Stockage sécurisé (MinIO)
- Extraction texte robuste (fallback OCR)
- Parsing tables (pdfplumber)
- Métadonnées automatiques

**3. Pipeline Asynchrone**
- Traitement parallèle documents
- Suivi progression temps réel (status)
- Retry automatique sur erreur
- Cache Redis pour performances

### 🚧 En Développement

**4. Amélioration Parsing Tableaux**
- Reconstruction markdown de tableaux complexes
- Post-processing spatial des cellules
- Fallback Camelot pour tables difficiles

**5. Base de Connaissances (RAG)**
- Embeddings OpenAI (à compléter)
- Recherche vectorielle pgvector
- Suggestions basées sur tenders passés

### 📋 Planifiées

**6. Génération de Réponses**
- Sections pré-remplies par IA
- Templates personnalisables
- Bibliothèque de contenu réutilisable
- Export Word/PDF

**7. Interface Web**
- Dashboard tenders
- Upload drag & drop
- Visualisation analyses
- Éditeur collaboratif

**8. Intégrations Externes**
- Scraper BOAMP automatique
- Connecteur AWS PLACE
- Notifications email

**9. Outils Avancés**
- Génération DUME/DC4 automatique
- Scoring simulation
- Mémo technique auto-généré

---

## 🔐 Configuration

### Variables d'Environnement

Copiez `.env.example` vers `.env` et configurez :

```bash
cd backend
cp .env.example .env
```

**Essentielles**:
```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI (pour embeddings)
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@postgres:5432/scorpius_db

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/1

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

**Optionnelles**:
```env
# Feature flags
ENABLE_HIERARCHICAL_OPTIMIZATION=true
ENABLE_OCR=true

# LLM settings
LLM_MODEL=claude-3-5-sonnet-20240620
MAX_TOKENS=8000
TEMPERATURE=0.2
```

---

## 📊 Performances

### Metrics Validées (Tender VSGP-AO)

| Métrique | Valeur | Notes |
|----------|--------|-------|
| **Documents traités** | 3 PDFs | CCTP (69p), CCAP (38p), RC (12p) |
| **Sections extraites** | 377 | Dont 135 TOC, 106 clés |
| **Processus ITIL détectés** | 18/18 | 100% recall |
| **Texte total** | ~270,000 chars | ~68k tokens |
| **Tokens LLM (optimisé)** | 32,637 input | -20% vs flat |
| **Coût analyse** | $0.12 | Claude Sonnet 4.5 |
| **Temps extraction** | ~45s | 3 docs en parallèle |
| **Temps analyse LLM** | ~8s | Avec prompt caching |

### Objectifs de Performance

- ✅ Extraction: < 2 min pour 3 documents (ATTEINT: 45s)
- ✅ Analyse LLM: < 15s (ATTEINT: 8s)
- ✅ Coût: < $0.20 par tender (ATTEINT: $0.12)
- ✅ Détection sections clés: > 90% recall (ATTEINT: 100% ITIL)
- ⏳ Parsing tableaux: > 80% qualité (EN COURS)

---

## 📚 Documentation

### Guides Principaux
- [CLAUDE.md](CLAUDE.md) - Instructions pour Claude Code
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture technique détaillée
- [ROADMAP.md](ROADMAP.md) - Feuille de route & priorités
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - État implémentation

### Documentation Technique
- [backend/SOLUTIONS_PARSING_TABLEAUX.md](backend/SOLUTIONS_PARSING_TABLEAUX.md) - Solutions parsing tableaux
- [scripts/tests/TEST_END_TO_END.md](scripts/tests/TEST_END_TO_END.md) - Procédure test E2E
- [scripts/tests/README.md](scripts/tests/README.md) - Guide scripts de test

### API Documentation
- **Swagger UI**: http://localhost:8000/docs (une fois l'API lancée)
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Tests

### Tests Unitaires

```bash
cd backend

# Tous les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Test spécifique
pytest tests/test_parser_service.py -v
```

### Tests End-to-End

```bash
# Test complet documenté
cd scripts/tests
./run_e2e_test.sh

# Tests individuels
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py
```

---

## 🤝 Contribution

### Workflow Git

```bash
# Créer une branche feature
git checkout -b feature/nom-fonctionnalite

# Commits
git add .
git commit -m "feat: description"

# Push et PR
git push origin feature/nom-fonctionnalite
```

### Standards Code

- Python: PEP 8 + type hints
- Docstrings: Google style
- Tests: pytest + coverage > 80%
- Commits: Conventional Commits

---

## 📝 License

Proprietary - All rights reserved

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/cisbeo/scorpiusAO/issues)
- **Documentation**: Voir fichiers `.md` à la racine du projet

---

**Dernière mise à jour**: 2 octobre 2025
**Version**: 0.2.0 (MVP Backend)
