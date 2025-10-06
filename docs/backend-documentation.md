# ScorpiusAO Backend - Technical Documentation

**Version:** 0.1.0
**Framework:** FastAPI (Python)
**Generated:** 2025-10-06

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Database Models](#database-models)
6. [API Endpoints](#api-endpoints)
7. [Services Layer](#services-layer)
8. [Background Tasks](#background-tasks)
9. [Configuration](#configuration)
10. [Dependencies](#dependencies)

---

## 1. Project Overview

**ScorpiusAO** is an AI-powered Copilot for French Public Tender Bid Management. The backend provides intelligent tender analysis, document processing, RAG (Retrieval Augmented Generation) capabilities, and automated proposal generation.

### Key Features

- **Document Processing**: PDF parsing with text extraction, OCR support, and structured section detection
- **AI Analysis**: Claude AI integration for tender analysis, criteria extraction, and compliance checking
- **RAG System**: Vector embeddings with pgvector for semantic search and knowledge base
- **Archiving**: Historical tender/proposal management with embedding generation for knowledge base
- **Async Processing**: Celery-based background tasks for heavy operations
- **Real-time Updates**: Redis caching and WebSocket support (planned)

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   FastAPI    │─────▶│  PostgreSQL │
│   (React)   │      │   Backend    │      │  + pgvector │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ├─────▶ Redis (Cache)
                            │
                            ├─────▶ MinIO (Storage)
                            │
                            ├─────▶ Celery (Tasks)
                            │
                            ├─────▶ Claude API (LLM)
                            │
                            └─────▶ OpenAI (Embeddings)
```

### Service-Oriented Architecture

- **API Layer**: FastAPI routes and endpoints
- **Service Layer**: Business logic and external integrations
- **Data Layer**: SQLAlchemy models and database operations
- **Task Layer**: Celery workers for async processing
- **Storage Layer**: MinIO for file storage

---

## 3. Technology Stack

### Core Framework

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Web Framework** | FastAPI | 0.109.0 | Async API server |
| **ASGI Server** | Uvicorn | 0.27.0 | Production server |
| **ORM** | SQLAlchemy | 2.0.25 | Database abstraction |
| **Migrations** | Alembic | 1.13.1 | Schema versioning |

### Data & Storage

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Database** | PostgreSQL | - | Primary database |
| **Vector DB** | pgvector | 0.2.4 | Vector embeddings |
| **Cache** | Redis | 5.0.1 | Caching layer |
| **Object Storage** | MinIO | 7.2.3 | File storage |

### AI & ML

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **LLM** | Anthropic Claude | 0.18.1 | Analysis & generation |
| **Embeddings** | OpenAI | 1.12.0 | Vector embeddings |
| **PDF Processing** | pdfplumber | 0.10.3 | Document parsing |
| **OCR** | pytesseract | 0.3.10 | Text extraction |

### Task Queue

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Task Queue** | Celery | 5.3.6 | Background jobs |
| **Message Broker** | RabbitMQ | - | Task distribution |
| **Monitoring** | Flower | 2.0.1 | Task monitoring |

---

## 4. Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/              # Migration files
│   └── env.py                 # Alembic environment
│
├── app/
│   ├── api/                   # API layer
│   │   └── v1/
│   │       ├── api.py        # Route aggregation
│   │       └── endpoints/    # Endpoint modules
│   │           ├── tenders.py
│   │           ├── tender_documents.py
│   │           ├── tender_analysis.py
│   │           ├── analysis.py
│   │           ├── proposals.py
│   │           ├── documents.py
│   │           ├── search.py
│   │           └── archive.py
│   │
│   ├── core/                  # Core configuration
│   │   ├── config.py         # Settings
│   │   ├── celery_app.py     # Celery config
│   │   └── prompts.py        # LLM prompts
│   │
│   ├── models/                # Database models
│   │   ├── base.py           # Base & session
│   │   ├── tender.py
│   │   ├── tender_document.py
│   │   ├── tender_analysis.py
│   │   ├── document.py
│   │   ├── document_section.py
│   │   ├── proposal.py
│   │   ├── past_proposal.py
│   │   ├── historical_tender.py
│   │   ├── similar_tender.py
│   │   └── criterion_suggestion.py
│   │
│   ├── schemas/               # Pydantic schemas
│   │   ├── tender.py
│   │   ├── tender_document.py
│   │   ├── tender_analysis.py
│   │   ├── analysis.py
│   │   ├── proposal.py
│   │   └── search.py
│   │
│   ├── services/              # Business logic
│   │   ├── llm_service.py    # Claude integration
│   │   ├── rag_service.py    # Vector search
│   │   ├── parser_service.py # PDF parsing
│   │   ├── storage_service.py # MinIO integration
│   │   └── archive_service.py # Archiving
│   │
│   ├── tasks/                 # Celery tasks
│   │   ├── celery_app.py
│   │   └── tender_tasks.py
│   │
│   ├── utils/                 # Utilities
│   │
│   └── main.py               # FastAPI app
│
├── scripts/                   # Utility scripts
│   └── ingest_past_proposals.py
│
├── tests/                     # Test suite
│   ├── conftest.py
│   ├── test_e2e_pipeline.py
│   ├── test_rag_e2e.py
│   └── test_rag_service.py
│
├── docker-compose.yml         # Docker services
├── Dockerfile                 # Container image
├── requirements.txt           # Dependencies
├── alembic.ini               # Alembic config
└── README.md                 # Documentation
```

---

## 5. Database Models

### Core Models

#### **Tender** (`/app/models/tender.py`)

Main tender entity representing an "appel d'offre".

```python
class Tender(Base):
    __tablename__ = "tenders"

    id: UUID                    # Primary key
    title: str                  # Tender title
    organization: str           # Issuing organization
    reference_number: str       # Reference number
    deadline: datetime          # Submission deadline
    raw_content: str           # Original content
    parsed_content: JSON       # Structured content
    status: str                # new/processing/analyzed/archived
    source: str                # Source (BOAMP, AWS Place, etc.)
    created_at: datetime
    updated_at: datetime
```

**Relationships:**
- Has many `TenderDocument`
- Has one `TenderAnalysis`
- Has many `TenderCriterion`
- Has many `Proposal`

#### **TenderDocument** (`/app/models/tender_document.py`)

Documents uploaded for tenders (CCTP, RC, AE, BPU, etc.).

```python
class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id: UUID                      # Primary key
    tender_id: UUID              # Foreign key
    filename: str                # Original filename
    file_path: str               # MinIO path
    file_size: int               # Size in bytes
    mime_type: str               # MIME type
    document_type: str           # CCTP/RC/AE/BPU/DUME/ANNEXE
    extraction_status: str       # pending/processing/completed/failed
    extracted_text: str          # Extracted text
    page_count: int
    extraction_method: str       # text/ocr
    extraction_meta_data: JSON   # Sections, tables, structured data
    extraction_error: str
    uploaded_at: datetime
    processed_at: datetime
```

**Relationships:**
- Belongs to `Tender`
- Has many `DocumentSection`

#### **DocumentSection** (`/app/models/document_section.py`)

Structured sections extracted from documents.

```python
class DocumentSection(Base):
    __tablename__ = "document_sections"

    id: UUID                    # Primary key
    document_id: UUID          # Foreign key
    section_type: str          # PART/ARTICLE/SECTION/NUMBERED_ITEM
    section_number: str        # 1.2.3
    parent_number: str         # 1.2 (for hierarchy)
    parent_id: UUID           # Parent section ID
    title: str                # Section title
    content: str              # Section content
    content_length: int
    content_truncated: bool
    page: int
    line: int
    level: int                # Hierarchy level
    is_toc: bool             # Table of contents flag
    is_key_section: bool     # Important section flag
    created_at: datetime
```

**Key Section Categories:**
- Exclusions (motifs d'exclusion)
- Obligations (obligations contractuelles)
- Criteria (critères d'évaluation)
- Deadlines (délais)
- Penalties (pénalités)
- Price conditions (conditions financières)
- Processes (processus ITIL, gouvernance)

#### **TenderAnalysis** (`/app/models/tender_analysis.py`)

AI-generated analysis results.

```python
class TenderAnalysis(Base):
    __tablename__ = "tender_analysis"

    id: UUID                       # Primary key
    tender_id: UUID               # Foreign key (unique)
    summary: str                  # Executive summary
    key_requirements: JSON        # Main requirements
    deadlines: JSON               # Important dates
    risks: JSON                   # Risk factors
    mandatory_documents: JSON     # Required docs
    complexity_level: str         # faible/moyenne/élevée
    recommendations: JSON         # Strategic recommendations
    similar_tenders: JSON         # Similar past tenders
    structured_data: JSON         # Technical/budget/contact info
    analysis_status: str          # pending/processing/completed/failed
    error_message: str
    analyzed_at: datetime
    processing_time_seconds: int
```

#### **DocumentEmbedding** (`/app/models/document.py`)

Vector embeddings for RAG (pgvector).

```python
class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id: UUID                    # Primary key
    document_id: UUID          # Source document
    document_type: str         # tender/proposal/past_proposal/certification
    chunk_text: str           # Text chunk
    embedding: Vector(1536)   # OpenAI embedding vector
    meta_data: JSON          # Chunk metadata
    created_at: datetime
```

**Vector Search:**
- Cosine similarity: `1 - (embedding <=> query_embedding)`
- Indexes: GIN index on document_id, IVFFLAT on embedding vector

### Archive Models

#### **HistoricalTender** (`/app/models/historical_tender.py`)

Archived completed tenders for knowledge base.

```python
class HistoricalTender(Base):
    __tablename__ = "historical_tenders"

    id: UUID
    title: str
    organization: str
    reference_number: str
    publication_date: date
    deadline: date
    award_date: date
    status: str                 # awarded/cancelled/withdrawn
    archived_at: datetime
    archived_by: UUID
    meta_data: JSON            # Original tender data
```

#### **PastProposal** (`/app/models/past_proposal.py`)

Archived proposals with outcomes for learning.

```python
class PastProposal(Base):
    __tablename__ = "past_proposals"

    id: UUID
    historical_tender_id: UUID
    our_company_id: UUID
    our_company_name: str
    status: str                # won/lost/shortlisted/withdrawn
    score_obtained: Decimal
    max_score: Decimal
    rank: int
    total_bidders: int
    sections: JSON             # Proposal content
    lessons_learned: str
    win_factors: JSON
    improvement_areas: JSON
    meta_data: JSON
    is_winning_proposal: bool  # Computed property
```

**RAG Integration:**
- Archived proposals are embedded into `document_embeddings`
- Document type: `"past_proposal"`
- Used for content suggestion and reuse

### Proposal Models

#### **Proposal** (`/app/models/proposal.py`)

Active proposals being drafted.

```python
class Proposal(Base):
    __tablename__ = "proposals"

    id: UUID
    tender_id: UUID
    user_id: UUID
    sections: JSON              # Proposal sections
    status: str                 # draft/review/submitted
    compliance_score: float
    version: int
    created_at: datetime
    updated_at: datetime
```

#### **TenderCriterion** (`/app/models/tender.py`)

Evaluation criteria extracted from tenders.

```python
class TenderCriterion(Base):
    __tablename__ = "tender_criteria"

    id: UUID
    tender_id: UUID
    criterion_type: str        # technique/financier/delai/rse/autre
    description: str
    weight: str                # Percentage (e.g., "60%")
    is_mandatory: str          # "true"/"false"
    meta_data: JSON           # evaluation_method, sub_criteria
```

---

## 6. API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check status |

**Response:**
```json
{
  "status": "healthy",
  "app": "ScorpiusAO",
  "version": "0.1.0",
  "environment": "development"
}
```

### Tenders API (`/api/v1/tenders`)

#### List Tenders
**GET** `/api/v1/tenders`

**Query Parameters:**
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=20): Max results
- `status` (str, optional): Filter by status

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "title": "Tender title",
    "organization": "Organization name",
    "reference_number": "AO-2024-123",
    "deadline": "2024-12-31T23:59:59Z",
    "status": "new",
    "created_at": "2024-10-01T10:00:00Z"
  }
]
```

#### Create Tender
**POST** `/api/v1/tenders`

**Request Body:**
```json
{
  "title": "Tender title",
  "organization": "Organization",
  "reference_number": "AO-2024-123",
  "deadline": "2024-12-31T23:59:59Z",
  "raw_content": "Full text...",
  "source": "BOAMP"
}
```

**Response:** `201 Created`

#### Get Tender
**GET** `/api/v1/tenders/{tender_id}`

**Response:** `200 OK` - Full tender object

#### Upload Tender Document (deprecated)
**POST** `/api/v1/tenders/upload`

⚠️ **Deprecated**: Use `/api/v1/tenders/{tender_id}/documents/upload` instead

#### Ask Question (RAG Q&A)
**POST** `/api/v1/tenders/{tender_id}/ask`

**Request Body:**
```json
{
  "question": "What are the mandatory certifications?",
  "top_k": 5
}
```

**Response:** `200 OK`
```json
{
  "question": "What are the mandatory certifications?",
  "answer": "According to section 3.2.1, the mandatory certifications are ISO 27001 and ISO 9001...",
  "sources": [
    {
      "document_id": "uuid",
      "document_type": "tender",
      "chunk_text": "Section 3.2.1: Certifications...",
      "similarity_score": 0.87,
      "metadata": {
        "section_number": "3.2.1",
        "page": 15,
        "document_filename": "CCTP.pdf"
      }
    }
  ],
  "confidence": 0.85,
  "cached": false
}
```

**Features:**
- Vector semantic search across all tender documents
- Claude AI answer generation
- Source citations with section/page references
- Redis caching (1 hour TTL)
- Confidence scoring

### Tender Documents API (`/api/v1/tenders/{tender_id}/documents`)

#### Upload Document
**POST** `/api/v1/tenders/{tender_id}/documents/upload`

**Request:** `multipart/form-data`
- `file`: PDF file
- `document_type`: CCTP|RC|AE|BPU|DUME|ANNEXE

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "tender_id": "uuid",
  "filename": "CCTP.pdf",
  "file_size": 1234567,
  "document_type": "CCTP",
  "extraction_status": "pending",
  "uploaded_at": "2024-10-01T10:00:00Z"
}
```

**Processing Flow:**
1. File uploaded to MinIO
2. Document record created in DB
3. Celery task `process_tender_document` queued
4. Async PDF extraction and section detection
5. Structured data saved to `document_sections`

#### List Documents
**GET** `/api/v1/tenders/{tender_id}/documents`

**Response:** `200 OK` - Array of TenderDocument objects

#### Get Document
**GET** `/api/v1/tenders/{tender_id}/documents/{document_id}`

**Response:** `200 OK` - TenderDocument with extracted content

#### Delete Document
**DELETE** `/api/v1/tenders/{tender_id}/documents/{document_id}`

**Response:** `204 No Content`

#### Trigger Analysis
**POST** `/api/v1/tenders/{tender_id}/analyze`

**Response:** `202 Accepted`
```json
{
  "message": "Analysis started",
  "tender_id": "uuid",
  "document_count": 3
}
```

**Processing Flow:**
1. Validates tender and documents exist
2. Updates tender status to "processing"
3. Celery task `process_tender_documents` queued
4. Async pipeline: extraction → embeddings → AI analysis → criteria extraction → similar tenders

### Tender Analysis API (`/api/v1/tenders/{tender_id}/analysis`)

#### Get Analysis
**GET** `/api/v1/tenders/{tender_id}/analysis`

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "tender_id": "uuid",
  "summary": "This tender is for datacenter infrastructure...",
  "key_requirements": [
    "ISO 27001 certification required",
    "24/7 support in French",
    "Maximum 4-hour response time"
  ],
  "deadlines": [
    {
      "type": "remise_offre",
      "date": "2024-12-31",
      "description": "Final submission deadline"
    }
  ],
  "risks": [
    "Penalty of 1000€/day for delays",
    "Exclusion if missing DUME"
  ],
  "mandatory_documents": ["DC1", "DC2", "DUME"],
  "complexity_level": "élevée",
  "recommendations": [
    "Focus on ITIL processes compliance",
    "Highlight ISO certifications early"
  ],
  "similar_tenders": [
    {
      "tender_id": "uuid",
      "similarity_score": 0.82
    }
  ],
  "analysis_status": "completed",
  "analyzed_at": "2024-10-01T10:30:00Z",
  "processing_time_seconds": 45
}
```

#### Get Analysis Status
**GET** `/api/v1/tenders/{tender_id}/analysis/status`

**Response:** `200 OK`
```json
{
  "tender_id": "uuid",
  "status": "processing",
  "current_step": "creating_embeddings",
  "progress": 50,
  "estimated_time_remaining": "5-10 minutes",
  "error_message": null
}
```

### Archive API (`/api/v1/archive`)

#### Archive Tender
**POST** `/api/v1/archive/tenders/{tender_id}/archive`

**Request Body:**
```json
{
  "proposal_id": "uuid",
  "proposal_status": "won",
  "score_obtained": 85.50,
  "rank": 1,
  "total_bidders": 5,
  "lessons_learned": "Strong technical approach, competitive pricing",
  "win_factors": ["technical_excellence", "price_competitive", "good_references"],
  "improvement_areas": ["presentation_clarity"],
  "delete_original": false,
  "create_embeddings": true
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "historical_tender_id": "uuid",
  "past_proposal_id": "uuid",
  "embeddings_created": 15,
  "original_deleted": false,
  "message": "Tender archived successfully. Created 15 embeddings."
}
```

**Archiving Workflow:**
1. Copy `Tender` → `HistoricalTender`
2. Copy `Proposal` → `PastProposal`
3. Create RAG embeddings for `PastProposal` (knowledge base)
4. Optionally delete original tender/proposal

### Search API (`/api/v1/search`)

#### Semantic Search
**POST** `/api/v1/search`

**Request Body:**
```json
{
  "query": "datacenter requirements",
  "top_k": 10,
  "document_types": ["tender", "past_proposal"]
}
```

**Response:** `200 OK`
```json
{
  "query": "datacenter requirements",
  "results": [
    {
      "document_id": "uuid",
      "document_type": "tender",
      "chunk_text": "The datacenter must have...",
      "similarity_score": 0.88,
      "metadata": {
        "section_number": "2.1",
        "page": 10
      }
    }
  ],
  "total": 10
}
```

#### Find Similar Tenders
**GET** `/api/v1/search/similar-tenders/{tender_id}?limit=5`

**Response:** `200 OK`
```json
{
  "tender_id": "uuid",
  "similar_tenders": [
    {
      "tender_id": "uuid",
      "similarity_score": 0.82,
      "title": "Similar tender title",
      "organization": "Organization"
    }
  ]
}
```

### Proposals API (`/api/v1/proposals`)

#### Create Proposal
**POST** `/api/v1/proposals`

**Request Body:**
```json
{
  "tender_id": "uuid",
  "sections": {
    "company_presentation": {
      "title": "Présentation de l'entreprise",
      "content": "..."
    }
  }
}
```

**Response:** `201 Created`

#### Generate Section
**POST** `/api/v1/proposals/{proposal_id}/sections/generate`

**Request Body:**
```json
{
  "section_type": "company_presentation",
  "requirements": {...}
}
```

**Response:** `200 OK`
```json
{
  "section_type": "company_presentation",
  "content": "AI-generated content...",
  "status": "generated"
}
```

#### Check Compliance
**POST** `/api/v1/proposals/{proposal_id}/compliance-check`

**Response:** `200 OK`
```json
{
  "compliance_score": 85.5,
  "is_compliant": true,
  "issues": [],
  "status": "completed"
}
```

### Analysis API (`/api/v1/analysis`)

#### Get Tender Analysis (legacy)
**GET** `/api/v1/analysis/tenders/{tender_id}`

⚠️ **Use** `/api/v1/tenders/{tender_id}/analysis` instead

#### Get Criteria (legacy)
**GET** `/api/v1/analysis/tenders/{tender_id}/criteria`

#### Re-analyze Tender
**POST** `/api/v1/analysis/tenders/{tender_id}/reanalyze`

**Response:** `202 Accepted`

### Documents API (`/api/v1/documents`)

#### List Documents
**GET** `/api/v1/documents`

**Response:** `200 OK` - Array of documents

#### Ingest Document
**POST** `/api/v1/documents/ingest`

**Request:** Upload file for knowledge base ingestion

---

## 7. Services Layer

### LLM Service (`/app/services/llm_service.py`)

**Purpose:** Claude AI integration for analysis and generation.

#### Key Methods

**`analyze_tender(tender_content: str) -> Dict`**
- Analyzes tender document using Claude API
- Extracts: summary, requirements, deadlines, risks, recommendations
- Returns structured JSON analysis
- Redis caching (1 hour TTL)
- Token limit: 100K chars max (truncates if needed)

**`analyze_tender_structured(sections: List[Dict]) -> Dict`**
- NEW: Hierarchical analysis using structured sections
- 70% token reduction vs full-text analysis
- Focuses on key sections (exclusions, criteria, obligations)
- Preserves context via parent section headers

**`extract_criteria(tender_content: str) -> List[Dict]`**
- Extracts evaluation criteria from tender
- Returns: criterion_type, description, weight, is_mandatory, sub_criteria
- Validates total weight = 100%
- Identifies eliminatory criteria

**`generate_response_section(section_type: str, requirements: Dict, company_context: Dict, db: Session, use_knowledge_base: bool = True) -> str`**
- Generates proposal section using AI
- Optional RAG: retrieves similar past winning proposals
- Adapts content from knowledge base to current context
- Returns professionally formatted response

**`check_compliance(proposal: str, requirements: List[Dict]) -> Dict`**
- Validates proposal against tender requirements
- Returns: compliance_score, is_compliant, missing_requirements, improvements
- Identifies critical gaps

**Sync/Async Duality:**
- Async methods for FastAPI endpoints (AsyncAnthropic client)
- Sync methods for Celery tasks (Anthropic client)
- Example: `analyze_tender()` (async) vs `analyze_tender_sync()` (sync)

**Prompts:**
- Defined in `/app/core/prompts.py`
- Templates: TENDER_ANALYSIS_PROMPT, CRITERIA_EXTRACTION_PROMPT, etc.
- JSON-structured responses for reliability

### RAG Service (`/app/services/rag_service.py`)

**Purpose:** Retrieval Augmented Generation with vector search.

#### Key Methods

**`create_embedding(text: str) -> List[float]`**
- Creates OpenAI embedding (text-embedding-3-small, 1536 dimensions)
- Retry logic (3 attempts with exponential backoff)
- Returns embedding vector for pgvector storage

**`chunk_text(text: str) -> List[str]`**
- Simple word-based chunking
- Default: 1024 words per chunk, 200 word overlap
- Returns list of text chunks

**`chunk_sections_semantic(sections: List[Dict], max_tokens: int = 1000, min_tokens: int = 100) -> List[Dict]`**
- **Semantic chunking** based on document structure
- Strategy:
  1. Filter out TOC sections
  2. Small sections (<100 tokens): Merge with next section
  3. Medium sections (100-1000 tokens): Keep as-is
  4. Large sections (>1000 tokens): Split with 200 token overlap
- Returns chunks with rich metadata (section_number, page, is_key_section, etc.)

**`ingest_document_sync(db: Session, document_id: UUID, chunks: List[Dict], document_type: str, metadata: Dict) -> int`**
- Ingests pre-chunked sections into vector DB
- Creates embeddings for each chunk
- Stores in `document_embeddings` table
- Batch processing (100 chunks at a time)
- Returns total chunks ingested

**`retrieve_relevant_content_sync(db: Session, query: str, top_k: int = 5, document_ids: List[str] = None, document_types: List[str] = None) -> List[Dict]`**
- Semantic search using cosine similarity
- Filters by document IDs and/or types
- Returns chunks with similarity scores
- Vector search SQL: `1 - (embedding <=> query_embedding::vector) as similarity`

**`find_similar_tenders_sync(db: Session, tender_id: UUID, limit: int = 5) -> List[Dict]`**
- Finds similar past tenders using vector similarity
- Uses first document embedding as representative
- Groups by tender_id and calculates average similarity
- Returns tender IDs with similarity scores

**`ingest_all_past_proposals_sync(db: Session, batch_size: int = 10, status_filter: str = "won") -> Dict`**
- Batch ingestion of past proposals into knowledge base
- Converts proposal sections to semantic chunks
- Creates embeddings with rich metadata (tender_title, organization, score, win_factors)
- Used for RAG-based proposal generation
- Returns: total_proposals, total_embeddings, errors

**Vector Search Performance:**
- IVFFLAT index on embedding column
- GIN index on document_id for filtering
- Typical search: <50ms for 10K chunks

### Parser Service (`/app/services/parser_service.py`)

**Purpose:** PDF document parsing and structured extraction.

#### Key Methods

**`extract_from_pdf_sync(file_content: bytes, use_ocr: bool = False) -> Dict`**
- Main extraction method (sync for Celery)
- Returns: text, tables, sections, metadata, structured_data
- Falls back to OCR if no text found

**`_extract_with_pdfplumber_enhanced_sync(pdf_file: BytesIO) -> Dict`**
- Enhanced pdfplumber extraction
- Extracts:
  - **Full page text** for each page
  - **Structured tables** (headers + rows)
  - **Detected sections** with numbering and hierarchy
- Section detection regex patterns:
  - PARTIE (Roman numerals)
  - Article (numbered)
  - Hierarchical sections (1.2.3)
  - Numbered items (1. Title)

**`_extract_section_content_from_pages(sections: List[Dict], pages_text: Dict[int, str]) -> List[Dict]`**
- Enriches detected sections with full content
- Extracts content between section headers
- Detects:
  - **TOC sections** (dots pattern, no content, early pages)
  - **Key sections** (exclusions, obligations, criteria, penalties, deadlines, processes)
- Returns sections with: content, content_length, is_toc, is_key_section, key_category

**`_is_key_section(section: Dict) -> Tuple[bool, str]`**
- Identifies critical sections for tender analysis
- Patterns:
  - Exclusions: `exclusion`, `motifs d'exclusion`
  - Obligations: `obligation`, `engagements`, `prescriptions`
  - Criteria: `critères de sélection/jugement/attribution`
  - Deadlines: `délai`, `durée de l'accord`, `date limite`
  - Penalties: `pénalités`, `sanctions`, `amendes`
  - Price: `prix global/unitaire`, `conditions financières`
  - Processes: `processus à mettre`, `gestion des incidents/changements`
  - Governance: `gouvernance`, `pilotage`, `comités`
- Returns: (is_key, category)

**`_build_section_hierarchy(sections: List[Dict]) -> List[Dict]`**
- Builds parent-child relationships based on section numbering
- Example: "4.1.4.2" → parent "4.1.4" → parent "4.1" → parent "4"
- Enables hierarchical context for AI analysis

**Structured Extraction:**
- Reference numbers (tender IDs, marché numbers)
- Deadlines (dates with context)
- Organizations (NER planned)
- Contact info (emails, phones)
- Section/table summaries

**Tables:**
- Extracted as structured objects (headers + rows)
- Stored with page number and table ID
- Clean empty cells and skip empty tables

### Storage Service (`/app/services/storage_service.py`)

**Purpose:** MinIO/S3 file storage management.

#### Key Methods

**`upload_file(file_content: bytes, object_name: str, content_type: str = "application/pdf") -> str`**
- Uploads file to MinIO bucket
- Returns object path
- Auto-creates bucket if needed

**`download_file(object_name: str) -> bytes`**
- Downloads file from MinIO
- Returns file content as bytes

**`delete_file(object_name: str) -> None`**
- Deletes file from MinIO

**`file_exists(object_name: str) -> bool`**
- Checks if file exists

**`get_file_url(object_name: str, expires: int = 3600) -> str`**
- Generates presigned URL (default 1 hour expiry)
- For temporary file access

**Configuration:**
- Endpoint: `localhost:9000` (configurable)
- Credentials: `minioadmin` / `minioadmin` (dev)
- Default bucket: `scorpius-documents`
- Secure: False (dev), True (prod)

**File Organization:**
```
scorpius-documents/
└── tenders/
    └── {tender_id}/
        └── documents/
            └── {file_id}_{filename}
```

### Archive Service (`/app/services/archive_service.py`)

**Purpose:** Archive completed tenders/proposals to historical tables.

#### Key Method

**`archive_tender(db: Session, tender_id: UUID, proposal_id: UUID, proposal_status: str, ...) -> Dict`**

**Workflow:**
1. **Validate:** Check tender and proposal exist and match
2. **Create HistoricalTender:**
   - Copy tender metadata
   - Store original tender data in `meta_data` JSON
   - Set archived_at timestamp
3. **Create PastProposal:**
   - Copy proposal sections
   - Store outcome data (status, score, rank, bidders)
   - Store lessons_learned and win_factors
   - Calculate `is_winning_proposal` property
4. **Create Embeddings (optional):**
   - Convert proposal sections to semantic chunks
   - Ingest into `document_embeddings` with type "past_proposal"
   - Rich metadata: tender_title, organization, status, score, win_factors
5. **Delete Originals (optional):**
   - Remove original tender and proposal if requested
6. **Return Results:**
   - historical_tender_id, past_proposal_id, embeddings_created, original_deleted

**Use Cases:**
- Won tender: `status="won"`, `rank=1`
- Lost tender: `status="lost"`, `rank=2+`
- Withdrawn: `status="withdrawn"`
- Shortlisted: `status="shortlisted"`

**Knowledge Base Integration:**
- Archived winning proposals are embedded for RAG
- Used in `generate_response_section()` for content reuse
- Filters by `status="won"` for best examples

---

## 8. Background Tasks

### Celery Configuration

**Broker:** RabbitMQ (`amqp://guest:guest@localhost:5672//`)
**Backend:** Redis (`redis://localhost:6379/1`)
**Worker:** Sync engine with psycopg2

#### Database Session Management

**`get_celery_session()` (in `/app/models/base.py`):**
- Lazy initialization to avoid fork() issues
- Separate sync engine for Celery workers
- Pool: 5 connections, max overflow 10
- Pool pre-ping: Verifies connections before use

### Key Tasks (`/app/tasks/tender_tasks.py`)

#### **`process_tender_document(document_id: str)`**

**Purpose:** Extract text and structure from a single PDF document.

**Workflow:**
1. Load `TenderDocument` from DB
2. Update status to "processing"
3. Download file from MinIO
4. Extract using `parser_service.extract_from_pdf_sync()`
   - Text extraction
   - Section detection
   - Table extraction
   - Structured metadata
5. Save extraction results to `TenderDocument`:
   - `extracted_text`
   - `extraction_meta_data` (sections, tables, structured)
   - `page_count`, `extraction_method`
6. Save sections to `DocumentSection` table:
   - PASS 1: Insert sections with `parent_number`
   - PASS 2: Resolve `parent_id` via SQL JOIN on `parent_number`
7. Update status to "completed"
8. Fallback: Try OCR if no text found

**Retry:** Max 3 retries with exponential backoff

#### **`process_tender_documents(tender_id: str)`**

**Purpose:** Complete tender analysis pipeline.

**Workflow (6 Steps):**

1. **Extract Content:**
   - Ensure all documents are extracted (call `process_tender_document` if needed)
   - Concatenate all document texts

2. **Create Embeddings:**
   - Load `DocumentSection` for each document (filter `is_toc=False`)
   - Semantic chunking via `rag_service.chunk_sections_semantic()`
   - Ingest chunks with embeddings via `rag_service.ingest_document_sync()`
   - Metadata: tender_id, filename, document_type

3. **AI Analysis:**
   - Call `llm_service.analyze_tender_sync(full_content)`
   - Extract: summary, requirements, deadlines, risks, recommendations, complexity
   - Save to `TenderAnalysis` table

4. **Extract Criteria:**
   - Call `llm_service.extract_criteria_sync(full_content)`
   - Parse criteria with weights and sub-criteria
   - Save to `TenderCriterion` table
   - Validate total weight = 100%

5. **Find Similar Tenders:**
   - Call `rag_service.find_similar_tenders_sync(tender_id)`
   - Vector search across historical tenders
   - Store top 5 results in `analysis.similar_tenders`

6. **Generate Suggestions (planned):**
   - Content suggestions from knowledge base
   - Not yet implemented

**Finalization:**
- Update `analysis.analysis_status = "completed"`
- Update `tender.status = "analyzed"`
- Record processing time
- Return summary

**Error Handling:**
- Set `analysis_status = "failed"` on error
- Store error message in `analysis.error_message`
- Retry with exponential backoff

**Monitoring:**
- Console logging for each step
- Progress tracking for UI updates (planned WebSocket)
- Performance metrics (processing_time_seconds)

### Other Tasks (Placeholders)

#### **`process_new_tender(tender_id: str)`**
- Placeholder for complete tender processing
- Future: Trigger full pipeline on tender creation

#### **`generate_proposal_section(proposal_id: str, section_type: str)`**
- Generate AI proposal section
- To be implemented

#### **`check_proposal_compliance(proposal_id: str)`**
- Compliance validation
- To be implemented

#### **`ingest_knowledge_base_document(document_id: str, document_type: str)`**
- Knowledge base ingestion
- For certifications, references, case studies

---

## 9. Configuration

### Settings (`/app/core/config.py`)

**Environment Variables (.env file):**

```python
class Settings(BaseSettings):
    # Application
    app_name: str = "ScorpiusAO"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@host:port/db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # AI APIs
    anthropic_api_key: str = "sk-ant-..."
    openai_api_key: str = "sk-..."

    # AI Configuration
    llm_model: str = "claude-sonnet-4-20241022"
    embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 4096
    temperature: float = 0.7
    chunk_size: int = 1024
    chunk_overlap: int = 200

    # Security
    secret_key: str = "your-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "scorpius-documents"
    minio_secure: bool = False

    # Logging
    log_level: str = "INFO"
    sentry_dsn: str | None = None

    # Rate Limiting
    rate_limit_per_minute: int = 60

    @property
    def database_url_sync(self) -> str:
        """Synchronous DB URL for Alembic/Celery (psycopg2)"""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
```

### Environment File Example (`.env`)

```bash
# Application
APP_NAME=ScorpiusAO
APP_VERSION=0.1.0
DEBUG=True
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# AI APIs
ANTHROPIC_API_KEY=sk-ant-api03-xxx
OPENAI_API_KEY=sk-xxx

# AI Configuration
LLM_MODEL=claude-sonnet-4-20241022
EMBEDDING_MODEL=text-embedding-3-small
MAX_TOKENS=4096
TEMPERATURE=0.7
CHUNK_SIZE=1024
CHUNK_OVERLAP=200

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=scorpius-documents
MINIO_SECURE=False

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Lifespan Events

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    yield
    # Shutdown
    print("👋 Shutting down")
```

---

## 10. Dependencies

### Core Dependencies (`requirements.txt`)

#### Web Framework
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
```

#### Database
```
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9      # Sync driver (Alembic, Celery)
asyncpg==0.29.0              # Async driver (FastAPI)
pgvector==0.2.4              # Vector extension
```

#### Cache & Queue
```
redis==5.0.1
hiredis==2.3.2
celery==5.3.6
flower==2.0.1
kombu==5.3.5
```

#### AI & ML
```
anthropic==0.18.1            # Claude API
openai==1.12.0               # Embeddings API
```

#### Document Processing
```
pypdf2==3.0.1
pdfplumber==0.10.3
python-docx==1.1.0
pillow==10.2.0
pytesseract==0.3.10
```

#### Data Validation
```
pydantic==2.6.0
pydantic-settings==2.1.0
email-validator==2.1.0
```

#### HTTP & APIs
```
httpx==0.26.0
aiohttp==3.9.3
requests==2.31.0
```

#### Security
```
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

#### Utilities
```
python-dateutil==2.8.2
pytz==2024.1
tenacity==8.2.3              # Retry logic
```

#### Monitoring
```
structlog==24.1.0
sentry-sdk==1.40.0
```

#### Storage
```
minio==7.2.3                 # S3-compatible storage
```

#### Development
```
pytest==7.4.0
pytest-asyncio==0.23.4
pytest-cov==4.1.0
black==24.1.1
ruff==0.2.1
mypy==1.8.0
python-dotenv==1.0.1
```

### Removed Dependencies

**Note:** The following were removed as unused:
- `langchain` (not used, direct API calls instead)
- `langchain-community` (not used)
- `sentence-transformers` (OpenAI embeddings used instead)

---

## Database Schema Diagram

```
┌─────────────────┐       ┌──────────────────────┐
│    Tender       │──────<│  TenderDocument      │
│                 │       │                      │
│ - id (PK)       │       │ - id (PK)           │
│ - title         │       │ - tender_id (FK)    │
│ - organization  │       │ - filename          │
│ - reference_num │       │ - file_path         │
│ - deadline      │       │ - extracted_text    │
│ - status        │       │ - extraction_status │
└─────────────────┘       │ - sections (JSON)   │
         │                └──────────────────────┘
         │                          │
         │                          │
         ├─────────<─────────┬──────┘
         │                   │
         │             ┌─────▼──────────────────┐
         │             │  DocumentSection       │
         │             │                        │
         │             │ - id (PK)             │
         │             │ - document_id (FK)    │
         │             │ - section_number      │
         │             │ - parent_number       │
         │             │ - title               │
         │             │ - content             │
         │             │ - is_key_section      │
         │             └────────────────────────┘
         │
         ├─────────<─────────┐
         │                   │
         │             ┌─────▼──────────────────┐
         │             │  TenderAnalysis        │
         │             │                        │
         │             │ - id (PK)             │
         │             │ - tender_id (FK)      │
         │             │ - summary             │
         │             │ - key_requirements    │
         │             │ - deadlines           │
         │             │ - similar_tenders     │
         │             │ - analysis_status     │
         │             └────────────────────────┘
         │
         └─────────<─────────┐
                             │
                       ┌─────▼──────────────────┐
                       │  TenderCriterion       │
                       │                        │
                       │ - id (PK)             │
                       │ - tender_id (FK)      │
                       │ - criterion_type      │
                       │ - description         │
                       │ - weight              │
                       │ - is_mandatory        │
                       └────────────────────────┘

┌──────────────────────┐       ┌────────────────────────┐
│  HistoricalTender    │──────<│  PastProposal          │
│                      │       │                        │
│ - id (PK)           │       │ - id (PK)              │
│ - title             │       │ - hist_tender_id (FK)  │
│ - organization      │       │ - status (won/lost)    │
│ - reference_number  │       │ - score_obtained       │
│ - archived_at       │       │ - rank                 │
└──────────────────────┘       │ - sections (JSON)      │
                               │ - lessons_learned      │
                               │ - win_factors          │
                               └────────────────────────┘

┌──────────────────────────────────────┐
│  DocumentEmbedding (pgvector)        │
│                                      │
│ - id (PK)                           │
│ - document_id (UUID)                │
│ - document_type (tender/proposal)   │
│ - chunk_text (text)                 │
│ - embedding (vector(1536))          │
│ - meta_data (JSON)                  │
│                                      │
│ Index: IVFFLAT on embedding          │
└──────────────────────────────────────┘
```

---

## API Architecture Flow

### Document Upload & Processing Flow

```
1. User uploads PDF
   │
   ▼
2. POST /api/v1/tenders/{id}/documents/upload
   │
   ├─► Upload file to MinIO
   ├─► Create TenderDocument record (status=pending)
   └─► Queue Celery task: process_tender_document
       │
       ▼
3. Celery Worker (process_tender_document)
   │
   ├─► Download file from MinIO
   ├─► Extract with pdfplumber (text + tables + sections)
   ├─► Save to TenderDocument (extracted_text, extraction_meta_data)
   └─► Save sections to DocumentSection table (with hierarchy)
       │
       ▼
4. Status updated to "completed"
```

### Tender Analysis Flow

```
1. User clicks "Analyze"
   │
   ▼
2. POST /api/v1/tenders/{id}/analyze
   │
   ├─► Validate tender & documents exist
   ├─► Update tender.status = "processing"
   └─► Queue Celery task: process_tender_documents
       │
       ▼
3. Celery Worker (process_tender_documents)
   │
   ├─► STEP 1: Extract all documents (if needed)
   │   └─► Call process_tender_document for each
   │
   ├─► STEP 2: Create embeddings
   │   ├─► Load DocumentSection (filter is_toc=False)
   │   ├─► Semantic chunking (merge/split sections)
   │   └─► Ingest chunks with OpenAI embeddings
   │
   ├─► STEP 3: AI Analysis
   │   ├─► Call Claude API (analyze_tender_sync)
   │   └─► Save TenderAnalysis (summary, requirements, risks)
   │
   ├─► STEP 4: Extract Criteria
   │   ├─► Call Claude API (extract_criteria_sync)
   │   └─► Save TenderCriterion records
   │
   ├─► STEP 5: Find Similar Tenders
   │   ├─► Vector search (cosine similarity)
   │   └─► Save in analysis.similar_tenders
   │
   └─► STEP 6: Generate Suggestions (planned)
       │
       ▼
4. Update analysis_status = "completed"
5. Update tender.status = "analyzed"
6. Return processing summary
```

### RAG Q&A Flow

```
1. User asks question about tender
   │
   ▼
2. POST /api/v1/tenders/{id}/ask
   │
   ├─► Check Redis cache (question hash)
   │   └─► Return cached if exists
   │
   ├─► Get tender documents IDs
   │
   ├─► Create query embedding (OpenAI)
   │
   ├─► Vector search (pgvector)
   │   ├─► Filter by document_ids
   │   ├─► Cosine similarity: 1 - (embedding <=> query)
   │   └─► Return top_k chunks with metadata
   │
   ├─► Build context from chunks
   │   └─► Format: [filename - Section X, Page Y] content
   │
   ├─► Generate answer (Claude API)
   │   ├─► Prompt: TENDER_QA_PROMPT
   │   └─► Temperature: 0.3 (factual)
   │
   ├─► Calculate confidence (avg top-3 similarity)
   │
   └─► Cache response (1 hour TTL)
       │
       ▼
3. Return: question, answer, sources, confidence
```

### Archive & Knowledge Base Flow

```
1. User archives completed tender
   │
   ▼
2. POST /api/v1/archive/tenders/{id}/archive
   │
   ├─► Validate tender & proposal
   │
   ├─► Create HistoricalTender (copy tender data)
   │
   ├─► Create PastProposal
   │   ├─► Copy proposal sections
   │   └─► Store outcome (status, score, rank, lessons_learned)
   │
   ├─► Create RAG embeddings (if enabled)
   │   ├─► Convert proposal sections to chunks
   │   ├─► Create embeddings with metadata
   │   │   └─► (tender_title, organization, status, score, win_factors)
   │   └─► Ingest into document_embeddings
   │
   └─► Optionally delete original tender/proposal
       │
       ▼
3. Return: historical_tender_id, past_proposal_id, embeddings_created
```

---

## Testing

### Test Files

- `/tests/conftest.py` - Pytest fixtures
- `/tests/test_e2e_pipeline.py` - End-to-end pipeline tests
- `/tests/test_rag_e2e.py` - RAG system tests
- `/tests/test_rag_service.py` - RAG service unit tests

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_rag_service.py -v

# Run specific test
pytest tests/test_rag_service.py::test_semantic_search -v
```

---

## Docker Services

### Docker Compose (`docker-compose.yml`)

Services defined:
- **postgres**: PostgreSQL 15 with pgvector
- **redis**: Redis 7 (cache & Celery backend)
- **rabbitmq**: RabbitMQ (Celery broker)
- **minio**: MinIO (object storage)
- **celery_worker**: Celery worker
- **flower**: Celery monitoring UI

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres redis minio

# View logs
docker-compose logs -f celery_worker

# Stop all
docker-compose down
```

---

## Development Workflow

### Local Development

1. **Setup Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Start Infrastructure:**
   ```bash
   docker-compose up -d postgres redis rabbitmq minio
   ```

4. **Run Migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start API Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. **Start Celery Worker:**
   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

7. **Access API Docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Performance & Optimization

### Caching Strategy

- **Redis TTL:**
  - Tender analysis: 1 hour
  - Q&A responses: 1 hour
  - Criteria extraction: 1 hour

### Vector Search Optimization

- **Indexes:**
  - IVFFLAT on embedding column (100 lists)
  - GIN index on document_id for filtering
- **Query Performance:**
  - Typical search: <50ms for 10K chunks
  - Batch embedding creation: ~100 chunks/min

### Token Optimization

- **Structured Analysis:**
  - 70% token reduction via hierarchical sections
  - Focus on key sections (exclusions, criteria, obligations)
  - Parent headers for context

- **Semantic Chunking:**
  - Section-aware chunking (not arbitrary splits)
  - Merge small sections (<100 tokens)
  - Split large sections (>1000 tokens) with overlap

### Async/Sync Patterns

- **FastAPI Endpoints:** Async (AsyncAnthropic, AsyncOpenAI, AsyncSession)
- **Celery Tasks:** Sync (Anthropic, OpenAI, Session with psycopg2)
- **Database:**
  - Async pool: 20 connections, 10 overflow
  - Sync pool (Celery): 5 connections, 10 overflow

---

## Security Considerations

### Authentication & Authorization

⚠️ **Not yet implemented**

Planned:
- JWT token authentication
- Role-based access control (RBAC)
- User management

### API Security

- **CORS:** Configured origins in settings
- **Rate Limiting:** 60 requests/minute (planned)
- **Input Validation:** Pydantic schemas
- **File Upload:** PDF only, size limits

### Secrets Management

- **Environment Variables:** All secrets in `.env`
- **Never commit:** `.env` in `.gitignore`
- **Production:** Use secret management service (AWS Secrets Manager, Vault)

### Data Privacy

- **Document Storage:** MinIO with access controls
- **Database:** PostgreSQL with SSL (production)
- **Embeddings:** Anonymized metadata (no PII)

---

## Monitoring & Logging

### Logging

- **Framework:** structlog
- **Levels:** INFO (default), DEBUG (development)
- **Sentry:** Error tracking (optional, configure `SENTRY_DSN`)

### Celery Monitoring

- **Flower:** http://localhost:5555
  - Task monitoring
  - Worker status
  - Task history
  - Rate graphs

### Health Checks

- **API:** GET `/health`
- **Database:** Connection pool monitoring
- **Redis:** Connection status
- **MinIO:** Bucket existence check

---

## Future Enhancements

### Planned Features

1. **WebSocket Support:**
   - Real-time progress updates for analysis
   - Live Q&A streaming

2. **Multi-tenancy:**
   - User authentication
   - Organization-based isolation
   - Role-based permissions

3. **Advanced RAG:**
   - Hybrid search (keyword + vector)
   - Reranking with cross-encoder
   - Multi-query expansion

4. **AI Features:**
   - Automated proposal generation
   - Compliance validation
   - Risk assessment scoring

5. **Integration:**
   - BOAMP API integration
   - AWS Place integration
   - Email notifications

---

## Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string in .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/db
```

#### Celery Tasks Not Running
```bash
# Check RabbitMQ is running
docker-compose ps rabbitmq

# Check Celery worker logs
docker-compose logs -f celery_worker

# Restart worker
docker-compose restart celery_worker
```

#### MinIO Upload Fails
```bash
# Check MinIO is running
docker-compose ps minio

# Access MinIO console: http://localhost:9001
# Credentials: minioadmin / minioadmin

# Check bucket exists
docker-compose exec minio mc ls local/scorpius-documents
```

#### Embeddings Fail
```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Test embeddings manually
python -c "
from app.services.rag_service import rag_service
emb = rag_service.create_embedding_sync('test')
print(len(emb))  # Should be 1536
"
```

---

## API Reference Summary

### Core Resources

| Resource | Base Path | Description |
|----------|-----------|-------------|
| **Tenders** | `/api/v1/tenders` | Tender management |
| **Documents** | `/api/v1/tenders/{id}/documents` | Document upload & processing |
| **Analysis** | `/api/v1/tenders/{id}/analysis` | AI analysis results |
| **Q&A** | `/api/v1/tenders/{id}/ask` | RAG question answering |
| **Search** | `/api/v1/search` | Semantic search |
| **Archive** | `/api/v1/archive/tenders/{id}/archive` | Archiving |
| **Proposals** | `/api/v1/proposals` | Proposal management |

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async task queued) |
| 204 | No Content (success, no body) |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Contact & Support

For questions or issues:
- **Repository:** [GitHub Project URL]
- **Documentation:** `/docs` directory
- **API Docs:** http://localhost:8000/docs (when running)

---

**Last Updated:** 2025-10-06
**Documentation Version:** 1.0
**Backend Version:** 0.1.0
