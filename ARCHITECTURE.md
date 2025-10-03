# 🏗️ Architecture ScorpiusAO

**Version**: 0.2.0 (MVP Backend + RAG Service)  
**Dernière mise à jour**: 3 octobre 2025

---

## 📋 Vue d'ensemble

ScorpiusAO est un AI copilot pour bid managers répondant aux appels d'offres publics français. Architecture microservices avec orchestration Docker, RAG vectoriel, et pipeline asynchrone Celery.

### Stack Technologique

| Composant | Technologie | Usage |
|-----------|-------------|-------|
| **API** | FastAPI + Uvicorn | REST API async |
| **Database** | PostgreSQL 15 + pgvector | Données + embeddings vectoriels |
| **Cache** | Redis 7 | LLM cache + Q&A cache |
| **Queue** | RabbitMQ 3.12 | Message broker Celery |
| **Worker** | Celery 5.3 | Processing async |
| **Storage** | MinIO | S3-compatible storage |
| **LLM** | Claude Sonnet 4.5 | Analyse IA |
| **Embeddings** | OpenAI text-embedding-3-small | Vectorisation (1536 dim) |

---

## 🏗️ Architecture Globale

```
┌──────────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                     │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP/REST
                        ↓
┌──────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │  Tenders   │  │ Documents  │  │    Q&A     │         │
│  │ Endpoints  │  │ Endpoints  │  │  Endpoint  │         │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘         │
│        └────────────────┴───────────────┘                │
│                         │                                │
│         ┌───────────────┴────────────────┐               │
│         ↓                                ↓               │
│  ┌─────────────┐                 ┌──────────────┐       │
│  │  Services   │                 │   Models     │       │
│  │  (LLM/RAG)  │                 │   (ORM)      │       │
│  └─────────────┘                 └──────────────┘       │
└──────────────────────────────────────────────────────────┘
         │                                 │
         ↓                                 ↓
┌──────────────────┐           ┌─────────────────────┐
│  External APIs   │           │  PostgreSQL + pgvec │
│  • Claude API    │           │  • tenders          │
│  • OpenAI API    │           │  • documents        │
└──────────────────┘           │  • embeddings       │
         │                     └─────────────────────┘
         ↓                                 │
┌──────────────────┐                       │
│  Redis Cache     │←──────────────────────┘
│  • LLM responses │
│  • Q&A (1h TTL)  │
└────────┬─────────┘
         │
┌────────▼─────────┐
│    RabbitMQ      │
│  Message Broker  │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐           ┌─────────────────────┐
│ Celery Workers   │───────────│  MinIO Storage      │
│ • process_tender │           │  (S3-compatible)    │
│ • create_embed   │           └─────────────────────┘
└──────────────────┘
```

---

## 🔧 Services Backend

### 1. RAG Service - Q&A sur Tender

**Status**: ✅ Implémenté (3 oct 2025) - Solution 5.5

**Endpoint**:
```
POST /api/v1/tenders/{tender_id}/ask
Body: {"question": "Quelle est la durée du marché?", "top_k": 5}
```

**Fonctionnalités**:
- Chunking sémantique (merge <100, keep 100-1000, split >1000 tokens)
- Embeddings OpenAI text-embedding-3-small (1536 dim)
- Recherche vectorielle pgvector (cosine similarity)
- Génération réponse Claude Sonnet 4.5
- Cache Redis 1h TTL
- Citations sources avec sections

**Métriques validées**:
- Recall@5: 100% (objectif: >80%) ✅
- Answer Quality: 80% ✅
- Coût: $0.016/tender ✅
- Temps: <100ms (cache hit), 3-4s (cache miss) ✅

**Exemple**:
```bash
curl -X POST 'http://localhost:8000/api/v1/tenders/{id}/ask' \
  -H 'Content-Type: application/json' \
  -d '{"question": "Quelle est la durée du marché?", "top_k": 5}'
```

**Réponse**:
```json
{
  "question": "Quelle est la durée du marché?",
  "answer": "Le marché est conclu pour 4 ans...",
  "sources": [
    {
      "document_id": "...",
      "chunk_text": "Section 1: Durée du marché...",
      "similarity_score": 0.95,
      "metadata": {"section_number": "1", "page": 1}
    }
  ],
  "confidence": 0.92,
  "cached": false
}
```

### 2. LLM Service

**Fonctionnalités**:
- Analyse tender avec Claude Sonnet 4.5
- Cache Redis pour économies API
- Prompt caching (50% économies)

**Métriques**:
- Temps: 8s (objectif: <15s) ✅
- Coût: $0.12/tender ✅

### 3. Parser Service

**Fonctionnalités**:
- Extraction PDF (PyPDF2, pdfplumber)
- Détection structure hiérarchique
- OCR Tesseract

**Métriques**:
- Extraction 3 docs: 45s ✅
- Détection ITIL: 100% recall ✅

---

## 💾 Base de Données

### Table: `document_embeddings` (pgvector)

```sql
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY,
    document_id UUID,
    document_type VARCHAR(50), -- "tender", "past_proposal", etc.
    chunk_text TEXT NOT NULL,
    embedding vector(1536),    -- OpenAI embeddings
    meta_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour recherche vectorielle
CREATE INDEX idx_embeddings_cosine
ON document_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Types de documents**:
- ✅ `"tender"` - Embeddings des tenders actuels (Q&A)
- ⏳ `"past_proposal"` - Propositions gagnantes (Sprint 2)
- ⏳ `"case_study"` - Cas clients (Sprint 2)
- ⏳ `"certification"` - Certifications (Sprint 2)

---

## 🔄 Pipeline Celery

### Tâche: `process_new_tender`

**6 étapes**:

1. **STEP 1**: Parse documents → Sections structurées
2. **STEP 2**: ✅ Create embeddings (RAG)
   ```python
   chunks = rag_service.chunk_sections_semantic(sections)
   rag_service.ingest_document_sync(db, doc_id, chunks, "tender")
   ```
3. **STEP 3**: Analyze with LLM (Claude)
4. **STEP 4**: Extract criteria
5. **STEP 5**: ✅ Find similar tenders (RAG)
   ```python
   similar = rag_service.find_similar_tenders_sync(db, tender_id, limit=5)
   ```
6. **STEP 6**: Save & notify

---

## 🚀 Déploiement Docker

### Services

```yaml
services:
  postgres:       # Port 5433 (pgvector)
  redis:          # Port 6379
  rabbitmq:       # Ports 5672, 15672
  minio:          # Ports 9000, 9001
  api:            # Port 8000
  celery-worker:  # Concurrency: 2
  flower:         # Port 5555 (monitoring)
```

### Commandes

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f api

# Arrêter
docker-compose down
```

---

## 📊 Métriques & Performances

| Composant | Métrique | Objectif | Actuel | Status |
|-----------|----------|----------|--------|--------|
| RAG Q&A | Recall@5 | >80% | 100% | ✅ |
| RAG Q&A | Coût | <$0.02 | $0.016 | ✅ |
| RAG Q&A | Cache hit | <100ms | <100ms | ✅ |
| RAG Q&A | Cache miss | <5s | 3-4s | ✅ |
| LLM | Analyse | <15s | 8s | ✅ |
| LLM | Coût | <$0.20 | $0.12 | ✅ |
| Parser | 3 docs | <2min | 45s | ✅ |

---

## 🔮 Roadmap

### ✅ Sprint 1-2 (Actuel)
- ✅ RAG Service Q&A opérationnel
- ✅ Tests E2E validés (recall@5: 100%)
- ✅ Pipeline Celery intégré
- [ ] Frontend Dashboard React
- [ ] Composant Chat Q&A

### ⏳ Sprint 2
- [ ] Knowledge Base (past_proposals, case_studies)
- [ ] FAQ pré-calculée (20-30 questions)
- [ ] Response Generation with RAG
- [ ] Re-ranking (optionnel)

### ⏳ Sprint 3-4
- [ ] Solution 6 Multi-Passes (analyse 377 sections)
- [ ] Détection contradictions
- [ ] A/B testing

---

## 📚 Documentation

- **ROADMAP.md**: Plan général projet
- **CLAUDE.md**: Guide développeur
- **backend/docs/RAG_SERVICE_DAY3_REPORT.md**: Tests RAG
- **docs/RAG_SERVICE_PLAN_V2.md**: Plan implémentation RAG

---

**Dernière mise à jour**: 3 octobre 2025  
**Status**: MVP Backend + RAG Service Q&A ✅
