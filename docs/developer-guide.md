# 🚀 ScorpiusAO Developer Onboarding Guide

**Version:** 0.2.0
**Last Updated:** October 6, 2025
**Maintainer:** ScorpiusAO Team

---

## 📋 Table of Contents

1. [Welcome to ScorpiusAO](#welcome-to-scorpiusao)
2. [Prerequisites](#prerequisites)
3. [Quick Start (5 Minutes)](#quick-start-5-minutes)
4. [Development Environment Setup](#development-environment-setup)
5. [Project Structure](#project-structure)
6. [Common Development Workflows](#common-development-workflows)
7. [Testing Guide](#testing-guide)
8. [Contribution Guidelines](#contribution-guidelines)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [Additional Resources](#additional-resources)

---

## Welcome to ScorpiusAO

ScorpiusAO is an **AI copilot for bid managers** responding to French public tenders. It's a microservices architecture built with FastAPI, PostgreSQL (with pgvector), Redis, RabbitMQ, and powered by Claude AI.

### What Does ScorpiusAO Do?

- 📄 **Parses tender documents** (PDF extraction with OCR fallback)
- 🧠 **Analyzes tenders** using Claude Sonnet 4.5
- 🔍 **Semantic search** with RAG (Retrieval Augmented Generation)
- 💬 **Q&A on tender documents** with citation sources
- 📊 **Extracts criteria** and provides structured analysis
- ⚡ **Asynchronous processing** with Celery workers

### Tech Stack Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend API** | FastAPI + Uvicorn | Async REST API |
| **Database** | PostgreSQL 15 + pgvector | Data storage + vector embeddings |
| **Cache** | Redis 7 | LLM response cache + Q&A cache |
| **Message Queue** | RabbitMQ 3.12 | Async task broker |
| **Worker** | Celery 5.3 | Background processing |
| **Storage** | MinIO | S3-compatible object storage |
| **LLM** | Claude Sonnet 4.5 (Anthropic) | AI analysis |
| **Embeddings** | OpenAI text-embedding-3-small | Vector embeddings (1536 dim) |

---

## Prerequisites

### Required Software

Before you begin, ensure you have the following installed:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop))
- **Docker Compose** (included with Docker Desktop)
- **Git** ([Download](https://git-scm.com/downloads))
- **Code Editor** (VS Code recommended)

### Optional Tools

- **PostgreSQL client** (psql, pgAdmin, DBeaver)
- **Redis client** (RedisInsight, redis-cli)
- **API testing tool** (Postman, Insomnia, Bruno)

### Required API Keys

You'll need API keys for:

1. **Anthropic (Claude API)**: [Get API Key](https://console.anthropic.com/)
2. **OpenAI (Embeddings)**: [Get API Key](https://platform.openai.com/api-keys)

### System Requirements

- **RAM:** 8GB minimum, 16GB recommended
- **Disk Space:** 10GB minimum for Docker images and data
- **OS:** macOS, Linux, or Windows 10/11 with WSL2

---

## Quick Start (5 Minutes)

Get ScorpiusAO running in 5 minutes:

### 1. Clone the Repository

```bash
git clone https://github.com/cisbeo/scorpiusAO.git
cd scorpiusAO
```

### 2. Set Up Backend Environment

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

Required variables in `.env`:
```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Database (use defaults for local dev)
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# MinIO Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

### 4. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, RabbitMQ, MinIO
docker-compose up -d postgres redis rabbitmq minio
```

### 5. Run Database Migrations

```bash
# Apply all migrations
alembic upgrade head
```

### 6. Start the API Server

```bash
# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### 7. Start Celery Worker (New Terminal)

```bash
# Navigate to backend directory
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

### 8. Verify Installation

Open your browser and visit:

- 🌐 **API Documentation:** http://localhost:8000/docs
- ✅ **Health Check:** http://localhost:8000/health
- 📊 **RabbitMQ Management:** http://localhost:15672 (guest/guest)
- 💾 **MinIO Console:** http://localhost:9001 (minioadmin/minioadmin)

---

## Development Environment Setup

### Detailed Setup Instructions

#### Option 1: Local Development (Recommended for Active Development)

**Step 1: Python Environment**

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
.\venv\Scripts\activate.bat

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Step 2: Start Infrastructure**

```bash
# Start only infrastructure services
docker-compose up -d postgres redis rabbitmq minio elasticsearch

# Verify services are running
docker-compose ps
```

**Step 3: Database Setup**

```bash
# Create database schema
alembic upgrade head

# Verify migration status
alembic current

# View migration history
alembic history --verbose
```

**Step 4: Start Development Servers**

Terminal 1 - API Server:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 --log-level debug
```

Terminal 2 - Celery Worker:
```bash
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

Terminal 3 - Flower Monitoring (Optional):
```bash
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app flower --port=5555
```

#### Option 2: Full Docker Stack (Recommended for Testing)

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Service Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Docs (Swagger)** | http://localhost:8000/docs | N/A |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | N/A |
| **Health Check** | http://localhost:8000/health | N/A |
| **PostgreSQL** | localhost:5433 | scorpius / scorpius_password |
| **Redis** | localhost:6379 | No auth |
| **RabbitMQ Management** | http://localhost:15672 | guest / guest |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **Elasticsearch** | http://localhost:9200 | No auth |
| **Flower (Celery Monitor)** | http://localhost:5555 | N/A |

### IDE Configuration

#### Visual Studio Code

Recommended extensions:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "mtxr.sqltools",
    "mtxr.sqltools-driver-pg",
    "humao.rest-client",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

Python settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

---

## Project Structure

```
ScorpiusAO/
├── backend/                      # Backend API
│   ├── app/
│   │   ├── api/                  # API routes
│   │   │   └── v1/
│   │   │       └── endpoints/    # Endpoint handlers
│   │   │           ├── tenders.py
│   │   │           ├── analysis.py
│   │   │           ├── proposals.py
│   │   │           └── search.py
│   │   ├── core/                 # Configuration
│   │   │   ├── config.py         # Settings management
│   │   │   ├── prompts.py        # LLM prompts
│   │   │   └── celery_app.py     # Celery configuration
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── tender.py
│   │   │   ├── tender_document.py
│   │   │   ├── tender_analysis.py
│   │   │   ├── evaluation_criterion.py
│   │   │   ├── document_section.py
│   │   │   └── document_embedding.py
│   │   ├── schemas/              # Pydantic schemas
│   │   │   ├── tender.py
│   │   │   ├── analysis.py
│   │   │   └── proposal.py
│   │   ├── services/             # Business logic
│   │   │   ├── storage_service.py    # MinIO S3 storage
│   │   │   ├── parser_service.py     # PDF extraction
│   │   │   ├── llm_service.py        # Claude API
│   │   │   ├── rag_service.py        # RAG & embeddings
│   │   │   └── integration_service.py
│   │   ├── tasks/                # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   └── tender_tasks.py   # Async processing
│   │   ├── utils/                # Utilities
│   │   └── main.py               # FastAPI app entry
│   ├── alembic/                  # Database migrations
│   │   ├── versions/             # Migration files
│   │   └── env.py
│   ├── tests/                    # Test suite
│   ├── docker-compose.yml        # Docker orchestration
│   ├── Dockerfile               # Container definition
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Environment template
├── scripts/                      # Utility scripts
│   └── tests/                    # E2E test scripts
├── docs/                         # Documentation
│   ├── developer-guide.md        # This file
│   └── RAG_SERVICE_PLAN_V2.md
├── ARCHITECTURE.md               # Architecture docs
├── PROJECT_STATUS.md             # Project status
├── CLAUDE.md                     # Claude Code config
└── README.md                     # Main README
```

### Key Directories Explained

- **`app/api/v1/endpoints/`**: REST API route handlers
- **`app/services/`**: Business logic layer (LLM, RAG, Parser, Storage)
- **`app/models/`**: Database models using SQLAlchemy ORM
- **`app/schemas/`**: Request/response validation with Pydantic
- **`app/tasks/`**: Async background tasks with Celery
- **`alembic/versions/`**: Database migration files

---

## Common Development Workflows

### 1. Creating a New API Endpoint

**Example: Add a new endpoint to delete tender analysis**

**Step 1: Define Schema** (`app/schemas/analysis.py`)

```python
from pydantic import BaseModel
from typing import Optional

class AnalysisDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_id: Optional[str] = None
```

**Step 2: Create Endpoint** (`app/api/v1/endpoints/analysis.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.analysis import AnalysisDeleteResponse
from app.models.tender_analysis import TenderAnalysis

router = APIRouter()

@router.delete("/tenders/{tender_id}/analysis", response_model=AnalysisDeleteResponse)
async def delete_tender_analysis(
    tender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete tender analysis by tender ID"""

    # Query analysis
    result = await db.execute(
        select(TenderAnalysis).where(TenderAnalysis.tender_id == tender_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Delete
    await db.delete(analysis)
    await db.commit()

    return AnalysisDeleteResponse(
        success=True,
        message="Analysis deleted successfully",
        deleted_id=str(analysis.id)
    )
```

**Step 3: Register Route** (`app/api/v1/api.py`)

```python
from app.api.v1.endpoints import analysis

api_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["analysis"]
)
```

**Step 4: Test**

```bash
# Using curl
curl -X DELETE "http://localhost:8000/api/v1/analysis/tenders/{tender_id}/analysis"

# Using httpie
http DELETE localhost:8000/api/v1/analysis/tenders/{tender_id}/analysis
```

### 2. Adding a Database Migration

**Scenario: Add a new column to tenders table**

```bash
# Step 1: Modify model (app/models/tender.py)
# Add new column:
# priority = Column(String(20), default="medium")

# Step 2: Generate migration
alembic revision --autogenerate -m "add_priority_to_tenders"

# Step 3: Review generated migration file
# Check: alembic/versions/xxxxx_add_priority_to_tenders.py

# Step 4: Apply migration
alembic upgrade head

# Step 5: Verify in database
docker exec -it scorpius-postgres psql -U scorpius -d scorpius_db -c "\d tenders"
```

### 3. Creating a New Background Task

**Example: Add email notification task**

**Step 1: Define Task** (`app/tasks/notification_tasks.py`)

```python
from app.tasks.celery_app import celery_app
from app.core.config import settings
import smtplib
from email.mime.text import MIMEText

@celery_app.task(name="send_analysis_complete_email")
def send_analysis_complete_email(tender_id: str, user_email: str):
    """Send email notification when analysis completes"""

    msg = MIMEText(f"Analysis complete for tender {tender_id}")
    msg['Subject'] = 'Tender Analysis Complete'
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = user_email

    # Send email (configure SMTP settings)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.send_message(msg)

    return {"status": "sent", "tender_id": tender_id}
```

**Step 2: Trigger Task** (in your endpoint or another task)

```python
from app.tasks.notification_tasks import send_analysis_complete_email

# Async trigger
send_analysis_complete_email.delay(
    tender_id=str(tender.id),
    user_email=user.email
)
```

### 4. Working with RAG Service

**Example: Add document to knowledge base**

```python
from app.services.rag_service import RAGService
from app.core.database import get_db

async def ingest_document_example():
    """Example: Ingest a document for RAG"""

    async with get_db() as db:
        rag_service = RAGService()

        # Document sections (from parser)
        sections = [
            {"content": "Section 1: Project overview...", "metadata": {"page": 1}},
            {"content": "Section 2: Technical requirements...", "metadata": {"page": 2}},
        ]

        # Create embeddings and store
        await rag_service.ingest_document(
            db=db,
            document_id="doc-123",
            sections=sections,
            document_type="tender"
        )

        print("Document ingested successfully!")
```

**Example: Search with RAG**

```python
async def search_example():
    """Example: Semantic search"""

    async with get_db() as db:
        rag_service = RAGService()

        results = await rag_service.search(
            db=db,
            query="What are the technical requirements?",
            document_type="tender",
            top_k=5
        )

        for result in results:
            print(f"Score: {result['score']:.3f}")
            print(f"Text: {result['text'][:100]}...")
            print(f"Metadata: {result['metadata']}\n")
```

### 5. Testing Claude API Integration

**Example: Test LLM analysis**

```python
from app.services.llm_service import LLMService

async def test_claude_analysis():
    """Test Claude API analysis"""

    llm_service = LLMService()

    # Sample tender sections
    sections = [
        {"title": "Scope of Work", "content": "Build a web application..."},
        {"title": "Duration", "content": "Contract duration: 12 months"},
    ]

    # Analyze with Claude
    analysis = await llm_service.analyze_tender(
        tender_id="test-123",
        sections=sections
    )

    print("Analysis Results:")
    print(f"Summary: {analysis['summary']}")
    print(f"Criteria: {analysis['criteria']}")
    print(f"Recommendations: {analysis['recommendations']}")
```

---

## Testing Guide

### Running Tests

```bash
# Activate virtual environment
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_parser_service.py

# Run specific test function
pytest tests/test_llm_service.py::test_analyze_tender

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Writing Tests

**Example: Unit Test for Parser Service**

```python
# tests/test_parser_service.py
import pytest
from app.services.parser_service import ParserService

@pytest.fixture
def parser_service():
    return ParserService()

@pytest.mark.asyncio
async def test_extract_text_from_pdf(parser_service, tmp_path):
    """Test PDF text extraction"""

    # Create sample PDF (or use fixture)
    pdf_path = tmp_path / "sample.pdf"
    # ... create PDF ...

    # Extract text
    result = await parser_service.extract_text(str(pdf_path))

    assert result['success'] is True
    assert len(result['text']) > 0
    assert 'metadata' in result

@pytest.mark.asyncio
async def test_detect_structure(parser_service):
    """Test hierarchical structure detection"""

    sample_text = """
    1. Introduction
    1.1 Background
    2. Requirements
    2.1 Technical
    """

    sections = await parser_service.detect_structure(sample_text)

    assert len(sections) > 0
    assert any(s['title'] == 'Introduction' for s in sections)
```

**Example: Integration Test for API Endpoint**

```python
# tests/test_api_tenders.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_tender():
    """Test tender creation endpoint"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tenders/",
            json={
                "title": "Test Tender",
                "reference": "REF-001",
                "deadline": "2025-12-31T23:59:59"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data['title'] == "Test Tender"
    assert 'id' in data

@pytest.mark.asyncio
async def test_upload_tender_pdf():
    """Test PDF upload endpoint"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        files = {'file': ('test.pdf', open('tests/fixtures/sample.pdf', 'rb'), 'application/pdf')}
        response = await client.post("/api/v1/tenders/upload", files=files)

    assert response.status_code == 200
    assert 'task_id' in response.json()
```

### E2E Testing Scripts

Located in `scripts/tests/`:

```bash
# Run full E2E test suite
cd scripts/tests
./run_all_tests.sh

# Individual test scripts
python 01_upload_tender.py
python 02_check_processing.py
python 03_get_analysis.py
python 04_test_rag_search.py
python 05_test_qa.py
```

---

## Contribution Guidelines

### Git Workflow

**Branch Naming Convention:**

- `feature/` - New features (e.g., `feature/rag-service`)
- `fix/` - Bug fixes (e.g., `fix/parser-ocr-issue`)
- `docs/` - Documentation (e.g., `docs/api-guide`)
- `refactor/` - Code refactoring (e.g., `refactor/llm-service`)
- `test/` - Test additions (e.g., `test/integration-tests`)

**Workflow:**

```bash
# 1. Create feature branch
git checkout -b feature/my-new-feature

# 2. Make changes and commit
git add .
git commit -m "feat: add new feature description"

# 3. Push to remote
git push origin feature/my-new-feature

# 4. Create Pull Request on GitHub
# 5. After review and approval, merge to main
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

**Examples:**

```bash
git commit -m "feat(rag): implement semantic search with pgvector"
git commit -m "fix(parser): handle OCR fallback for scanned PDFs"
git commit -m "docs: update API documentation with new endpoints"
git commit -m "test(llm): add unit tests for Claude integration"
```

### Code Quality Standards

**1. Code Formatting**

```bash
# Format with Black
black app/ tests/

# Lint with Ruff
ruff check app/ tests/

# Type checking with mypy
mypy app/
```

**2. Type Hints**

Always use type hints:

```python
from typing import List, Optional, Dict, Any

async def process_tender(
    tender_id: str,
    sections: List[Dict[str, Any]],
    force_reprocess: bool = False
) -> Optional[Dict[str, Any]]:
    """Process tender with type hints"""
    pass
```

**3. Documentation**

Use docstrings for all functions:

```python
async def analyze_tender(tender_id: str, sections: List[dict]) -> dict:
    """
    Analyze tender using Claude AI.

    Args:
        tender_id: Unique tender identifier
        sections: List of document sections with content

    Returns:
        Analysis results containing summary, criteria, and recommendations

    Raises:
        ValueError: If sections are empty
        APIError: If Claude API fails
    """
    pass
```

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guide (Black + Ruff)
- [ ] All tests pass (`pytest`)
- [ ] New features have tests (coverage > 80%)
- [ ] Documentation is updated
- [ ] Type hints are added
- [ ] Commit messages follow convention
- [ ] No sensitive data in commits (API keys, passwords)
- [ ] PR description explains changes clearly

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Database Connection Errors

**Error:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres

# Verify connection
docker exec -it scorpius-postgres psql -U scorpius -d scorpius_db
```

#### 2. Celery Worker Not Processing Tasks

**Error:** Tasks stuck in pending state

**Solution:**
```bash
# Check Celery worker logs
celery -A app.tasks.celery_app worker --loglevel=debug

# Check RabbitMQ
docker-compose logs rabbitmq

# Restart Celery worker
# Ctrl+C to stop, then restart with:
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Clear stuck tasks (if needed)
celery -A app.tasks.celery_app purge
```

#### 3. Redis Connection Issues

**Error:** `redis.exceptions.ConnectionError`

**Solution:**
```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
docker exec -it scorpius-redis redis-cli ping
# Should return: PONG

# Restart Redis
docker-compose restart redis
```

#### 4. MinIO/S3 Upload Failures

**Error:** `S3Error: Access Denied`

**Solution:**
```bash
# Check MinIO is running
docker-compose ps minio

# Verify credentials in .env
cat .env | grep MINIO

# Test MinIO access
curl http://localhost:9000/minio/health/live

# Check bucket exists (using MinIO console)
# Visit: http://localhost:9001
```

#### 5. pgvector Extension Not Found

**Error:** `sqlalchemy.exc.ProgrammingError: extension "vector" does not exist`

**Solution:**
```bash
# Verify pgvector image
docker-compose ps postgres
# Should use: pgvector/pgvector:pg15

# Create extension manually
docker exec -it scorpius-postgres psql -U scorpius -d scorpius_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify
docker exec -it scorpius-postgres psql -U scorpius -d scorpius_db -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

#### 6. Alembic Migration Conflicts

**Error:** `Multiple head revisions are present`

**Solution:**
```bash
# Check migration history
alembic history

# Merge heads
alembic merge heads -m "merge_migration_heads"

# Apply merge
alembic upgrade head
```

#### 7. API Key Issues (Claude/OpenAI)

**Error:** `anthropic.APIError: Invalid API key`

**Solution:**
```bash
# Verify API keys are set
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Check .env file
cat backend/.env | grep API_KEY

# Restart API server after updating keys
# Ctrl+C and restart:
uvicorn app.main:app --reload
```

#### 8. Docker Disk Space Issues

**Error:** `no space left on device`

**Solution:**
```bash
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a --volumes

# Remove specific volumes
docker-compose down -v
docker volume prune
```

### Debug Mode

Enable detailed logging:

```bash
# API server with debug logging
uvicorn app.main:app --reload --log-level debug

# Celery with debug logging
celery -A app.tasks.celery_app worker --loglevel=debug

# Check application logs
tail -f logs/app.log  # If logging to file
```

---

## FAQ

### General Questions

**Q: What Python version should I use?**
A: Python 3.11 or higher. The project is tested on Python 3.11.

**Q: Can I use this project on Windows?**
A: Yes, but WSL2 (Windows Subsystem for Linux) is recommended for better compatibility with Docker.

**Q: How much does it cost to run the AI features?**
A: Costs vary based on usage:
- Claude API: ~$0.12 per tender analysis
- OpenAI Embeddings: ~$0.016 per tender
- Total: ~$0.14 per tender (estimated)

### Development Questions

**Q: How do I add a new LLM prompt?**
A: Edit `app/core/prompts.py` and add your prompt template. Use Jinja2 syntax for variables.

**Q: Where are the API routes defined?**
A: Routes are in `app/api/v1/endpoints/`. Each file corresponds to a resource (tenders, analysis, etc.).

**Q: How do I change the database schema?**
A: Modify models in `app/models/`, then create a migration with `alembic revision --autogenerate`.

**Q: Can I use a different LLM provider?**
A: Yes, create a new service in `app/services/` implementing the same interface as `LLMService`.

### Deployment Questions

**Q: Is this production-ready?**
A: The backend MVP is functional but needs additional security hardening, monitoring, and scaling configurations for production.

**Q: How do I deploy to production?**
A: Production deployment guide is coming soon. Consider using:
- Kubernetes for orchestration
- Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- Managed Redis (ElastiCache, Cloud Memorystore)
- Cloud object storage (AWS S3, GCS)

**Q: What about authentication?**
A: JWT authentication is planned but not yet implemented. Current version focuses on core features.

### Troubleshooting Questions

**Q: Tests are failing with import errors**
A: Ensure you're in the virtual environment and all dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Q: Docker services won't start**
A: Check port conflicts. Default ports used: 5433, 6379, 5672, 9000, 8000. Change in `docker-compose.yml` if needed.

**Q: How do I reset the database?**
A:
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d postgres
alembic upgrade head  # Re-apply migrations
```

---

## Additional Resources

### Documentation

- **[ARCHITECTURE.md](/Users/cedric/Dev/projects/ScorpiusAO/ARCHITECTURE.md)** - System architecture overview
- **[PROJECT_STATUS.md](/Users/cedric/Dev/projects/ScorpiusAO/PROJECT_STATUS.md)** - Current project status and roadmap
- **[CLAUDE.md](/Users/cedric/Dev/projects/ScorpiusAO/CLAUDE.md)** - Claude Code development guide
- **[Backend README](/Users/cedric/Dev/projects/ScorpiusAO/backend/README.md)** - Backend-specific documentation
- **[RAG Service Plan](/Users/cedric/Dev/projects/ScorpiusAO/docs/RAG_SERVICE_PLAN_V2.md)** - RAG implementation details

### External Resources

#### FastAPI
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)

#### PostgreSQL & pgvector
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)

#### Claude AI
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Prompt Engineering](https://docs.anthropic.com/claude/docs/prompt-engineering)

#### Celery
- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Best Practices](https://denibertovic.com/posts/celery-best-practices/)

#### Testing
- [Pytest Documentation](https://docs.pytest.org/)
- [Testing FastAPI Applications](https://fastapi.tiangolo.com/tutorial/testing/)

### Community & Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/cisbeo/scorpiusAO/issues)
- **GitHub Discussions:** [Ask questions and share ideas](https://github.com/cisbeo/scorpiusAO/discussions)
- **Project Wiki:** Coming soon

### Code Examples

Check the `Examples/` directory for:
- Sample tender documents
- API usage examples
- Integration examples
- Test fixtures

---

## Quick Reference

### Essential Commands Cheat Sheet

```bash
# Environment Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Docker Services
docker-compose up -d                    # Start all services
docker-compose down                     # Stop all services
docker-compose down -v                  # Stop and remove volumes
docker-compose logs -f api              # Follow API logs
docker-compose ps                       # List running services

# Database
alembic upgrade head                    # Apply migrations
alembic downgrade -1                    # Rollback one migration
alembic revision --autogenerate -m "msg" # Create migration
alembic current                         # Show current version

# Development Servers
uvicorn app.main:app --reload           # Start API
celery -A app.tasks.celery_app worker --loglevel=info  # Start worker
celery -A app.tasks.celery_app flower   # Start monitoring

# Testing
pytest                                  # Run all tests
pytest -v                              # Verbose output
pytest --cov=app                       # With coverage
pytest -k "test_name"                  # Run specific test

# Code Quality
black app/ tests/                      # Format code
ruff check app/ tests/                 # Lint code
mypy app/                              # Type check
```

### Environment Variables Quick Reference

```bash
# API Keys (Required)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Database
DATABASE_URL=postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db

# Caching
REDIS_URL=redis://localhost:6379/0

# Task Queue
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check existing documentation** in the `/docs` folder
2. **Search GitHub issues** for similar problems
3. **Review error logs** for detailed error messages
4. **Ask in GitHub Discussions** with:
   - Clear description of the issue
   - Steps to reproduce
   - Error messages and logs
   - Environment details (OS, Python version, Docker version)

---

**Welcome to the ScorpiusAO team! Happy coding!** 🚀

---

*Last updated: October 6, 2025*
*For updates to this guide, please submit a PR or open an issue.*
