# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScorpiusAO is an AI copilot application for bid managers responding to French public procurement tenders (appels d'offres publics), specifically focused on IT infrastructure, datacenter hosting, and IT support services.

## Business Context

### Bid Manager Challenges
- **Document Volume**: Complex technical specifications requiring thorough analysis
- **Time Constraints**: Tight response deadlines (typically 30-45 days)
- **Compliance**: Strict criteria adherence (DUME, DC4, mandatory certifications)
- **Repetition**: Need to reuse winning content from past bids
- **Coordination**: Multi-stakeholder input (technical, legal, financial teams)

### Target Platforms
- **BOAMP** (Bulletin Officiel des Annonces des Marchés Publics)
- **AWS PLACE** (Plateforme des Achats de l'État)
- Regional public procurement platforms

## Architecture

### Technology Stack
- **API**: FastAPI (Python 3.11+) with async/await
- **AI Orchestration**: Claude API (Sonnet 4.5) + custom RAG
- **Frontend**: Next.js 14+ with TypeScript
- **Database**: PostgreSQL 15+ with pgvector extension
- **Cache**: Redis 7+ for sessions and API responses
- **Message Queue**: RabbitMQ for async task processing
- **Task Worker**: Celery with Flower monitoring
- **Search**: Elasticsearch for full-text search
- **Storage**: MinIO (S3-compatible) for document storage
- **Reverse Proxy**: Nginx
- **OCR**: Tesseract for scanned documents

### Backend Structure
```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── tenders.py          # Tender CRUD operations
│   │   │   │   ├── analysis.py         # AI analysis endpoints
│   │   │   │   ├── documents.py        # Upload & parsing
│   │   │   │   ├── proposals.py        # Response generation
│   │   │   │   └── search.py           # RAG search
│   │   │   └── api.py                  # Router aggregation
│   │   └── dependencies.py             # FastAPI dependencies
│   ├── core/
│   │   ├── config.py                   # Settings & environment
│   │   ├── security.py                 # Auth & RBAC
│   │   └── prompts.py                  # LLM prompt templates
│   ├── services/
│   │   ├── llm_service.py              # Claude API integration
│   │   ├── rag_service.py              # RAG & embeddings
│   │   ├── parser_service.py           # Document parsing
│   │   └── integration_service.py      # External APIs (BOAMP, etc.)
│   ├── models/                         # SQLAlchemy ORM models
│   ├── schemas/                        # Pydantic validation schemas
│   ├── tasks/                          # Celery async tasks
│   └── utils/                          # Helper utilities
├── tests/
├── alembic/                            # Database migrations
├── docker-compose.yml
└── requirements.txt
```

### Core Services

#### LLM Service (`llm_service.py`)
Handles all Claude API interactions with caching and retry logic:
- `analyze_tender()`: Extract criteria, deadlines, requirements
- `generate_response_section()`: Create tender response sections
- `check_compliance()`: Validate response against requirements
- Implements prompt caching to reduce API costs

#### RAG Service (`rag_service.py`)
Semantic search over company knowledge base:
- `ingest_document()`: Chunk and embed documents into pgvector
- `retrieve_relevant_content()`: Semantic search with top-k results
- `rerank_results()`: Reranking for improved relevance
- Handles embeddings for past tenders, certifications, case studies

#### Parser Service (`parser_service.py`)
Multi-format document extraction:
- PDF text extraction (PyPDF2, pdfplumber)
- OCR for scanned documents (Tesseract)
- Structure detection (headers, tables, criteria lists)
- Metadata extraction (deadlines, organization, contact info)

#### Integration Service (`integration_service.py`)
External platform connectors:
- BOAMP API scraping
- AWS PLACE integration
- Automated tender monitoring
- Notification system

### Database Schema (PostgreSQL)

```sql
-- Tenders table
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    organization VARCHAR(200),
    reference_number VARCHAR(100),
    deadline TIMESTAMP,
    raw_content TEXT,
    parsed_content JSONB,
    status VARCHAR(50) DEFAULT 'new',
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Proposals (responses to tenders)
CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    sections JSONB,
    compliance_score FLOAT,
    status VARCHAR(50) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Vector embeddings (pgvector)
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID,
    document_type VARCHAR(50),
    chunk_text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embeddings_cosine
ON document_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Criteria extracted from tenders
CREATE TABLE tender_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID REFERENCES tenders(id) ON DELETE CASCADE,
    criterion_type VARCHAR(50),
    description TEXT,
    weight FLOAT,
    is_mandatory BOOLEAN DEFAULT false,
    metadata JSONB
);
```

### Async Task Pipeline (Celery)

```python
@celery_app.task(bind=True, max_retries=3)
def process_new_tender(self, tender_id: str):
    """Complete tender processing pipeline"""
    # 1. Parse document
    content = parser_service.extract_content(tender_id)

    # 2. Create embeddings
    rag_service.ingest_document(tender_id, content)

    # 3. AI analysis
    analysis = llm_service.analyze_tender(content)

    # 4. Extract criteria
    criteria = llm_service.extract_criteria(content)

    # 5. Find similar past tenders
    similar = rag_service.find_similar_tenders(tender_id)

    # 6. Save & notify
    save_analysis(tender_id, analysis, criteria, similar)
    notify_user_via_websocket(tender_id)
```

### Optimization Strategies

#### Performance
- Redis caching with adaptive TTL based on query frequency
- PostgreSQL connection pooling (pgbouncer)
- Lazy loading of embeddings (load on-demand)
- GZIP compression on API responses
- CDN for static assets

#### AI Cost Reduction
- Prompt caching for recurring templates (50%+ savings)
- Optimal chunking strategy (512-1024 tokens per chunk)
- Batch embedding requests
- Fallback to smaller models for simple tasks
- Response streaming for better UX

#### Scalability
- Horizontal scaling of Celery workers
- Database partitioning by date for tenders table
- Vector index optimization (IVFFlat with 100 lists)
- Rate limiting per user/organization
- Request queuing during high load

## Commands

### Development Setup
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d postgres redis rabbitmq minio

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start Flower monitoring
celery -A app.tasks.celery_app flower --port=5555
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tender_parser.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run single test
pytest -k "test_extract_criteria"
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Reset database (dev only)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

### Docker Operations
```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Reset everything (caution: deletes data)
docker-compose down -v
```

## Core Features
1. **Tender Analysis**: Extract criteria, deadlines, mandatory documents
2. **Response Generation**: AI-powered section generation with company context
3. **Response Library**: Searchable database of past winning responses
4. **Compliance Checking**: Real-time validation against requirements
5. **Technical Memorandum**: Automated generation with customization
6. **Scoring Simulation**: Predict evaluation scores
7. **Knowledge Base**: RAG over certifications, references, case studies
8. **Document Export**: Generate DUME, DC4, and platform-specific formats

## Development Status

Project initialization in progress. Architecture defined, implementing backend structure.
