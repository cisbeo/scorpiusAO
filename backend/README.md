# ScorpiusAO Backend

Backend API for ScorpiusAO - AI Copilot for French Public Tender Bid Management.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+ with pgvector extension

### Local Development Setup

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. **Start infrastructure services**
```bash
docker-compose up -d postgres redis rabbitmq minio
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start API server**
```bash
uvicorn app.main:app --reload --port 8000
```

7. **Start Celery worker** (in separate terminal)
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

8. **Start Flower monitoring** (optional)
```bash
celery -A app.tasks.celery_app flower --port=5555
```

### Using Docker Compose (Full Stack)

```bash
docker-compose up -d --build
```

## 🔗 Quick Access Links

### Currently Running Services
- **PostgreSQL**: `localhost:5433` (user: `scorpius`, password: `scorpius_password`, db: `scorpius_db`)
- **Redis**: `localhost:6379`
- **RabbitMQ**: `localhost:5672`
  - 🌐 Management UI: http://localhost:15672 (guest/guest)
- **MinIO**: `localhost:9000`
  - 🌐 Console: http://localhost:9001 (minioadmin/minioadmin)

### When API is Running
- 🌐 API: http://localhost:8000
- 🌐 API Docs (Swagger): http://localhost:8000/docs
- 🌐 API Docs (ReDoc): http://localhost:8000/redoc
- 🌐 Health Check: http://localhost:8000/health
- 🌐 Flower (Celery Monitoring): http://localhost:5555

## API Endpoints

### Tenders
- `POST /api/v1/tenders/` - Create tender
- `POST /api/v1/tenders/upload` - Upload tender PDF
- `GET /api/v1/tenders/` - List tenders
- `GET /api/v1/tenders/{id}` - Get tender details
- `DELETE /api/v1/tenders/{id}` - Delete tender

### Analysis
- `GET /api/v1/analysis/tenders/{id}` - Get AI analysis
- `GET /api/v1/analysis/tenders/{id}/criteria` - Get extracted criteria
- `POST /api/v1/analysis/tenders/{id}/reanalyze` - Trigger re-analysis

### Proposals
- `POST /api/v1/proposals/` - Create proposal
- `GET /api/v1/proposals/tender/{tender_id}` - List proposals for tender
- `GET /api/v1/proposals/{id}` - Get proposal details
- `POST /api/v1/proposals/{id}/sections/generate` - Generate section
- `POST /api/v1/proposals/{id}/compliance-check` - Check compliance

### Search
- `POST /api/v1/search/` - Semantic search in knowledge base
- `GET /api/v1/search/similar-tenders/{id}` - Find similar tenders

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_tender_parser.py

# Run specific test
pytest -k "test_extract_criteria"
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/    # API route handlers
│   ├── core/                # Configuration and security
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic (LLM, RAG, Parser)
│   ├── tasks/               # Celery async tasks
│   └── utils/               # Helper utilities
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── docker-compose.yml       # Docker orchestration
├── Dockerfile              # Container definition
└── requirements.txt        # Python dependencies
```

## Core Services

### LLM Service
Handles Claude API interactions for:
- Tender analysis
- Criteria extraction
- Response generation
- Compliance checking

### RAG Service
Manages semantic search using pgvector:
- Document embedding
- Similarity search
- Context retrieval
- Reranking

### Parser Service
Extracts text from documents:
- PDF text extraction
- OCR for scanned documents
- Metadata extraction
- Structured data parsing

## Environment Variables

Key environment variables (see `.env.example`):

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key (for embeddings)
- `CELERY_BROKER_URL` - RabbitMQ URL
- `MINIO_ENDPOINT` - MinIO/S3 endpoint

## License

Proprietary - All rights reserved
