"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings


# ==================== Database Fixtures ====================

@pytest.fixture(scope="session")
def db_engine():
    """
    Database engine shared across all tests in session.
    """
    engine = create_engine(settings.database_url_sync)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Fresh database session for each test function.
    Automatically rolls back changes after test.
    """
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ==================== Tender Fixtures ====================

@pytest.fixture
def sample_tender(db_session):
    """
    Create a sample tender for testing.
    """
    from app.models.tender import Tender
    from uuid import uuid4
    from datetime import datetime

    tender = Tender(
        id=uuid4(),
        title="VSGP - Test Tender for E2E",
        organization="Établissement Public Territorial Test",
        reference_number="TEST-001",
        deadline=datetime(2025, 12, 31),
        status="new",
        source="test"
    )
    db_session.add(tender)
    db_session.commit()
    db_session.refresh(tender)

    yield tender

    # Cleanup (cascade will delete related records)
    db_session.delete(tender)
    db_session.commit()


@pytest.fixture
def sample_tender_with_documents(db_session, sample_tender):
    """
    Create a tender with uploaded documents.
    """
    from app.models.tender_document import TenderDocument
    from uuid import uuid4

    documents = [
        TenderDocument(
            id=uuid4(),
            tender_id=sample_tender.id,
            filename="CCTP_test.pdf",
            file_path="/tmp/test/CCTP_test.pdf",
            document_type="CCTP",
            extraction_status="completed"
        ),
        TenderDocument(
            id=uuid4(),
            tender_id=sample_tender.id,
            filename="RC_test.pdf",
            file_path="/tmp/test/RC_test.pdf",
            document_type="RC",
            extraction_status="completed"
        )
    ]

    for doc in documents:
        db_session.add(doc)

    db_session.commit()

    yield sample_tender, documents


# ==================== Section Fixtures ====================

@pytest.fixture
def sample_sections():
    """
    Sample sections data for testing (without DB).
    """
    return [
        {
            "section_number": "1",
            "title": "Durée du marché",
            "content": "Le marché est conclu pour une durée initiale de 4 ans à compter de la notification. Il peut être renouvelé 2 fois par période de 1 an.",
            "page": 1,
            "level": 1,
            "is_key_section": True,
            "is_toc": False
        },
        {
            "section_number": "2",
            "title": "Prestations demandées",
            "content": "Les prestations comprennent l'infogérance complète de l'infrastructure informatique, incluant la supervision 24/7, la maintenance préventive et corrective.",
            "page": 2,
            "level": 1,
            "is_key_section": True,
            "is_toc": False
        },
        {
            "section_number": "2.1",
            "title": "Supervision",
            "content": "La supervision doit être assurée 24 heures sur 24, 7 jours sur 7.",
            "page": 2,
            "level": 2,
            "is_key_section": False,
            "is_toc": False
        }
    ]


@pytest.fixture
def sample_document_sections(db_session, sample_tender_with_documents):
    """
    Create sample DocumentSection records in database.
    """
    from app.models.document_section import DocumentSection
    from uuid import uuid4

    tender, documents = sample_tender_with_documents
    doc = documents[0]  # Use first document

    sections = [
        DocumentSection(
            id=uuid4(),
            document_id=doc.id,
            section_type="HEADING",
            section_number="1",
            title="Durée du marché",
            content="Le marché est conclu pour 4 ans...",
            page=1,
            level=1,
            is_key_section=True,
            is_toc=False
        ),
        DocumentSection(
            id=uuid4(),
            document_id=doc.id,
            section_type="HEADING",
            section_number="2",
            title="Prestations demandées",
            content="Les prestations comprennent...",
            page=2,
            level=1,
            is_key_section=True,
            is_toc=False
        )
    ]

    for section in sections:
        db_session.add(section)

    db_session.commit()

    yield sections


# ==================== Service Fixtures ====================

@pytest.fixture
def llm_service():
    """
    LLM Service instance for testing.
    """
    from app.services.llm_service import llm_service
    return llm_service


@pytest.fixture
def rag_service():
    """
    RAG Service instance for testing.
    """
    from app.services.rag_service import rag_service
    return rag_service


@pytest.fixture
def parser_service():
    """
    Parser Service instance for testing.
    """
    from app.services.parser_service import parser_service
    return parser_service


# ==================== Mock Fixtures ====================

@pytest.fixture
def mock_claude_response():
    """
    Mock Claude API response for testing without API calls.
    """
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": """## Résumé
Appel d'offres pour infogérance infrastructure IT.

## Exigences principales
- Durée: 4 ans renouvelable 2x1 an
- Supervision 24/7
- Maintenance préventive et corrective

## Risques identifiés
- Complexité technique élevée
- Délais de réponse serrés
"""
            }
        ],
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 200
        }
    }


@pytest.fixture
def mock_openai_embedding():
    """
    Mock OpenAI embedding response.
    """
    import random
    return [random.random() for _ in range(1536)]


# ==================== PDF Fixtures ====================

@pytest.fixture
def sample_pdf_path():
    """
    Path to sample PDF for testing (if available).
    """
    base_path = Path(__file__).parent.parent.parent  # Project root
    pdf_path = base_path / "Examples" / "VSGP-AO" / "CCTP.pdf"

    if pdf_path.exists():
        return str(pdf_path)
    else:
        pytest.skip(f"Sample PDF not found: {pdf_path}")


# ==================== Pytest Configuration ====================

def pytest_configure(config):
    """
    Register custom markers.
    """
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full pipeline)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (with external APIs)"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests (isolated components)"
    )
    config.addinivalue_line(
        "markers", "quality: Quality validation tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (> 5 seconds)"
    )
    config.addinivalue_line(
        "markers", "rag: RAG Service specific tests"
    )
