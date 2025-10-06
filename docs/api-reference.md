# ScorpiusAO API Reference

**Version:** 0.1.0
**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`

## Table of Contents

1. [Authentication](#authentication)
2. [Health & Status](#health--status)
3. [Tenders](#tenders)
4. [Tender Documents](#tender-documents)
5. [Tender Analysis](#tender-analysis)
6. [Analysis (AI)](#analysis-ai)
7. [Proposals](#proposals)
8. [Search & RAG](#search--rag)
9. [Archive](#archive)
10. [Documents (Knowledge Base)](#documents-knowledge-base)
11. [Error Handling](#error-handling)

---

## Authentication

**Current Status:** No authentication implemented
**Planned:** JWT-based authentication with role-based access control

All endpoints are currently accessible without authentication. Production deployment will require:
- Bearer token authentication
- Role-based permissions (Admin, User, Viewer)
- API key support for integrations

---

## Health & Status

### Check API Health

**Endpoint:** `GET /health`

Returns the health status of the API service.

**Response:**
```json
{
  "status": "healthy",
  "app": "ScorpiusAO",
  "version": "0.1.0",
  "environment": "development"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

## Tenders

### Create Tender

**Endpoint:** `POST /api/v1/tenders/`

Create a new tender record in the database.

**Request Body:**
```json
{
  "title": "Construction nouvelle école primaire",
  "organization": "Mairie de Paris",
  "reference_number": "2024-CITY-001",
  "deadline": "2024-12-31T23:59:59Z",
  "source": "BOAMP",
  "raw_content": "Full tender text..."
}
```

**Response:** `201 Created`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Construction nouvelle école primaire",
  "organization": "Mairie de Paris",
  "reference_number": "2024-CITY-001",
  "deadline": "2024-12-31T23:59:59Z",
  "source": "BOAMP",
  "status": "new",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Required Fields:**
- `title` (max 500 chars)

**Optional Fields:**
- `organization` (max 200 chars)
- `reference_number` (max 100 chars)
- `deadline` (ISO 8601 datetime)
- `source` (string)
- `raw_content` (string)

---

### Upload Tender Document

**Endpoint:** `POST /api/v1/tenders/upload`

Upload a PDF tender document and create tender from it.

**Request:** `multipart/form-data`
- `file` (required): PDF file

**Response:** `201 Created`
```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "title": "tender.pdf",
  "status": "processing",
  "message": "Document uploaded successfully"
}
```

**Status Codes:**
- `201 Created` - Document uploaded successfully
- `400 Bad Request` - Invalid file type (only PDF supported)

**Notes:**
- Currently returns placeholder response
- Implementation pending for MinIO storage and text extraction

---

### List Tenders

**Endpoint:** `GET /api/v1/tenders/`

List all tenders with pagination and filtering.

**Query Parameters:**
- `skip` (int, default: 0) - Number of records to skip
- `limit` (int, default: 20) - Maximum number of records to return
- `status` (string, optional) - Filter by status (new, processing, completed, failed)

**Example Request:**
```bash
GET /api/v1/tenders/?skip=0&limit=10&status=new
```

**Response:** `200 OK`
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Construction nouvelle école primaire",
    "organization": "Mairie de Paris",
    "deadline": "2024-12-31T23:59:59Z",
    "status": "new",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### Get Tender by ID

**Endpoint:** `GET /api/v1/tenders/{tender_id}`

Retrieve a specific tender by its UUID.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `200 OK`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Construction nouvelle école primaire",
  "organization": "Mairie de Paris",
  "reference_number": "2024-CITY-001",
  "deadline": "2024-12-31T23:59:59Z",
  "source": "BOAMP",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T14:22:00Z"
}
```

**Status Codes:**
- `200 OK` - Tender found
- `404 Not Found` - Tender does not exist

---

### Delete Tender

**Endpoint:** `DELETE /api/v1/tenders/{tender_id}`

Delete a tender and all associated data.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `204 No Content`

**Status Codes:**
- `204 No Content` - Successfully deleted
- `404 Not Found` - Tender does not exist

**Notes:**
- Currently not implemented
- Will delete all related documents, analysis, and proposals

---

### Ask Question About Tender (RAG)

**Endpoint:** `POST /api/v1/tenders/{tender_id}/ask`

Ask a question about a specific tender using RAG (Retrieval-Augmented Generation).

**Path Parameters:**
- `tender_id` (UUID, required)

**Request Body:**
```json
{
  "question": "Quel est le délai de réalisation pour ce projet ?",
  "top_k": 5
}
```

**Parameters:**
- `question` (string, 5-500 chars, required) - Question in natural language
- `top_k` (int, 1-20, default: 5) - Number of relevant chunks to retrieve

**Response:** `200 OK`
```json
{
  "question": "Quel est le délai de réalisation pour ce projet ?",
  "answer": "Le délai de réalisation est de 18 mois à compter de la notification du marché, avec une livraison prévue au 30 juin 2025.",
  "sources": [
    {
      "document_id": "doc-uuid-1",
      "document_type": "CCTP",
      "chunk_text": "Article 3 - Délais d'exécution: Les travaux devront être achevés dans un délai de 18 mois...",
      "similarity_score": 0.92,
      "metadata": {
        "section_number": "3",
        "page": "12",
        "document_filename": "CCTP_Ecole_Paris.pdf",
        "document_type_full": "CCTP"
      }
    }
  ],
  "confidence": 0.89,
  "cached": false
}
```

**Features:**
- **Semantic Search**: Uses pgvector for similarity search
- **Context-Aware**: Retrieves relevant document sections
- **Source Citations**: Returns source documents with page/section references
- **Caching**: Redis cache (1 hour TTL) for frequently asked questions
- **Confidence Score**: Average similarity of top-3 chunks

**Status Codes:**
- `200 OK` - Answer generated successfully
- `404 Not Found` - Tender or documents not found

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/tenders/{tender_id}/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quelles sont les pièces obligatoires à fournir ?",
    "top_k": 5
  }'
```

---

## Tender Documents

### Upload Document

**Endpoint:** `POST /api/v1/tenders/{tender_id}/documents/upload`

Upload a document (PDF) for a specific tender.

**Path Parameters:**
- `tender_id` (UUID, required)

**Request:** `multipart/form-data`
- `file` (required): PDF file
- `document_type` (required): Document type

**Document Types:**
- `CCTP` - Cahier des Clauses Techniques Particulières
- `RC` - Règlement de Consultation
- `AE` - Acte d'Engagement
- `BPU` - Bordereau de Prix Unitaires
- `DUME` - Document Unique de Marché Européen
- `ANNEXE` - Annexe

**Response:** `201 Created`
```json
{
  "id": "doc-uuid-123",
  "tender_id": "tender-uuid-456",
  "filename": "CCTP_Projet.pdf",
  "file_path": "tenders/tender-uuid-456/documents/doc-uuid-123_CCTP_Projet.pdf",
  "file_size": 2048576,
  "mime_type": "application/pdf",
  "document_type": "CCTP",
  "extraction_status": "pending",
  "page_count": null,
  "uploaded_at": "2024-01-15T10:30:00Z",
  "processed_at": null
}
```

**Workflow:**
1. Validates tender exists
2. Validates file type (PDF only)
3. Validates document type
4. Uploads to MinIO storage
5. Creates database record
6. Triggers async processing (Celery task)

**Status Codes:**
- `201 Created` - Document uploaded successfully
- `400 Bad Request` - Invalid file type or document type
- `404 Not Found` - Tender not found
- `500 Internal Server Error` - Storage failure

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/tenders/{tender_id}/documents/upload \
  -F "file=@/path/to/CCTP.pdf" \
  -F "document_type=CCTP"
```

---

### List Documents

**Endpoint:** `GET /api/v1/tenders/{tender_id}/documents`

List all documents for a specific tender.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `200 OK`
```json
[
  {
    "id": "doc-uuid-1",
    "tender_id": "tender-uuid-456",
    "filename": "CCTP.pdf",
    "file_path": "tenders/.../CCTP.pdf",
    "file_size": 2048576,
    "mime_type": "application/pdf",
    "document_type": "CCTP",
    "extraction_status": "completed",
    "page_count": 45,
    "uploaded_at": "2024-01-15T10:30:00Z",
    "processed_at": "2024-01-15T10:35:00Z"
  }
]
```

**Extraction Status Values:**
- `pending` - Awaiting processing
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed

---

### Get Document Details

**Endpoint:** `GET /api/v1/tenders/{tender_id}/documents/{document_id}`

Get specific document with extracted content.

**Path Parameters:**
- `tender_id` (UUID, required)
- `document_id` (UUID, required)

**Response:** `200 OK`
```json
{
  "id": "doc-uuid-1",
  "tender_id": "tender-uuid-456",
  "filename": "CCTP.pdf",
  "document_type": "CCTP",
  "extraction_status": "completed",
  "extracted_text": "Full extracted text content...",
  "structured_sections": [
    {
      "section_number": "1",
      "title": "Objet du marché",
      "content": "...",
      "page_start": 1,
      "page_end": 3
    }
  ],
  "uploaded_at": "2024-01-15T10:30:00Z",
  "processed_at": "2024-01-15T10:35:00Z"
}
```

**Status Codes:**
- `200 OK` - Document found
- `404 Not Found` - Document or tender not found

---

### Delete Document

**Endpoint:** `DELETE /api/v1/tenders/{tender_id}/documents/{document_id}`

Delete a specific document.

**Path Parameters:**
- `tender_id` (UUID, required)
- `document_id` (UUID, required)

**Response:** `204 No Content`

**Status Codes:**
- `204 No Content` - Successfully deleted
- `404 Not Found` - Document or tender not found

**Notes:**
- MinIO file deletion currently pending implementation

---

### Analyze Tender Documents

**Endpoint:** `POST /api/v1/tenders/{tender_id}/analyze`

Trigger AI analysis of all tender documents.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `202 Accepted`
```json
{
  "message": "Analysis started",
  "tender_id": "tender-uuid-456",
  "document_count": 5
}
```

**Workflow:**
1. Verifies tender exists
2. Checks documents are uploaded
3. Updates tender status to "processing"
4. Triggers async Celery task
5. Returns immediately (async processing)

**Status Codes:**
- `202 Accepted` - Analysis queued successfully
- `400 Bad Request` - No documents found
- `404 Not Found` - Tender not found

---

## Tender Analysis

### Get Analysis Results

**Endpoint:** `GET /api/v1/tenders/{tender_id}/analysis`

Retrieve AI analysis results for a tender.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `200 OK`
```json
{
  "id": "analysis-uuid-1",
  "tender_id": "tender-uuid-456",
  "summary": "Marché de travaux pour la construction d'une école primaire...",
  "key_requirements": [
    "Certification ISO 9001",
    "3 références similaires",
    "Capacité financière > 500k€"
  ],
  "deadlines": [
    {
      "type": "submission",
      "date": "2024-03-15T17:00:00Z",
      "description": "Dépôt des offres"
    }
  ],
  "risks": [
    "Délai de réalisation court",
    "Pénalités de retard élevées"
  ],
  "mandatory_documents": [
    "DC1 - Lettre de candidature",
    "DC2 - Déclaration du candidat",
    "Attestation fiscale"
  ],
  "complexity_level": "high",
  "recommendations": [
    "Former un groupement pour répartir les risques",
    "Prévoir 20% de marge sur les délais"
  ],
  "structured_data": {
    "budget_range": "500000-1000000",
    "duration_months": 18
  },
  "analysis_status": "completed",
  "processing_time_seconds": 45,
  "analyzed_at": "2024-01-15T11:00:00Z"
}
```

**Status Codes:**
- `200 OK` - Analysis found
- `404 Not Found` - Analysis not found (tender may not be analyzed yet)

---

### Get Analysis Status

**Endpoint:** `GET /api/v1/tenders/{tender_id}/analysis/status`

Get current status of tender analysis processing.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `200 OK`
```json
{
  "tender_id": "tender-uuid-456",
  "status": "processing",
  "current_step": "processing",
  "progress": 50,
  "steps_completed": [],
  "estimated_time_remaining": "5-10 minutes",
  "error_message": null
}
```

**Status Values:**
- `pending` - Analysis not started
- `processing` - Currently analyzing
- `completed` - Analysis complete
- `failed` - Analysis failed

**Progress Mapping:**
- `pending`: 0%
- `processing`: 50%
- `completed`: 100%
- `failed`: 0%

**Status Codes:**
- `200 OK` - Status retrieved
- `404 Not Found` - Tender not found

---

## Analysis (AI)

### Get Tender Analysis (Legacy)

**Endpoint:** `GET /api/v1/analysis/tenders/{tender_id}`

**Status:** `404 Not Found` - Not implemented (legacy endpoint)

---

### Get Tender Criteria

**Endpoint:** `GET /api/v1/analysis/tenders/{tender_id}/criteria`

**Status:** `404 Not Found` - Not implemented

**Planned Features:**
- Extract evaluation criteria
- Parse weighting and scoring rules
- Identify mandatory vs. optional criteria

---

### Reanalyze Tender

**Endpoint:** `POST /api/v1/analysis/tenders/{tender_id}/reanalyze`

Trigger re-analysis of a tender.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `202 Accepted`
```json
{
  "message": "Re-analysis queued",
  "tender_id": "tender-uuid-456"
}
```

**Status Codes:**
- `202 Accepted` - Re-analysis queued

**Notes:**
- Task queuing not yet implemented

---

## Proposals

### Create Proposal

**Endpoint:** `POST /api/v1/proposals/`

Create a new proposal (tender response) for a tender.

**Request Body:**
```json
{
  "tender_id": "tender-uuid-456",
  "user_id": "user-uuid-789",
  "sections": {
    "technical": {},
    "financial": {},
    "administrative": {}
  }
}
```

**Response:** `201 Created` or `501 Not Implemented`

**Status Codes:**
- `501 Not Implemented` - Feature pending

---

### List Proposals for Tender

**Endpoint:** `GET /api/v1/proposals/tender/{tender_id}`

List all proposals for a specific tender.

**Path Parameters:**
- `tender_id` (UUID, required)

**Response:** `200 OK`
```json
[]
```

**Notes:**
- Currently returns empty array
- Implementation pending

---

### Get Proposal

**Endpoint:** `GET /api/v1/proposals/{proposal_id}`

Get a specific proposal by ID.

**Path Parameters:**
- `proposal_id` (UUID, required)

**Response:** `404 Not Found`

**Notes:**
- Implementation pending

---

### Generate Proposal Section

**Endpoint:** `POST /api/v1/proposals/{proposal_id}/sections/generate`

Generate a proposal section using AI.

**Path Parameters:**
- `proposal_id` (UUID, required)

**Request Body:**
```json
{
  "section_type": "technical",
  "context": {
    "company_info": "...",
    "past_projects": "..."
  },
  "max_tokens": 2000
}
```

**Response:** `200 OK`
```json
{
  "section_type": "technical",
  "content": "AI-generated content placeholder",
  "status": "generated"
}
```

**Notes:**
- Currently returns placeholder
- LLM integration pending

---

### Update Section

**Endpoint:** `PUT /api/v1/proposals/{proposal_id}/sections/{section_id}`

Update a specific section of a proposal.

**Path Parameters:**
- `proposal_id` (UUID, required)
- `section_id` (string, required)

**Request Body:**
```json
{
  "content": "Updated section content...",
  "version": 2
}
```

**Response:** `200 OK`
```json
{
  "message": "Section updated"
}
```

**Notes:**
- Implementation pending

---

### Compliance Check

**Endpoint:** `POST /api/v1/proposals/{proposal_id}/compliance-check`

Run AI compliance check on proposal.

**Path Parameters:**
- `proposal_id` (UUID, required)

**Response:** `200 OK`
```json
{
  "compliance_score": 0.0,
  "issues": [],
  "status": "pending"
}
```

**Planned Features:**
- Check mandatory document presence
- Validate against tender requirements
- Identify missing information
- Score compliance 0-100%

---

## Search & RAG

### Semantic Search

**Endpoint:** `POST /api/v1/search/`

Perform semantic search across knowledge base.

**Request Body:**
```json
{
  "query": "construction école norme",
  "limit": 10,
  "document_types": ["CCTP", "RC"],
  "filters": {
    "min_date": "2023-01-01"
  }
}
```

**Response:** `200 OK`
```json
{
  "query": "construction école norme",
  "results": [],
  "total": 0
}
```

**Notes:**
- pgvector implementation pending
- Will search across all indexed documents

---

### Find Similar Tenders

**Endpoint:** `GET /api/v1/search/similar-tenders/{tender_id}`

Find similar past tenders using vector similarity.

**Path Parameters:**
- `tender_id` (string, required)

**Query Parameters:**
- `limit` (int, 1-20, default: 5)

**Response:** `200 OK`
```json
{
  "tender_id": "tender-uuid-456",
  "similar_tenders": []
}
```

**Planned Features:**
- Vector similarity search
- Match by domain/sector
- Historical performance data

---

## Archive

### Archive Tender

**Endpoint:** `POST /api/v1/archive/tenders/{tender_id}/archive`

Archive a completed tender to historical tables for knowledge base.

**Path Parameters:**
- `tender_id` (UUID, required)

**Request Body:**
```json
{
  "proposal_id": "proposal-uuid-123",
  "proposal_status": "won",
  "score_obtained": 85.50,
  "rank": 1,
  "total_bidders": 5,
  "lessons_learned": "Strong technical memo, competitive pricing",
  "win_factors": [
    "price_competitive",
    "strong_references",
    "good_presentation"
  ],
  "improvement_areas": [
    "delivery_planning"
  ],
  "delete_original": false,
  "create_embeddings": true
}
```

**Parameters:**
- `proposal_id` (UUID, required) - Proposal to archive
- `proposal_status` (string, default: "won") - Status: won, lost, shortlisted, withdrawn
- `score_obtained` (decimal, optional) - Final score (e.g., 85.50)
- `rank` (int, optional) - Rank among bidders (1 = winner)
- `total_bidders` (int, optional) - Total number of bidders
- `lessons_learned` (string, optional) - Post-mortem analysis
- `win_factors` (array, optional) - Key success factors
- `improvement_areas` (array, optional) - Areas for improvement
- `delete_original` (bool, default: false) - Delete source after archiving
- `create_embeddings` (bool, default: true) - Create RAG embeddings

**Response:** `201 Created`
```json
{
  "success": true,
  "historical_tender_id": "hist-tender-uuid",
  "past_proposal_id": "past-prop-uuid",
  "embeddings_created": 42,
  "original_deleted": false,
  "message": "Tender archived successfully. Created 42 embeddings."
}
```

**Workflow:**
1. Copy Tender → HistoricalTender
2. Copy Proposal → PastProposal
3. Create RAG embeddings (optional)
4. Delete original records (optional)

**Use Cases:**
- **Won tender**: `proposal_status="won"`, `rank=1`
- **Lost tender**: `proposal_status="lost"`, `rank=2+`
- **Withdrawn**: `proposal_status="withdrawn"`

**Status Codes:**
- `201 Created` - Successfully archived
- `404 Not Found` - Tender or proposal not found
- `500 Internal Server Error` - Archive operation failed

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/archive/tenders/{tender_id}/archive \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "proposal-uuid-123",
    "proposal_status": "won",
    "score_obtained": 85.50,
    "rank": 1,
    "total_bidders": 5,
    "create_embeddings": true
  }'
```

---

## Documents (Knowledge Base)

### List Documents

**Endpoint:** `GET /api/v1/documents/`

List all documents in the knowledge base.

**Response:** `200 OK`
```json
[]
```

**Notes:**
- Implementation pending
- Will list all ingested documents

---

### Ingest Document

**Endpoint:** `POST /api/v1/documents/ingest`

Ingest a document into the RAG knowledge base.

**Response:** `200 OK`
```json
{
  "message": "Document ingestion not yet implemented"
}
```

**Planned Features:**
- Upload documents for RAG
- Extract and chunk text
- Generate embeddings
- Store in pgvector

---

## Error Handling

### Standard Error Response

All endpoints return errors in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200` | OK | Successful GET request |
| `201` | Created | Successful POST creating a resource |
| `202` | Accepted | Request accepted for async processing |
| `204` | No Content | Successful DELETE request |
| `400` | Bad Request | Invalid request parameters or body |
| `404` | Not Found | Resource does not exist |
| `422` | Validation Error | Request validation failed (Pydantic) |
| `500` | Internal Server Error | Server-side error |
| `501` | Not Implemented | Feature not yet implemented |

### Validation Errors (422)

Pydantic validation errors return detailed information:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "question"],
      "msg": "String should have at least 5 characters",
      "input": "Qui",
      "ctx": {"min_length": 5}
    }
  ]
}
```

---

## Rate Limiting

**Current Status:** Not implemented
**Configuration:** `rate_limit_per_minute: 60` (in settings)

**Planned Implementation:**
- 60 requests per minute per IP
- Higher limits for authenticated users
- Sliding window algorithm
- Rate limit headers in response

---

## API Versioning

**Current Version:** v1
**Strategy:** URL path versioning (`/api/v1/...`)

**Version Information:**
- All v1 endpoints are under `/api/v1` prefix
- Future versions will use `/api/v2`, etc.
- Deprecated endpoints will be marked in documentation
- 6-month deprecation notice before removal

---

## CORS Configuration

**Allowed Origins:**
- `http://localhost:3000` (Frontend dev)
- `http://localhost:8000` (API dev)

**Allowed Methods:** All (`*`)
**Allowed Headers:** All (`*`)
**Credentials:** Enabled

---

## Pagination

**Default Pattern:**
- `skip` (int, default: 0) - Offset for pagination
- `limit` (int, default: 20) - Maximum items per page

**Example:**
```
GET /api/v1/tenders/?skip=20&limit=10
```

Returns items 21-30.

**Future Enhancement:**
- Cursor-based pagination for large datasets
- Total count in response headers
- Link headers for next/prev pages

---

## Filtering

**Current Implementation:**
- Status filtering on tenders: `?status=new`
- Document type filtering (planned)

**Planned Features:**
- Date range filtering
- Full-text search
- Complex filter combinations
- Saved filter presets

---

## Content Types

**Supported:**
- `application/json` (default for all endpoints)
- `multipart/form-data` (file uploads)

**Response Format:** Always JSON

---

## Async Processing

### Celery Tasks

Background tasks are processed asynchronously using Celery:

**Document Processing:**
- `process_tender_document(document_id)` - Extract text, create embeddings
- `process_tender_documents(tender_id)` - Analyze all tender documents

**Task Status Tracking:**
- Tasks return immediately with 202 status
- Use status endpoints to check progress
- Results stored in Redis

**Configuration:**
- Broker: RabbitMQ (`amqp://guest:guest@localhost:5672//`)
- Backend: Redis (`redis://localhost:6379/1`)

---

## Caching

### Redis Cache

**Q&A Endpoint Caching:**
- Cache key: `tender_qa:{tender_id}:{question_hash}`
- TTL: 1 hour (3600 seconds)
- Response includes `cached: true/false` flag

**Cache Invalidation:**
- Manual: When tender documents are updated
- Automatic: TTL expiration

---

## External Dependencies

### Required Services

1. **PostgreSQL with pgvector**
   - Port: 5433
   - Database: scorpius_db
   - Vector similarity search

2. **Redis**
   - Port: 6379
   - Caching and Celery results

3. **RabbitMQ**
   - Port: 5672
   - Celery message broker

4. **MinIO (S3-compatible storage)**
   - Endpoint: localhost:9000
   - Bucket: scorpius-documents
   - Document storage

### AI APIs

1. **Anthropic Claude**
   - Model: `claude-sonnet-4-20241022`
   - Used for: Q&A, analysis, content generation

2. **OpenAI (Optional)**
   - Model: `text-embedding-3-small`
   - Used for: Text embeddings

---

## Security Considerations

### Current State
- No authentication implemented
- CORS configured for local development
- No rate limiting
- Secrets in .env file

### Production Requirements
- [ ] JWT authentication
- [ ] API key management
- [ ] Role-based access control
- [ ] Rate limiting per user/IP
- [ ] Input sanitization
- [ ] SQL injection prevention (using SQLAlchemy ORM)
- [ ] File upload validation
- [ ] Secure secret management (Vault/AWS Secrets)

---

## SDK & Client Libraries

**Status:** Not available

**Planned:**
- Python SDK
- JavaScript/TypeScript SDK
- OpenAPI-generated clients

---

## Changelog

### v0.1.0 (Current)
- Initial API implementation
- Tender CRUD operations
- Document upload and management
- RAG-based Q&A endpoint
- Tender analysis workflows
- Archive functionality

### Upcoming
- Authentication system
- Full proposal management
- Advanced search capabilities
- Rate limiting
- Webhook support

---

## Support & Documentation

**API Documentation:**
- Interactive docs: `http://localhost:8000/docs` (Swagger UI)
- OpenAPI spec: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

**Repository:** GitHub (add link)
**Issues:** GitHub Issues (add link)
**Contact:** (add contact info)

---

## Example Workflows

### Complete Tender Processing

```bash
# 1. Create tender
curl -X POST http://localhost:8000/api/v1/tenders/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Construction école primaire",
    "organization": "Mairie de Paris",
    "deadline": "2024-12-31T23:59:59Z"
  }'

# Response: {"id": "tender-123", ...}

# 2. Upload documents
curl -X POST http://localhost:8000/api/v1/tenders/tender-123/documents/upload \
  -F "file=@CCTP.pdf" \
  -F "document_type=CCTP"

curl -X POST http://localhost:8000/api/v1/tenders/tender-123/documents/upload \
  -F "file=@RC.pdf" \
  -F "document_type=RC"

# 3. Trigger analysis
curl -X POST http://localhost:8000/api/v1/tenders/tender-123/analyze

# 4. Check analysis status
curl http://localhost:8000/api/v1/tenders/tender-123/analysis/status

# 5. Get analysis results
curl http://localhost:8000/api/v1/tenders/tender-123/analysis

# 6. Ask questions
curl -X POST http://localhost:8000/api/v1/tenders/tender-123/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quels sont les délais ?",
    "top_k": 5
  }'
```

### Archive Won Tender

```bash
# Archive tender after winning bid
curl -X POST http://localhost:8000/api/v1/archive/tenders/tender-123/archive \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "proposal-456",
    "proposal_status": "won",
    "score_obtained": 88.5,
    "rank": 1,
    "total_bidders": 4,
    "lessons_learned": "Strong technical approach won the day",
    "win_factors": ["technical_excellence", "competitive_price"],
    "create_embeddings": true
  }'
```

---

**Last Updated:** 2024-01-15
**API Version:** 0.1.0
**Documentation Version:** 1.0
