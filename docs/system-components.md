# System Components Documentation - ScorpiusAO

**Version:** 0.2.0
**Last Updated:** October 6, 2025
**Architecture Type:** Microservices with Event-Driven Processing

---

## 📋 Executive Summary

ScorpiusAO is an AI-powered copilot for managing French public tender bids. The system uses a microservices architecture orchestrated via Docker, with asynchronous task processing, vector search capabilities, and LLM-based analysis.

**Key Characteristics:**
- **Architecture Pattern:** Microservices + Event-Driven + RAG (Retrieval Augmented Generation)
- **Deployment:** Docker Compose orchestration
- **Data Flow:** Request → API → Worker Queue → AI Processing → Storage
- **Scalability:** Horizontal scaling via Celery workers
- **Primary Technologies:** FastAPI, PostgreSQL (pgvector), Redis, RabbitMQ, Claude AI, OpenAI Embeddings

---

## 🏗️ System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Frontend - Next.js]
    end

    subgraph "API Gateway"
        API[FastAPI Backend<br/>Port 8000]
    end

    subgraph "Core Services"
        LLM[LLM Service<br/>Claude Sonnet 4.5]
        RAG[RAG Service<br/>Embeddings + Search]
        PARSER[Parser Service<br/>PDF Extraction]
        STORAGE[Storage Service<br/>MinIO/S3]
        ARCHIVE[Archive Service<br/>Knowledge Base]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 15<br/>+ pgvector<br/>Port 5433)]
        REDIS[(Redis Cache<br/>Port 6379)]
        MINIO[(MinIO Object Storage<br/>Port 9000/9001)]
    end

    subgraph "Message Queue"
        RMQ[RabbitMQ<br/>Port 5672/15672]
        CELERY[Celery Workers<br/>Concurrency: 2]
        FLOWER[Flower Monitor<br/>Port 5555]
    end

    subgraph "External APIs"
        CLAUDE[Claude API<br/>Anthropic]
        OPENAI[OpenAI API<br/>Embeddings]
    end

    UI -->|HTTP/REST| API
    API --> LLM
    API --> RAG
    API --> PARSER
    API --> STORAGE
    API --> ARCHIVE

    LLM --> CLAUDE
    LLM --> REDIS
    RAG --> OPENAI
    RAG --> PG
    RAG --> REDIS
    PARSER --> MINIO
    STORAGE --> MINIO

    API -->|Queue Tasks| RMQ
    RMQ --> CELERY
    CELERY --> LLM
    CELERY --> RAG
    CELERY --> PARSER
    CELERY --> PG

    FLOWER -.Monitor.-> CELERY

    style API fill:#4CAF50
    style PG fill:#336791
    style REDIS fill:#DC382D
    style RMQ fill:#FF6600
    style CLAUDE fill:#8A2BE2
    style OPENAI fill:#00A67E
```

---

## 📦 Component Inventory

### 1. API Gateway Layer

#### 1.1 FastAPI Backend (API)
- **Purpose:** Central HTTP API gateway for all client requests
- **Technology:** FastAPI 0.109.0 + Uvicorn
- **Port:** 8000
- **Responsibilities:**
  - Request routing and validation
  - Authentication & authorization
  - CORS management
  - Response serialization (Pydantic schemas)
  - Health checks

**Key Endpoints:**
- `/api/v1/tenders/*` - Tender CRUD operations
- `/api/v1/tenders/{id}/ask` - RAG-based Q&A
- `/api/v1/analysis/*` - AI analysis results
- `/api/v1/proposals/*` - Proposal management
- `/api/v1/search/*` - Semantic search
- `/api/v1/archive/*` - Knowledge base access
- `/health` - System health check

**Dependencies:**
- PostgreSQL (data persistence)
- Redis (caching, session)
- RabbitMQ (task queuing)
- External AI APIs

**Configuration:**
- Environment: `.env` file
- CORS origins: Configurable list
- Rate limiting: 60 req/min (configurable)

---

### 2. Core Service Layer

#### 2.1 LLM Service
- **Purpose:** Manage Claude API interactions for AI analysis
- **Technology:** Anthropic SDK (anthropic==0.18.1)
- **Model:** Claude Sonnet 4.5 (claude-sonnet-4-20241022)

**Capabilities:**
1. **Tender Analysis** - Extract structured information from tender documents
2. **Criteria Extraction** - Identify evaluation criteria with weights
3. **Response Generation** - Generate proposal content
4. **Compliance Checking** - Validate proposals against requirements

**Caching Strategy:**
- Redis-based response caching (1 hour TTL)
- Cache key: SHA256 hash of input content
- 50% cost reduction via prompt caching
- Async and sync clients for API/Celery contexts

**Performance Metrics:**
- Analysis time: ~8s (target: <15s)
- Cost per tender: $0.12 (target: <$0.20)
- Cache hit latency: <100ms

**Error Handling:**
- Retry logic with exponential backoff (tenacity)
- Fallback to cached results on API failure
- Truncation for oversized content (>100k chars)

**Data Flow:**
```
Tender Content → Cache Check → Claude API → Parse Response → Cache Store → Return
```

#### 2.2 RAG Service (Retrieval Augmented Generation)
- **Purpose:** Semantic search and context retrieval using vector embeddings
- **Technology:** OpenAI Embeddings + pgvector
- **Embedding Model:** text-embedding-3-small (1536 dimensions)

**Capabilities:**
1. **Document Ingestion** - Chunk and embed documents
2. **Semantic Search** - Find relevant content via cosine similarity
3. **Q&A System** - Answer questions with source citations
4. **Similar Tender Search** - Find historically similar tenders

**Chunking Strategy:**
- **Semantic Chunking:** Merge small (<100 tokens), keep medium (100-1000), split large (>1000)
- Preserves section context and hierarchy
- Metadata enrichment (section numbers, page references)

**Search Pipeline:**
```
Question → Embed Query → Vector Search (pgvector) → Top-K Results →
LLM Answer Generation → Citations → Cache (1h TTL) → Response
```

**Performance Metrics:**
- Recall@5: 100% (target: >80%)
- Cost per tender: $0.016
- Q&A cache hit: <100ms
- Q&A cache miss: 3-4s

**Vector Index:**
- Type: IVFFlat (Inverted File with Flat compression)
- Distance metric: Cosine similarity
- Lists parameter: 100
- Optimal for datasets <1M vectors

#### 2.3 Parser Service
- **Purpose:** Extract text and structure from tender documents
- **Technology:** PyPDF2, pdfplumber, Tesseract OCR

**Extraction Capabilities:**
1. **Text Extraction** - Standard PDF text extraction
2. **OCR Fallback** - Tesseract for scanned documents
3. **Structure Detection** - Hierarchical section parsing
4. **Table Extraction** - Detect and parse tabular data
5. **Metadata Extraction** - Page counts, document info

**Section Detection:**
- Hierarchical numbering (1.2.3 format)
- Table of contents (TOC) identification
- Key section detection (18 ITIL process patterns)
- Parent-child relationship mapping

**Performance:**
- 3 documents: ~45s (target: <2 min)
- ITIL detection recall: 100%

**Data Structures:**
```json
{
  "text": "Full extracted text",
  "sections": [
    {
      "number": "1.2.3",
      "title": "Section Title",
      "content": "Content...",
      "level": 3,
      "parent_number": "1.2",
      "is_key_section": true,
      "page": 5
    }
  ],
  "tables": [...],
  "metadata": {...}
}
```

#### 2.4 Storage Service
- **Purpose:** Manage document file storage
- **Technology:** MinIO (S3-compatible)
- **Ports:** 9000 (API), 9001 (Console)

**Operations:**
- File upload/download
- Presigned URL generation
- Bucket management
- Metadata storage

**Bucket Structure:**
- `scorpius-documents` - Main document bucket
- Organized by: tender_id/document_type/filename

#### 2.5 Archive Service
- **Purpose:** Knowledge base management for past proposals, certifications, case studies
- **Status:** Planned (Sprint 2)

**Planned Features:**
- Document type classification
- Version control
- Search and retrieval
- Recommendation engine

---

### 3. Data Layer

#### 3.1 PostgreSQL Database (+ pgvector)
- **Purpose:** Primary data store with vector search capabilities
- **Technology:** PostgreSQL 15 + pgvector extension
- **Port:** 5433
- **Connection Pool:** 20 connections, max overflow 10

**Database Schema (9 Tables):**

1. **tenders** - Main tender records
   - Core fields: title, organization, reference_number, deadline, status
   - Relationships: documents, analysis, proposals, criteria

2. **tender_documents** - Uploaded tender files
   - Fields: filename, file_path, document_type, extracted_text
   - Extraction metadata: sections, tables, structured data
   - Status tracking: extraction_status, processing

3. **document_sections** - Hierarchical document structure
   - Fields: section_number, parent_number, parent_id, title, content
   - Metadata: level, page, line, is_key_section, is_toc
   - Self-referencing hierarchy via parent_id

4. **document_embeddings** - Vector embeddings (pgvector)
   ```sql
   CREATE TABLE document_embeddings (
       id UUID PRIMARY KEY,
       document_id UUID,
       document_type VARCHAR(50),
       chunk_text TEXT,
       embedding vector(1536),
       meta_data JSONB,
       created_at TIMESTAMP
   );

   CREATE INDEX idx_embeddings_cosine
   ON document_embeddings
   USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   ```

5. **tender_analysis** - AI analysis results
   - Structured data: summary, key_requirements, deadlines, risks
   - Technical/budget info, evaluation methods
   - Similar tenders (from RAG)

6. **tender_criteria** - Evaluation criteria
   - Fields: criterion_type, description, weight, is_mandatory
   - Metadata: evaluation_method, sub_criteria

7. **proposals** - Response proposals
   - Status tracking, content sections
   - Compliance score

8. **past_proposals** - Historical proposal archive (Sprint 2)

9. **historical_tenders** - Past tender archive

**Migrations:**
- Managed via Alembic
- Version control for schema changes
- Automatic migration on deployment

#### 3.2 Redis Cache
- **Purpose:** Multi-purpose caching and session storage
- **Technology:** Redis 7 Alpine
- **Port:** 6379

**Usage Patterns:**

1. **LLM Response Cache** (DB 0)
   - Key format: `tender_analysis:{content_hash}`
   - TTL: 1 hour
   - Size: Variable (JSON serialized)

2. **Q&A Cache** (DB 0)
   - Key format: `tender_qa:{tender_id}:{question_hash}`
   - TTL: 1 hour
   - Stores: Answer + sources + confidence

3. **Celery Results** (DB 1)
   - Task results and state
   - Managed by Celery backend

**Persistence:**
- AOF (Append-Only File) enabled
- Survives restarts

#### 3.3 MinIO Object Storage
- **Purpose:** S3-compatible document storage
- **Technology:** MinIO latest
- **Ports:** 9000 (API), 9001 (Console UI)
- **Credentials:** minioadmin/minioadmin

**Storage Organization:**
```
scorpius-documents/
├── {tender_id}/
│   ├── source/
│   │   └── {document_id}.pdf
│   ├── processed/
│   │   └── {document_id}_processed.json
│   └── exports/
│       └── {proposal_id}.docx
```

---

### 4. Message Queue & Task Processing

#### 4.1 RabbitMQ
- **Purpose:** Message broker for async task distribution
- **Technology:** RabbitMQ 3.12 Management Alpine
- **Ports:** 5672 (AMQP), 15672 (Management UI)
- **Credentials:** guest/guest

**Queue Structure:**
- `celery` - Default task queue
- Priority queues for urgent tasks (planned)
- Dead letter queue for failed tasks

**Message Flow:**
```
API Endpoint → Queue Task → RabbitMQ → Celery Worker → Execute → Update DB
```

#### 4.2 Celery Workers
- **Purpose:** Distributed async task execution
- **Technology:** Celery 5.3.6
- **Concurrency:** 2 workers (configurable)
- **Result Backend:** Redis DB 1

**Task Types:**

1. **process_tender_document** (Bind: True, Max Retries: 3)
   - Extract text from PDF
   - OCR fallback if needed
   - Save structured sections to DB
   - Update extraction status

2. **process_tender_documents** (Pipeline - 6 Steps)
   - Step 1: Extract content from all documents
   - Step 2: Create embeddings (RAG ingestion)
   - Step 3: AI analysis (Claude)
   - Step 4: Extract criteria
   - Step 5: Find similar tenders (RAG search)
   - Step 6: Save results & notify

3. **generate_proposal_section** (Planned)
4. **check_proposal_compliance** (Planned)
5. **ingest_knowledge_base_document** (Sprint 2)

**Retry Strategy:**
- Max retries: 3
- Backoff: Exponential (2^retries seconds)
- Failure handling: Update status to "failed" in DB

**Monitoring:**
- Flower UI (Port 5555)
- Real-time task tracking
- Worker health status
- Task history and metrics

---

### 5. External API Integration

#### 5.1 Claude API (Anthropic)
- **Purpose:** LLM-based text analysis and generation
- **Model:** claude-sonnet-4-20241022
- **Cost:** ~$0.12/tender analysis
- **Features Used:**
  - Prompt caching (50% cost reduction)
  - Structured JSON output
  - Long context window (200k tokens)

**API Quotas & Limits:**
- Rate limits: As per Anthropic tier
- Retry logic: Built-in via tenacity
- Circuit breaker: Planned for high-availability

#### 5.2 OpenAI API
- **Purpose:** Text embeddings for vector search
- **Model:** text-embedding-3-small
- **Dimensions:** 1536
- **Cost:** ~$0.016/tender (embeddings)

**Usage:**
- Document chunking embeddings
- Query embeddings for search
- Batch processing for efficiency

---

## 🔄 Data Flow Diagrams

### 5.1 Tender Upload & Analysis Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant MinIO
    participant RabbitMQ
    participant Celery
    participant Parser
    participant RAG
    participant LLM
    participant PostgreSQL
    participant Redis

    Client->>API: POST /tenders/upload (PDF)
    API->>MinIO: Store document
    API->>PostgreSQL: Create tender record
    API->>RabbitMQ: Queue process_tender_documents
    API-->>Client: 201 Created (tender_id)

    RabbitMQ->>Celery: Assign task to worker

    Note over Celery,PostgreSQL: STEP 1: Document Extraction
    Celery->>MinIO: Download PDF
    Celery->>Parser: Extract text + structure
    Parser-->>Celery: Sections, tables, metadata
    Celery->>PostgreSQL: Save sections to document_sections

    Note over Celery,PostgreSQL: STEP 2: Create Embeddings
    Celery->>RAG: Semantic chunking
    RAG-->>Celery: Chunks (100-1000 tokens)
    Celery->>RAG: Create embeddings (OpenAI)
    RAG->>PostgreSQL: Store in document_embeddings

    Note over Celery,PostgreSQL: STEP 3: AI Analysis
    Celery->>Redis: Check cache
    Redis-->>Celery: Cache miss
    Celery->>LLM: Analyze tender (Claude)
    LLM-->>Celery: Analysis results
    Celery->>Redis: Cache results (1h TTL)
    Celery->>PostgreSQL: Save to tender_analysis

    Note over Celery,PostgreSQL: STEP 4: Extract Criteria
    Celery->>LLM: Extract evaluation criteria
    LLM-->>Celery: Criteria list
    Celery->>PostgreSQL: Save to tender_criteria

    Note over Celery,PostgreSQL: STEP 5: Find Similar Tenders
    Celery->>RAG: Vector similarity search
    RAG->>PostgreSQL: Query embeddings
    PostgreSQL-->>RAG: Top 5 matches
    RAG-->>Celery: Similar tenders
    Celery->>PostgreSQL: Update tender_analysis

    Note over Celery,PostgreSQL: STEP 6: Finalize
    Celery->>PostgreSQL: Set status = "analyzed"
    Celery-->>Client: WebSocket notification (planned)
```

### 5.2 Q&A Flow (RAG-based)

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Redis
    participant RAG
    participant PostgreSQL
    participant OpenAI
    participant Claude

    Client->>API: POST /tenders/{id}/ask
    API->>Redis: Check cache (question_hash)

    alt Cache Hit
        Redis-->>API: Cached answer + sources
        API-->>Client: Response (cached: true)
    else Cache Miss
        API->>RAG: Create query embedding
        RAG->>OpenAI: Embed question
        OpenAI-->>RAG: Query vector [1536]

        RAG->>PostgreSQL: Vector similarity search (top_k=5)
        PostgreSQL-->>RAG: Top 5 relevant chunks

        RAG->>Claude: Generate answer (prompt + context)
        Claude-->>RAG: Answer + reasoning

        RAG->>API: Format response with sources
        API->>Redis: Cache result (1h TTL)
        API-->>Client: Response (cached: false)
    end
```

---

## 🔧 Configuration Management

### Environment Variables (.env)

**Application Config:**
```bash
APP_NAME=ScorpiusAO
APP_VERSION=0.2.0
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Database Config:**
```bash
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

**Cache & Queue:**
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

**AI APIs:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
LLM_MODEL=claude-sonnet-4-20241022
EMBEDDING_MODEL=text-embedding-3-small
MAX_TOKENS=4096
TEMPERATURE=0.7
```

**Storage:**
```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=scorpius-documents
MINIO_SECURE=false
```

**Security:**
```bash
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Monitoring:**
```bash
SENTRY_DSN=https://...  # Optional
RATE_LIMIT_PER_MINUTE=60
```

### Docker Compose Configuration

**Service Dependencies:**
```yaml
api:
  depends_on:
    postgres: {condition: service_healthy}
    redis: {condition: service_healthy}
    rabbitmq: {condition: service_healthy}

celery-worker:
  depends_on:
    postgres: {condition: service_healthy}
    redis: {condition: service_healthy}
    rabbitmq: {condition: service_healthy}
```

**Health Checks:**
- PostgreSQL: `pg_isready` (10s interval)
- Redis: `redis-cli ping` (10s interval)
- RabbitMQ: `rabbitmq-diagnostics ping` (10s interval)
- MinIO: `curl /minio/health/live` (10s interval)

---

## 📊 Performance & Scalability

### Current Performance Metrics

| Component | Metric | Target | Current | Status |
|-----------|--------|--------|---------|--------|
| RAG Q&A | Recall@5 | >80% | 100% | ✅ |
| RAG Q&A | Cost/tender | <$0.02 | $0.016 | ✅ |
| RAG Q&A | Cache hit | <100ms | <100ms | ✅ |
| RAG Q&A | Cache miss | <5s | 3-4s | ✅ |
| LLM Analysis | Time | <15s | 8s | ✅ |
| LLM Analysis | Cost | <$0.20 | $0.12 | ✅ |
| Parser | 3 docs | <2min | 45s | ✅ |
| Pipeline | Full analysis | <5min | ~2min | ✅ |

### Scalability Considerations

**Horizontal Scaling:**
1. **API Layer:**
   - Stateless design enables load balancing
   - Deploy multiple FastAPI instances behind nginx/traefik
   - Session data in Redis (shared state)

2. **Worker Layer:**
   - Increase Celery concurrency per worker
   - Deploy multiple worker containers
   - Auto-scaling based on queue depth

3. **Database Layer:**
   - Read replicas for analytics queries
   - Connection pooling (current: 20 + 10 overflow)
   - Partition large tables (embeddings) by date

4. **Cache Layer:**
   - Redis Cluster for distributed caching
   - Separate cache instances per service
   - TTL optimization (current: 1h for Q&A)

**Vertical Scaling:**
- Increase worker concurrency (current: 2)
- Larger PostgreSQL instances for vector ops
- More Redis memory for cache hit rate

**Bottleneck Analysis:**

1. **Potential Bottlenecks:**
   - Vector search on large datasets (>1M embeddings)
   - Claude API rate limits during peak
   - PDF parsing for very large documents (>500 pages)
   - Concurrent writes to PostgreSQL

2. **Mitigation Strategies:**
   - Implement vector index partitioning
   - Request batching for Claude API
   - Document chunking for large files
   - Write queue with batch inserts

---

## 🛡️ Error Handling & Logging

### Error Handling Strategy

**API Layer (FastAPI):**
- HTTP exception handlers for 4xx/5xx errors
- Validation errors via Pydantic
- Custom exception classes for business logic

**Service Layer:**
- Try-except blocks with specific error types
- Fallback to cached data on external API failure
- Graceful degradation (e.g., skip embeddings if OpenAI down)

**Worker Layer (Celery):**
- Task retry with exponential backoff (max 3 retries)
- Status tracking in database (failed/processing/completed)
- Dead letter queue for unrecoverable failures

### Logging Architecture

**Current Implementation:**
- Python print statements (to be replaced)
- Celery task logs
- Docker container logs

**Planned Enhancement (using structlog):**

```python
# Structured logging example
logger.info("tender_analysis_complete",
    tender_id=tender_id,
    processing_time=8.2,
    cost=0.12,
    sections_analyzed=377,
    criteria_extracted=15
)
```

**Log Levels:**
- DEBUG: Detailed diagnostic info
- INFO: General operational events
- WARNING: Non-critical issues (fallbacks, retries)
- ERROR: Failures requiring attention
- CRITICAL: System-wide failures

**Log Aggregation (Planned):**
- Sentry for error tracking (sentry_dsn configured)
- ELK stack for centralized logging
- CloudWatch/Datadog for production monitoring

**Monitoring Dashboard (Planned):**
- Grafana for metrics visualization
- Prometheus for time-series data
- Flower for Celery monitoring (currently available at :5555)

---

## 🚀 Deployment Topology

### Development Environment

```
┌─────────────────────────────────────────┐
│          Developer Machine               │
│                                          │
│  ┌──────────┐  ┌──────────────────────┐ │
│  │  VS Code │  │  Docker Desktop      │ │
│  └──────────┘  │                      │ │
│                │  ┌────────────────┐  │ │
│                │  │ docker-compose │  │ │
│                │  │   8 services   │  │ │
│                │  └────────────────┘  │ │
│                └──────────────────────┘ │
└─────────────────────────────────────────┘
         │
         │ Hot reload (volumes)
         ↓
    ./backend/app/
```

**Services Running:**
- postgres:5433
- redis:6379
- rabbitmq:5672,15672
- minio:9000,9001
- api:8000
- celery-worker
- flower:5555
- elasticsearch:9200 (optional)

### Staging/Production (Planned)

```
┌─────────────────────────────────────────────────┐
│              Load Balancer (nginx/ALB)          │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
    ┌───▼────┐                 ┌────▼───┐
    │  API   │                 │  API   │
    │Instance│                 │Instance│
    └───┬────┘                 └────┬───┘
        │                           │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────────┐
        │      RabbitMQ Cluster          │
        └─────────────┬─────────────────┘
                      │
        ┌─────────────▼─────────────────┐
        │    Celery Worker Pool (3+)    │
        └───────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
    ┌───▼────────┐            ┌─────▼──────┐
    │ PostgreSQL │            │   Redis    │
    │  (RDS/HA)  │            │  Cluster   │
    └────────────┘            └────────────┘
```

**Infrastructure:**
- Kubernetes or ECS for container orchestration
- Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- Managed Redis (ElastiCache, MemoryStore)
- S3/GCS for object storage (replace MinIO)
- Secrets management (AWS Secrets Manager, Vault)

---

## 🔐 Security Considerations

### Authentication & Authorization
- **Current:** Basic secret key authentication (planned)
- **Planned:**
  - JWT tokens (python-jose)
  - OAuth2/OIDC integration
  - API key management
  - Role-based access control (RBAC)

### Data Security
- **In Transit:** HTTPS/TLS for API
- **At Rest:** Encrypted database volumes (production)
- **Secrets:** Environment variables, secrets manager (production)

### API Security
- Rate limiting (60 req/min configured)
- CORS whitelist
- Input validation (Pydantic)
- SQL injection prevention (SQLAlchemy ORM)

### External API Security
- API key rotation strategy
- Separate keys per environment
- Monitoring for suspicious usage patterns

---

## 🔮 Future Enhancements

### Phase 2 (Sprint 2) - Knowledge Base
- Archive service implementation
- Past proposals, certifications, case studies ingestion
- Enhanced RAG with reranking
- Pre-calculated FAQ (20-30 questions)

### Phase 3 (Sprint 3-4) - Advanced Analysis
- Multi-pass analysis (Solution 6)
- Contradiction detection
- Adaptive complexity scoring
- A/B testing framework

### Monitoring & Observability
- Distributed tracing (OpenTelemetry)
- APM integration (Datadog, New Relic)
- Custom business metrics dashboard
- Alert system for SLA violations

### Performance Optimization
- Read replicas for PostgreSQL
- CDN for static assets
- GraphQL API (alternative to REST)
- WebSocket support for real-time updates

---

## 📚 API Reference Summary

### Core Endpoints

**Tenders:**
- `POST /api/v1/tenders/` - Create tender
- `POST /api/v1/tenders/upload` - Upload PDF
- `GET /api/v1/tenders/` - List tenders
- `GET /api/v1/tenders/{id}` - Get details
- `POST /api/v1/tenders/{id}/ask` - Q&A (RAG)

**Analysis:**
- `GET /api/v1/analysis/tenders/{id}` - Get analysis
- `GET /api/v1/analysis/tenders/{id}/criteria` - Get criteria
- `POST /api/v1/analysis/tenders/{id}/reanalyze` - Re-analyze

**Proposals:**
- `POST /api/v1/proposals/` - Create proposal
- `GET /api/v1/proposals/tender/{id}` - List proposals
- `POST /api/v1/proposals/{id}/sections/generate` - Generate section
- `POST /api/v1/proposals/{id}/compliance-check` - Check compliance

**Search:**
- `POST /api/v1/search/` - Semantic search
- `GET /api/v1/search/similar-tenders/{id}` - Find similar

**Archive:**
- Knowledge base endpoints (planned)

**System:**
- `GET /health` - Health check

---

## 🎯 Key Takeaways

### System Strengths
✅ **Modular Architecture** - Clear separation of concerns
✅ **Async Processing** - Non-blocking operations via Celery
✅ **AI-Powered** - Advanced RAG + LLM capabilities
✅ **Scalable Design** - Horizontal scaling ready
✅ **Cost Optimized** - Caching reduces API costs by 50%
✅ **High Accuracy** - 100% recall on key section detection

### Current Limitations
⚠️ **Logging** - Basic print statements, needs structured logging
⚠️ **Monitoring** - Limited observability (Flower only)
⚠️ **Auth** - Basic authentication, needs OAuth2/JWT
⚠️ **Frontend** - Not yet implemented
⚠️ **Scale Testing** - Not tested beyond development workloads

### Recommended Actions
1. **Immediate:** Implement structured logging (structlog + Sentry)
2. **Short-term:** Add comprehensive monitoring (Prometheus + Grafana)
3. **Medium-term:** Implement OAuth2 authentication
4. **Long-term:** Kubernetes deployment + auto-scaling

---

**Document Maintained By:** System Architecture Team
**Review Frequency:** Monthly or on major changes
**Related Documentation:**
- `/Users/cedric/Dev/projects/ScorpiusAO/ARCHITECTURE.md` - High-level architecture
- `/Users/cedric/Dev/projects/ScorpiusAO/ROADMAP.md` - Product roadmap
- `/Users/cedric/Dev/projects/ScorpiusAO/backend/README.md` - Backend setup guide
- `/Users/cedric/Dev/projects/ScorpiusAO/docs/RAG_SERVICE_PLAN_V2.md` - RAG service details
