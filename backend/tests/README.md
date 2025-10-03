# 🧪 Tests ScorpiusAO

**Framework**: pytest
**Coverage Target**: > 80%
**Last Update**: 3 octobre 2025

---

## 📋 Quick Start

### Run All Tests

```bash
# Local
cd backend
pytest

# Docker
docker exec scorpius-celery-worker pytest /app/tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests (with APIs)
pytest -m integration

# E2E tests (full pipeline)
pytest -m e2e

# All except slow tests
pytest -m "not slow"

# RAG Service tests only
pytest -m rag
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html
```

---

## 📁 Test Structure

```
tests/
├── README.md                      # This file
├── TESTS_ANALYSIS_REPORT.md       # Migration analysis
├── conftest.py                    # Shared fixtures
├── test_rag_service.py            # RAG unit tests (5 tests)
├── test_rag_e2e.py                # RAG E2E tests (4 tests)
├── test_e2e_pipeline.py           # Full pipeline E2E (6 tests) ✅
└── [planned migrations]
    ├── test_llm_integration.py    # LLM integration tests
    └── test_extraction_quality.py # Extraction quality tests
```

---

## 🎯 Test Markers

Pytest markers help organize and run tests selectively.

| Marker | Description | Example |
|--------|-------------|---------|
| `@pytest.mark.unit` | Isolated unit tests | `test_chunk_sections()` |
| `@pytest.mark.integration` | Tests with external APIs | `test_claude_analysis()` |
| `@pytest.mark.e2e` | End-to-end pipeline tests | `test_full_tender_pipeline()` |
| `@pytest.mark.quality` | Quality validation | `test_itil_detection()` |
| `@pytest.mark.slow` | Tests > 5 seconds | `test_extract_all_pdfs()` |
| `@pytest.mark.rag` | RAG Service specific | `test_vector_search()` |

### Usage Examples

```python
@pytest.mark.unit
def test_create_embedding_sync():
    """Unit test for embedding creation"""
    pass

@pytest.mark.integration
@pytest.mark.slow
async def test_llm_full_analysis():
    """Integration test with Claude API (slow)"""
    pass

@pytest.mark.e2e
@pytest.mark.quality
def test_section_extraction_quality():
    """E2E test validating extraction quality"""
    pass
```

---

## 🔧 Fixtures

Shared fixtures are defined in `conftest.py`.

### Database Fixtures

```python
def test_example(db_session):
    """Use database session"""
    # db_session auto-rolls back after test
    pass
```

### Tender Fixtures

```python
def test_with_tender(sample_tender):
    """Use pre-created tender"""
    assert sample_tender.id is not None

def test_with_documents(sample_tender_with_documents):
    """Use tender with uploaded documents"""
    tender, documents = sample_tender_with_documents
    assert len(documents) == 2
```

### Service Fixtures

```python
def test_rag(rag_service):
    """Use RAG Service instance"""
    result = rag_service.chunk_sections_semantic(sections)

def test_llm(llm_service):
    """Use LLM Service instance"""
    pass
```

### Mock Fixtures

```python
def test_without_api_call(mock_claude_response):
    """Use mocked Claude response (no API call)"""
    # Useful for CI/CD without API keys
    pass
```

---

## 📊 Current Test Coverage

### ✅ RAG Service (Implemented - Day 3)

**File**: `test_rag_service.py` (5 unit tests)
- `test_create_embedding_sync()` - Embedding creation
- `test_chunk_sections_semantic()` - Chunking strategy
- `test_ingest_and_retrieve_sync()` - E2E RAG flow
- `test_small_section_merging()` - Merge logic
- `test_large_section_splitting()` - Split logic

**File**: `test_rag_e2e.py` (4 E2E tests)
- `test_semantic_search_quality()` - Recall@5: 100% ✅
- `test_answer_quality()` - Coverage: 80% ✅
- `test_cost_tracking()` - Cost: $0.016/tender ✅
- `test_chunking_strategy()` - Chunking validation ✅

**Metrics**:
- Recall@5: 100% (target: >80%)
- Answer Quality: 80% (target: >80%)
- Cost: $0.016/tender (target: <$0.02)

### ✅ Full Pipeline E2E (Implemented - 3 oct 2025)

**File**: `test_e2e_pipeline.py` (6 E2E tests)
- `test_create_tender()` - Tender creation with metadata
- `test_upload_documents()` - MinIO upload + DB records (3 PDFs)
- `test_extract_sections()` - Parser service (377 sections expected)
- `test_create_embeddings()` - RAG ingestion + retrieval test
- `test_hierarchical_structure()` - LLM optimization (>10% reduction)
- `test_itil_process_detection()` - Quality validation (18 ITIL processes)

**Expected Results (VSGP-AO)**:
- Total sections: 350-400 (target: 377)
- TOC: ≥30%, Key sections: ≥25%
- ITIL processes: ≥18
- Hierarchy reduction: ≥10%

### ⏳ LLM Service (Planned)

- [ ] `test_analyze_tender()` - Claude API integration
- [ ] `test_extract_criteria()` - Criteria extraction
- [ ] `test_cost_calculation()` - Token tracking

### ⏳ Extraction Quality (Planned)

- [ ] `test_section_distribution()` - TOC/key section percentages
- [ ] `test_itil_detection_detailed()` - 19 ITIL processes validation
- [ ] `test_hierarchy_relationships()` - Parent-child validation

---

## 🎯 Expected Test Results

### Extraction Quality (from VSGP-AO tender)

```
✅ Documents: 3 (CCTP, CCAP, RC)
✅ Sections extracted: 377
   - CCTP: 202 sections (56 TOC, 46 key)
   - CCAP: 128 sections (47 TOC, 49 key)
   - RC: 47 sections (22 TOC, 13 key)
✅ Total key sections: 106 (28%)
✅ Total TOC: 135 (36%)
✅ ITIL processes detected: 18-19/19
```

### LLM Analysis

```
✅ Input tokens: 30-35k
✅ Output tokens: 1.5-2k
✅ Cost: $0.10-0.15
✅ Analysis contains:
   - Summary
   - 10+ key requirements
   - 5+ risks identified
   - ITIL processes mentioned
   - 10+ mandatory documents
   - 5+ recommendations
```

### RAG Q&A

```
✅ Recall@5: 100%
✅ Answer quality: 80%
✅ Cost per tender: $0.016
✅ Response time (cached): <100ms
✅ Response time (uncached): 3-4s
```

---

## 🐛 Troubleshooting

### Import Errors

```bash
# Ensure you're in backend directory
cd backend

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection string in .env
cat .env | grep DATABASE_URL
```

### API Key Errors (Integration Tests)

```bash
# Skip integration tests if no API keys
pytest -m "not integration"

# Or set API keys in .env
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key
```

### Slow Tests

```bash
# Skip slow tests for quick feedback
pytest -m "not slow"

# Run slow tests separately
pytest -m slow -v
```

---

## 🚀 CI/CD Integration (Planned)

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest -m "not integration and not slow" --cov=app
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 📈 Coverage Goals

| Component | Current | Target | Status |
|-----------|---------|--------|--------|
| RAG Service | ~80% | 80% | ✅ |
| LLM Service | ~30% | 80% | ⏳ |
| Parser Service | ~20% | 80% | ⏳ |
| Pipeline | ~40% | 80% | ⏳ |
| **Overall** | ~50% | **80%** | ⏳ |

---

## 📝 Writing New Tests

### Test Naming Convention

```python
# Good
def test_create_embedding_returns_1536_dimensions():
    pass

def test_chunk_sections_merges_small_sections():
    pass

# Bad (not descriptive)
def test_embedding():
    pass

def test_chunk():
    pass
```

### Test Structure (AAA Pattern)

```python
def test_something():
    # Arrange
    input_data = {"key": "value"}
    expected = "result"

    # Act
    result = function_to_test(input_data)

    # Assert
    assert result == expected
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

---

## 🔗 References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Backend README](../README.md)
- [TESTS_ANALYSIS_REPORT.md](TESTS_ANALYSIS_REPORT.md) - Migration plan

---

## ✅ Test Checklist

Before merging PR:

- [ ] All tests pass locally (`pytest`)
- [ ] Coverage > 70% for new code (`pytest --cov`)
- [ ] No integration test failures (or skipped with reason)
- [ ] Appropriate markers added (`@pytest.mark.unit`, etc.)
- [ ] Docstrings added to test functions
- [ ] README updated if new test category added

---

**Last Update**: 3 octobre 2025
**Maintainer**: Équipe ScorpiusAO
