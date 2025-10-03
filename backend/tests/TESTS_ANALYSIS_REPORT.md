# 📊 Analyse des Tests - Consolidation

**Date**: 3 octobre 2025
**Objectif**: Analyser `scripts/tests/` et consolider dans `backend/tests/`

---

## 📁 État Actuel

### Scripts dans `scripts/tests/` (9 fichiers)

| Fichier | Type | Status | Action Recommandée |
|---------|------|--------|-------------------|
| `test_fresh_e2e.py` | E2E complet | ✅ Valide | 🔄 Migrer + Moderniser |
| `test_end_to_end.py` | E2E alternatif | ⚠️ Doublon | ❌ Obsolète (dupliqu é avec fresh) |
| `test_hierarchical_analysis.py` | Analyse hiérarchie | ✅ Valide | 🔄 Migrer (tests unitaires) |
| `test_llm_analysis.py` | Test LLM | ✅ Valide | 🔄 Migrer (intégration) |
| `test_hierarchy.py` | Test hiérarchie | ⚠️ Doublon | ❌ Obsolète (couvert par hierarchical) |
| `test_dce_v1.py` | Test ancien DCE | ❌ Obsolète | ❌ Supprimer |
| `analyze_extraction_quality.py` | Analyse qualité | ✅ Utile | 🔄 Migrer (pytest) |
| `README.md` | Documentation | ✅ Valide | 🔄 Fusionner avec tests/README.md |
| `TEST_END_TO_END.md` | Doc E2E | ✅ Valide | 🔄 Fusionner avec tests/README.md |

### Tests dans `backend/tests/` (2 fichiers)

| Fichier | Type | Coverage | Status |
|---------|------|----------|--------|
| `test_rag_service.py` | Unit tests RAG | 5 tests | ✅ Récent (Day 3) |
| `test_rag_e2e.py` | E2E RAG | 4 tests | ✅ Récent (Day 3) |

---

## 🎯 Plan de Consolidation

### Phase 1: Migration Tests E2E (Priorité HAUTE)

#### 1.1 Migrer `test_fresh_e2e.py` → `backend/tests/test_e2e_pipeline.py`

**Modernisations nécessaires**:
- ✅ Convertir en pytest (fixtures, markers)
- ✅ Ajouter assertions précises (pas juste print)
- ✅ Intégrer avec RAG Service (STEP 2 & 5 embeddings)
- ✅ Séparer en tests atomiques:
  - `test_create_tender()`
  - `test_upload_documents()`
  - `test_extract_sections()`
  - `test_create_embeddings()`
  - `test_llm_analysis()`

**Exemple modernisation**:
```python
# ❌ Ancien (scripts/tests/test_fresh_e2e.py)
print(f"✅ {total_sections} sections extraites")

# ✅ Nouveau (backend/tests/test_e2e_pipeline.py)
@pytest.mark.e2e
def test_section_extraction(db_session, uploaded_documents):
    sections = extract_all_sections(db_session)
    assert len(sections) == 377, f"Expected 377 sections, got {len(sections)}"
    assert len([s for s in sections if s.is_key_section]) >= 106
```

#### 1.2 Migrer `test_llm_analysis.py` → `backend/tests/test_llm_integration.py`

**Modernisations**:
- ✅ Pytest avec fixtures async
- ✅ Mock Claude API (optionnel pour CI/CD)
- ✅ Validation JSON schema réponse
- ✅ Tests coûts et tokens

**Exemple**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_tender_analysis(llm_service, sample_sections):
    result = await llm_service.analyze_tender(
        tender_id="test-id",
        sections=sample_sections
    )

    assert result.summary is not None
    assert len(result.key_requirements) > 0
    assert len(result.risks) > 0
    # Validate cost < $0.20
    assert result.cost < 0.20
```

#### 1.3 Migrer `test_hierarchical_analysis.py` → `backend/tests/test_hierarchical_structure.py`

**Tests unitaires**:
- `test_build_hierarchy()`
- `test_token_reduction()`
- `test_parent_child_relationships()`

---

### Phase 2: Migration Tests Analyse (Priorité MOYENNE)

#### 2.1 Migrer `analyze_extraction_quality.py` → `backend/tests/test_extraction_quality.py`

**Conversion en pytest**:
```python
@pytest.mark.quality
def test_section_distribution(db_session):
    sections = db_session.query(DocumentSection).all()

    # Statistiques
    total = len(sections)
    toc_sections = len([s for s in sections if s.is_toc])
    key_sections = len([s for s in sections if s.is_key_section])

    # Assertions
    assert toc_sections / total >= 0.30, "TOC sections should be >= 30%"
    assert key_sections / total >= 0.25, "Key sections should be >= 25%"

@pytest.mark.quality
def test_itil_process_detection(db_session):
    """Validate 18 ITIL processes detected"""
    itil_sections = db_session.query(DocumentSection).filter(
        DocumentSection.section_number.like('4.1.5.%')
    ).all()

    assert len(itil_sections) >= 18, "Should detect at least 18 ITIL processes"
```

---

### Phase 3: Nettoyage (Priorité BASSE)

#### 3.1 Supprimer fichiers obsolètes

```bash
# Scripts à supprimer
scripts/tests/test_end_to_end.py     # Doublon de test_fresh_e2e
scripts/tests/test_hierarchy.py      # Doublon de test_hierarchical
scripts/tests/test_dce_v1.py         # Ancien format DCE
```

#### 3.2 Fusionner documentation

**Créer** `backend/tests/README.md` consolidé:
- Quick start pytest
- Markers disponibles (@pytest.mark.e2e, @pytest.mark.integration)
- Fixtures communes
- Guide running tests (local + Docker)
- Expected results (377 sections, etc.)

---

## 🧪 Structure Cible `backend/tests/`

```
backend/tests/
├── __init__.py
├── README.md                         # Documentation consolidée
├── conftest.py                       # Fixtures pytest communes
├── test_rag_service.py               # ✅ Unit tests RAG (existant)
├── test_rag_e2e.py                   # ✅ E2E tests RAG (existant)
├── test_e2e_pipeline.py              # 🔄 Migré de test_fresh_e2e.py
├── test_llm_integration.py           # 🔄 Migré de test_llm_analysis.py
├── test_hierarchical_structure.py    # 🔄 Migré de test_hierarchical_analysis.py
├── test_extraction_quality.py        # 🔄 Migré de analyze_extraction_quality.py
└── fixtures/
    ├── sample_pdfs.py                # Fixtures PDFs test
    └── sample_sections.py            # Fixtures sections test
```

---

## 🔧 Configuration Pytest

### `backend/tests/conftest.py` (à créer)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

@pytest.fixture(scope="session")
def db_engine():
    """Database engine for all tests"""
    return create_engine(settings.database_url_sync)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Fresh database session for each test"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_tender(db_session):
    """Create sample tender for tests"""
    from app.models.tender import Tender
    tender = Tender(
        title="Test Tender VSGP",
        organization="Test Org",
        status="new"
    )
    db_session.add(tender)
    db_session.commit()
    return tender

@pytest.fixture
def sample_sections():
    """Sample sections for LLM tests"""
    return [
        {
            "section_number": "1",
            "title": "Durée du marché",
            "content": "Le marché est conclu pour 4 ans...",
            "is_key_section": True
        },
        # ... more sections
    ]
```

### `backend/pytest.ini` (à créer)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    e2e: End-to-end tests (full pipeline)
    integration: Integration tests (with external APIs)
    unit: Unit tests (isolated components)
    quality: Quality validation tests
    slow: Slow tests (> 5 seconds)

addopts =
    -v
    --tb=short
    --strict-markers
    -p no:warnings
```

---

## 📊 Markers Pytest

| Marker | Usage | Exemple |
|--------|-------|---------|
| `@pytest.mark.e2e` | Tests E2E complets | `test_full_pipeline()` |
| `@pytest.mark.integration` | Tests avec APIs externes | `test_llm_analysis()` |
| `@pytest.mark.unit` | Tests unitaires isolés | `test_chunk_sections()` |
| `@pytest.mark.quality` | Validation qualité | `test_section_distribution()` |
| `@pytest.mark.slow` | Tests lents (>5s) | `test_extract_all_pdfs()` |

**Exemples de commandes**:
```bash
# Run all tests
pytest

# Run only E2E tests
pytest -m e2e

# Run all except slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## 🎯 Priorités d'Implémentation

### Sprint Actuel (1-2 jours)

1. ✅ Créer `conftest.py` avec fixtures communes
2. ✅ Créer `pytest.ini` avec markers
3. ✅ Migrer `test_fresh_e2e.py` → `test_e2e_pipeline.py` (modernisé)
   - ✅ 6 tests atomiques: tender creation, upload, extraction, embeddings, hierarchy, ITIL
   - ✅ Fixtures: e2e_tender, uploaded_documents, pdf_files_path
   - ✅ Assertions avec expected results (377 sections, 30% TOC, 25% key, 18 ITIL)
   - ✅ Markers: @pytest.mark.e2e, quality, slow, rag
   - ✅ RAG Service integration (embeddings + retrieval test)
4. ✅ Créer `README.md` consolidé dans `backend/tests/`
5. ⏳ Supprimer doublons dans `scripts/tests/`

### Sprint +1 (optionnel)

6. ⏳ Migrer `test_llm_analysis.py` → `test_llm_integration.py`
7. ⏳ Migrer `test_hierarchical_analysis.py` → `test_hierarchical_structure.py`
8. ⏳ Migrer `analyze_extraction_quality.py` → `test_extraction_quality.py`
9. ⏳ CI/CD GitHub Actions avec pytest

---

## ✅ Validation

### Critères de Succès

- [ ] Tous les tests migrés dans `backend/tests/`
- [ ] Tous les tests passent avec pytest
- [ ] Coverage > 70% (objectif: 80%)
- [ ] Documentation tests complète
- [ ] Scripts obsolètes supprimés
- [ ] CI/CD configuré (optionnel)

### Commandes de Test

```bash
# Local
cd backend
pytest -v

# Docker
docker exec scorpius-celery-worker pytest /app/tests/ -v

# Avec coverage
docker exec scorpius-celery-worker pytest /app/tests/ --cov=app --cov-report=term
```

---

## 📝 Notes

### Pourquoi Migrer?

1. **Standardisation**: pytest est le standard Python
2. **Assertions**: Meilleure validation qu'avec `print()`
3. **Fixtures**: Réutilisation code test
4. **Markers**: Run tests sélectifs
5. **Coverage**: Mesure précise couverture
6. **CI/CD**: Intégration GitHub Actions

### Tests à Garder dans `scripts/tests/`

Aucun - tous doivent être migrés dans `backend/tests/` pour:
- Centralisation
- pytest compatibility
- CI/CD integration
- Meilleure maintenance

---

**Dernière mise à jour**: 3 octobre 2025
**Status**: Analyse complète - Prêt pour migration
