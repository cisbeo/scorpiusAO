# 📋 Plan d'Implémentation Détaillé - Solution 1: Tables Séparées

**Issue**: [GitHub #2 - RAG Knowledge Base](https://github.com/cisbeo/scorpiusAO/issues/2)
**Solution**: Tables Séparées (`historical_tenders` + `past_proposals`)
**Sprint**: Sprint 2 (10 jours ouvrés)
**Effort estimé**: 7 jours
**Date début**: À définir
**Assigné**: Équipe Backend

---

## 📊 Vue d'Ensemble

### Objectifs
1. ✅ Créer modèles SQLAlchemy pour `HistoricalTender` et `PastProposal`
2. ✅ Implémenter migration Alembic (CREATE TABLE)
3. ✅ Développer script d'archivage automatique
4. ✅ Adapter RAG Service pour ingestion past_proposals
5. ✅ Intégrer Knowledge Base dans génération de réponses
6. ✅ Tests E2E complets

### Architecture Cible

```
┌─────────────────────────────────────────────────────────────┐
│                     ACTIVE WORKFLOW                         │
│                                                             │
│  User Upload PDF → Tender → TenderDocument → Processing    │
│                      ↓                                       │
│                  Proposal (draft/submitted)                 │
│                      ↓                                       │
│              DocumentSection → Embeddings                   │
│                   (document_type="tender")                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   [ARCHIVAGE - Manual/Auto]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   HISTORICAL WORKFLOW                       │
│                                                             │
│  Tender + Proposal  →  HistoricalTender + PastProposal     │
│                              ↓                               │
│                    RAG Ingestion (batch)                    │
│                   (document_type="past_proposal")           │
│                              ↓                               │
│              Knowledge Base Retrieval (Sprint 2)            │
│                              ↓                               │
│           Response Generation (enriched context)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗓️ Timeline Détaillé (7 jours)

| Jour | Phase | Tâches | Livrables | Status |
|------|-------|--------|-----------|--------|
| **J1** | Phase 1.1 | Modèles SQLAlchemy | `historical_tender.py`, `past_proposal.py` | ⏳ |
| **J2** | Phase 1.2 | Migration Alembic + Tests | Migration file, tests unitaires | ⏳ |
| **J3** | Phase 2.1 | Script archivage | `archive_tender.py`, endpoint API | ⏳ |
| **J4** | Phase 2.2 | Tests E2E archivage | Tests pipeline archivage | ⏳ |
| **J5** | Phase 3.1 | RAG ingestion KB | Adaptation `rag_service.py` | ⏳ |
| **J6** | Phase 3.2 | Batch ingestion | Script batch, tests RAG | ⏳ |
| **J7** | Phase 4 | Integration LLM | `llm_service.py` enrichi, tests | ⏳ |

---

## 📦 Phase 1: Modèles et Migration (J1-J2)

### 🎯 Objectif
Créer les modèles SQLAlchemy `HistoricalTender` et `PastProposal` avec migration Alembic et tests unitaires.

---

### Jour 1: Modèles SQLAlchemy

#### Tâche 1.1: Créer `app/models/historical_tender.py`

**Fichier**: `backend/app/models/historical_tender.py`

```python
"""
SQLAlchemy model for Historical Tenders.

A HistoricalTender represents an archived tender (appel d'offre) that has been
completed and awarded. It stores metadata about the tender and links to our
past proposal(s) for that tender.

Relationship: One HistoricalTender → Many PastProposals
(One tender can have multiple proposals from different companies,
but we only store OUR company's proposal(s))
"""
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import Column, String, Text, Date, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class HistoricalTender(Base):
    """
    Historical Tender model for archived tenders.

    Stores tenders that have been completed, evaluated, and awarded.
    Used for RAG Knowledge Base to retrieve similar past tenders
    and winning proposal patterns.
    """

    __tablename__ = "historical_tenders"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for historical tender"
    )

    # Tender Information (from original Tender model)
    title = Column(
        String(500),
        nullable=False,
        index=True,
        comment="Title of the tender (e.g., 'Infogérance infrastructure IT')"
    )

    organization = Column(
        String(200),
        index=True,
        comment="Organization that published the tender (e.g., 'Vallée Sud Grand Paris')"
    )

    reference_number = Column(
        String(100),
        unique=True,
        index=True,
        comment="Official tender reference number (e.g., '25TIC06')"
    )

    # Dates
    publication_date = Column(
        Date,
        comment="Date when tender was published on BOAMP/AWS PLACE"
    )

    deadline = Column(
        Date,
        comment="Deadline for proposal submission"
    )

    award_date = Column(
        Date,
        index=True,
        comment="Date when tender was awarded to winner"
    )

    # Award Information
    total_amount = Column(
        Numeric(12, 2),
        comment="Total contract amount in EUR (e.g., 500000.00 for 500k€)"
    )

    winner_company = Column(
        String(200),
        comment="Name of company that won the tender (if not us)"
    )

    status = Column(
        String(50),
        default="awarded",
        index=True,
        comment="Status: 'awarded', 'cancelled', 'deserted'"
    )

    # Archive Information
    archived_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when tender was archived"
    )

    archived_by = Column(
        UUID(as_uuid=True),
        comment="User ID who archived this tender"
    )

    # Metadata (stores original tender data)
    metadata = Column(
        JSON,
        default={},
        comment="Stores original_tender_id, raw_content, parsed_content, etc."
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    past_proposals = relationship(
        "PastProposal",
        back_populates="historical_tender",
        cascade="all, delete-orphan",
        lazy="selectin"  # Eager load proposals when querying tenders
    )

    def __repr__(self):
        return f"<HistoricalTender {self.reference_number}: {self.title[:50]}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "title": self.title,
            "organization": self.organization,
            "reference_number": self.reference_number,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "award_date": self.award_date.isoformat() if self.award_date else None,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "winner_company": self.winner_company,
            "status": self.status,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "past_proposals_count": len(self.past_proposals) if self.past_proposals else 0
        }
```

---

#### Tâche 1.2: Créer `app/models/past_proposal.py`

**Fichier**: `backend/app/models/past_proposal.py`

```python
"""
SQLAlchemy model for Past Proposals.

A PastProposal represents our company's submitted proposal for a historical tender.
It stores the proposal content, our score, rank, and lessons learned for future
use in RAG Knowledge Base.

Relationship: Many PastProposals → One HistoricalTender
"""
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import Column, String, Text, Integer, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import relationship

from app.models.base import Base


class PastProposal(Base):
    """
    Past Proposal model for archived winning/losing proposals.

    Stores our company's proposal for a historical tender.
    Used for RAG Knowledge Base to retrieve winning proposal sections
    and generate similar responses for new tenders.
    """

    __tablename__ = "past_proposals"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for past proposal"
    )

    # Foreign Key to HistoricalTender
    historical_tender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the historical tender"
    )

    # Company Information (for multi-tenancy support)
    our_company_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Our company ID (for multi-tenancy if needed)"
    )

    our_company_name = Column(
        String(200),
        default="ScorpiusAO Client",
        comment="Our company name at time of proposal"
    )

    # Proposal Status
    status = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Status: 'won', 'lost', 'shortlisted', 'withdrawn'"
    )

    # Scores and Ranking
    score_obtained = Column(
        Numeric(5, 2),
        comment="Final score obtained (e.g., 85.50 out of 100)"
    )

    max_score = Column(
        Numeric(5, 2),
        default=Decimal("100.00"),
        comment="Maximum possible score (usually 100.00)"
    )

    rank = Column(
        Integer,
        comment="Rank among all bidders (1 = winner, 2 = runner-up, etc.)"
    )

    total_bidders = Column(
        Integer,
        comment="Total number of bidders for this tender"
    )

    # Proposal Content (from original Proposal model)
    sections = Column(
        JSON,
        nullable=False,
        default={},
        comment="Complete proposal sections (same structure as Proposal.sections)"
    )

    # Post-Mortem Analysis (manually filled by bid manager)
    lessons_learned = Column(
        Text,
        comment="Lessons learned from this proposal (what worked, what didn't)"
    )

    win_factors = Column(
        ARRAY(String),
        default=[],
        comment="Key factors that contributed to win/loss (e.g., ['price_competitive', 'strong_references', 'weak_technical_memo'])"
    )

    improvement_areas = Column(
        ARRAY(String),
        default=[],
        comment="Areas for improvement identified in post-mortem"
    )

    # Financial Information
    proposed_amount = Column(
        Numeric(12, 2),
        comment="Total amount proposed in our bid (EUR)"
    )

    winning_amount = Column(
        Numeric(12, 2),
        comment="Winning bid amount (if we lost, to track competition)"
    )

    # Metadata
    metadata = Column(
        JSON,
        default={},
        comment="Stores original_proposal_id, evaluator_comments, etc."
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    historical_tender = relationship(
        "HistoricalTender",
        back_populates="past_proposals"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            'historical_tender_id',
            'our_company_id',
            name='uq_past_proposal_tender_company'
        ),
    )

    def __repr__(self):
        return f"<PastProposal {self.status} for HistoricalTender {self.historical_tender_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "historical_tender_id": str(self.historical_tender_id),
            "our_company_id": str(self.our_company_id),
            "our_company_name": self.our_company_name,
            "status": self.status,
            "score_obtained": float(self.score_obtained) if self.score_obtained else None,
            "max_score": float(self.max_score) if self.max_score else None,
            "rank": self.rank,
            "total_bidders": self.total_bidders,
            "lessons_learned": self.lessons_learned,
            "win_factors": self.win_factors,
            "improvement_areas": self.improvement_areas,
            "proposed_amount": float(self.proposed_amount) if self.proposed_amount else None,
            "winning_amount": float(self.winning_amount) if self.winning_amount else None,
            "sections_count": len(self.sections) if self.sections else 0,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @property
    def win_rate_percentage(self):
        """Calculate win rate percentage (for display)."""
        if not self.score_obtained or not self.max_score:
            return None
        return float((self.score_obtained / self.max_score) * 100)

    @property
    def is_winning_proposal(self):
        """Check if this was a winning proposal."""
        return self.status == "won" or self.rank == 1
```

---

#### Tâche 1.3: Mettre à jour `app/models/__init__.py`

**Fichier**: `backend/app/models/__init__.py`

```python
"""
SQLAlchemy models for ScorpiusAO.
"""
from app.models.base import Base
from app.models.tender import Tender, TenderCriterion
from app.models.proposal import Proposal
from app.models.document import Document
from app.models.tender_document import TenderDocument
from app.models.document_section import DocumentSection
from app.models.tender_analysis import TenderAnalysis
from app.models.criterion_suggestion import CriterionSuggestion
from app.models.similar_tender import SimilarTender

# NEW: Historical models for RAG Knowledge Base
from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal


__all__ = [
    "Base",
    "Tender",
    "TenderCriterion",
    "Proposal",
    "Document",
    "TenderDocument",
    "DocumentSection",
    "TenderAnalysis",
    "CriterionSuggestion",
    "SimilarTender",
    # Historical models
    "HistoricalTender",
    "PastProposal",
]
```

---

### Jour 2: Migration Alembic et Tests

#### Tâche 2.1: Créer migration Alembic

**Commande**:
```bash
cd backend
alembic revision --autogenerate -m "Add historical_tenders and past_proposals tables for RAG Knowledge Base"
```

**Fichier généré**: `backend/alembic/versions/XXXXX_add_historical_models.py`

**Contenu manuel (après autogenerate)**:

```python
"""Add historical_tenders and past_proposals tables for RAG Knowledge Base

Revision ID: XXXXX
Revises: YYYYY
Create Date: 2025-10-03 XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'XXXXX'
down_revision = 'YYYYY'
branch_labels = None
depends_on = None


def upgrade():
    # Create historical_tenders table
    op.create_table(
        'historical_tenders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('organization', sa.String(length=200), nullable=True),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('award_date', sa.Date(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('winner_company', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_historical_tenders_title', 'historical_tenders', ['title'])
    op.create_index('idx_historical_tenders_org', 'historical_tenders', ['organization'])
    op.create_index('idx_historical_tenders_ref', 'historical_tenders', ['reference_number'], unique=True)
    op.create_index('idx_historical_tenders_award', 'historical_tenders', ['award_date'])
    op.create_index('idx_historical_tenders_status', 'historical_tenders', ['status'])
    op.create_index('idx_historical_tenders_archived', 'historical_tenders', ['archived_at'])

    # Create past_proposals table
    op.create_table(
        'past_proposals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('historical_tender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('our_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('our_company_name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('score_obtained', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('max_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('total_bidders', sa.Integer(), nullable=True),
        sa.Column('sections', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('win_factors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('improvement_areas', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('proposed_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('winning_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['historical_tender_id'], ['historical_tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('historical_tender_id', 'our_company_id', name='uq_past_proposal_tender_company')
    )
    op.create_index('idx_past_proposals_tender', 'past_proposals', ['historical_tender_id'])
    op.create_index('idx_past_proposals_company', 'past_proposals', ['our_company_id'])
    op.create_index('idx_past_proposals_status', 'past_proposals', ['status'])


def downgrade():
    op.drop_table('past_proposals')
    op.drop_table('historical_tenders')
```

**Appliquer la migration**:
```bash
alembic upgrade head
```

---

#### Tâche 2.2: Tests unitaires modèles

**Fichier**: `backend/tests/test_historical_models.py`

```python
"""
Unit tests for HistoricalTender and PastProposal models.
"""
import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal


@pytest.fixture(scope="module")
def test_db():
    """Create test database session."""
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.mark.unit
def test_create_historical_tender(test_db):
    """Test creating a HistoricalTender."""
    tender = HistoricalTender(
        title="Test Tender - Infogérance Infrastructure",
        organization="Test Organization",
        reference_number="TEST-2025-001",
        publication_date=date(2025, 1, 1),
        deadline=date(2025, 2, 1),
        award_date=date(2025, 3, 1),
        total_amount=Decimal("500000.00"),
        status="awarded",
        metadata={"test": "data"}
    )

    test_db.add(tender)
    test_db.commit()
    test_db.refresh(tender)

    assert tender.id is not None
    assert tender.title == "Test Tender - Infogérance Infrastructure"
    assert tender.reference_number == "TEST-2025-001"
    assert tender.total_amount == Decimal("500000.00")
    assert tender.status == "awarded"
    assert tender.created_at is not None

    # Cleanup
    test_db.delete(tender)
    test_db.commit()


@pytest.mark.unit
def test_create_past_proposal(test_db):
    """Test creating a PastProposal linked to HistoricalTender."""
    # Create historical tender first
    tender = HistoricalTender(
        title="Test Tender for Proposal",
        reference_number="TEST-2025-002",
        status="awarded"
    )
    test_db.add(tender)
    test_db.commit()
    test_db.refresh(tender)

    # Create past proposal
    company_id = uuid4()
    proposal = PastProposal(
        historical_tender_id=tender.id,
        our_company_id=company_id,
        our_company_name="ScorpiusAO Test Client",
        status="won",
        score_obtained=Decimal("85.50"),
        max_score=Decimal("100.00"),
        rank=1,
        total_bidders=5,
        sections={"section1": "content1"},
        win_factors=["price_competitive", "strong_references"],
        proposed_amount=Decimal("480000.00")
    )

    test_db.add(proposal)
    test_db.commit()
    test_db.refresh(proposal)

    assert proposal.id is not None
    assert proposal.historical_tender_id == tender.id
    assert proposal.status == "won"
    assert proposal.score_obtained == Decimal("85.50")
    assert proposal.rank == 1
    assert proposal.win_factors == ["price_competitive", "strong_references"]
    assert proposal.is_winning_proposal is True
    assert proposal.win_rate_percentage == 85.5

    # Cleanup
    test_db.delete(proposal)
    test_db.delete(tender)
    test_db.commit()


@pytest.mark.unit
def test_relationship_tender_proposals(test_db):
    """Test One-to-Many relationship between HistoricalTender and PastProposals."""
    # Create tender
    tender = HistoricalTender(
        title="Test Tender - Multiple Proposals",
        reference_number="TEST-2025-003",
        status="awarded"
    )
    test_db.add(tender)
    test_db.commit()
    test_db.refresh(tender)

    # Create 2 proposals (different companies - should work)
    company1_id = uuid4()
    company2_id = uuid4()

    proposal1 = PastProposal(
        historical_tender_id=tender.id,
        our_company_id=company1_id,
        status="won",
        sections={"section1": "content1"}
    )

    proposal2 = PastProposal(
        historical_tender_id=tender.id,
        our_company_id=company2_id,
        status="lost",
        sections={"section1": "content1"}
    )

    test_db.add(proposal1)
    test_db.add(proposal2)
    test_db.commit()

    # Refresh tender to load relationships
    test_db.refresh(tender)

    assert len(tender.past_proposals) == 2
    assert proposal1 in tender.past_proposals
    assert proposal2 in tender.past_proposals

    # Cleanup
    test_db.delete(proposal1)
    test_db.delete(proposal2)
    test_db.delete(tender)
    test_db.commit()


@pytest.mark.unit
def test_unique_constraint_proposal_per_company(test_db):
    """Test that UniqueConstraint prevents duplicate proposals from same company."""
    # Create tender
    tender = HistoricalTender(
        title="Test Tender - Unique Constraint",
        reference_number="TEST-2025-004",
        status="awarded"
    )
    test_db.add(tender)
    test_db.commit()
    test_db.refresh(tender)

    company_id = uuid4()

    # First proposal
    proposal1 = PastProposal(
        historical_tender_id=tender.id,
        our_company_id=company_id,
        status="won",
        sections={"section1": "content1"}
    )
    test_db.add(proposal1)
    test_db.commit()

    # Second proposal (same tender, same company - should fail)
    proposal2 = PastProposal(
        historical_tender_id=tender.id,
        our_company_id=company_id,
        status="won",
        sections={"section1": "content1"}
    )

    with pytest.raises(IntegrityError):
        test_db.add(proposal2)
        test_db.commit()

    test_db.rollback()

    # Cleanup
    test_db.delete(proposal1)
    test_db.delete(tender)
    test_db.commit()


@pytest.mark.unit
def test_cascade_delete(test_db):
    """Test that deleting HistoricalTender cascades to PastProposals."""
    # Create tender
    tender = HistoricalTender(
        title="Test Tender - Cascade Delete",
        reference_number="TEST-2025-005",
        status="awarded"
    )
    test_db.add(tender)
    test_db.commit()
    test_db.refresh(tender)

    # Create proposal
    proposal = PastProposal(
        historical_tender_id=tender.id,
        our_company_id=uuid4(),
        status="won",
        sections={"section1": "content1"}
    )
    test_db.add(proposal)
    test_db.commit()

    proposal_id = proposal.id

    # Delete tender (should cascade to proposal)
    test_db.delete(tender)
    test_db.commit()

    # Verify proposal was deleted
    deleted_proposal = test_db.query(PastProposal).filter(
        PastProposal.id == proposal_id
    ).first()

    assert deleted_proposal is None


@pytest.mark.unit
def test_to_dict_serialization(test_db):
    """Test to_dict() serialization for API responses."""
    tender = HistoricalTender(
        title="Test Tender - Serialization",
        reference_number="TEST-2025-006",
        organization="Test Org",
        total_amount=Decimal("300000.00"),
        status="awarded",
        publication_date=date(2025, 1, 1)
    )
    test_db.add(tender)
    test_db.commit()
    test_db.refresh(tender)

    tender_dict = tender.to_dict()

    assert tender_dict["title"] == "Test Tender - Serialization"
    assert tender_dict["reference_number"] == "TEST-2025-006"
    assert tender_dict["total_amount"] == 300000.00
    assert tender_dict["status"] == "awarded"
    assert tender_dict["publication_date"] == "2025-01-01"
    assert "created_at" in tender_dict

    # Cleanup
    test_db.delete(tender)
    test_db.commit()
```

**Lancer les tests**:
```bash
pytest tests/test_historical_models.py -v
```

---

### 📋 Checklist Phase 1 (J1-J2)

- [ ] Créer `app/models/historical_tender.py` (HistoricalTender model)
- [ ] Créer `app/models/past_proposal.py` (PastProposal model)
- [ ] Mettre à jour `app/models/__init__.py` (imports)
- [ ] Créer migration Alembic `add_historical_models`
- [ ] Appliquer migration `alembic upgrade head`
- [ ] Créer `tests/test_historical_models.py` (6 tests unitaires)
- [ ] Valider tous tests passent (pytest -v)
- [ ] Commit Git: "feat: Add HistoricalTender and PastProposal models for RAG KB (Issue #2)"

---

## 📦 Phase 2: Script d'Archivage (J3-J4)

### 🎯 Objectif
Développer un script et un endpoint API pour archiver un tender actif + proposal vers l'historique.

---

### Jour 3: Script d'archivage

#### Tâche 3.1: Créer service d'archivage

**Fichier**: `backend/app/services/archive_service.py`

```python
"""
Archive Service - Migrate active tenders/proposals to historical tables.

This service handles the archiving workflow:
1. Copy Tender → HistoricalTender
2. Copy Proposal → PastProposal
3. Create embeddings for RAG Knowledge Base
4. Optionally delete original tender/proposal
"""
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.models.proposal import Proposal
from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal
from app.services.rag_service import rag_service
from app.core.config import settings


class ArchiveService:
    """Service for archiving tenders and proposals."""

    def archive_tender(
        self,
        db: Session,
        tender_id: UUID,
        proposal_id: UUID,
        proposal_status: str = "won",
        score_obtained: Optional[Decimal] = None,
        rank: Optional[int] = None,
        total_bidders: Optional[int] = None,
        lessons_learned: Optional[str] = None,
        win_factors: Optional[list] = None,
        improvement_areas: Optional[list] = None,
        archived_by: Optional[UUID] = None,
        delete_original: bool = False,
        create_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Archive a tender and proposal to historical tables.

        Args:
            db: Database session
            tender_id: UUID of tender to archive
            proposal_id: UUID of proposal to archive
            proposal_status: 'won', 'lost', 'shortlisted', 'withdrawn'
            score_obtained: Final score (e.g., 85.50)
            rank: Rank among bidders (1 = winner)
            total_bidders: Total number of bidders
            lessons_learned: Post-mortem analysis text
            win_factors: List of success factors
            improvement_areas: List of areas to improve
            archived_by: User ID who initiated archiving
            delete_original: If True, delete original tender/proposal after archiving
            create_embeddings: If True, create RAG embeddings for past_proposal

        Returns:
            Dict with historical_tender_id, past_proposal_id, embeddings_created

        Raises:
            ValueError: If tender or proposal not found
        """
        # 1. Fetch original tender and proposal
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        if proposal.tender_id != tender.id:
            raise ValueError(f"Proposal {proposal_id} does not belong to Tender {tender_id}")

        # 2. Create HistoricalTender
        historical_tender = HistoricalTender(
            id=uuid4(),
            title=tender.title,
            organization=tender.organization,
            reference_number=tender.reference_number,
            publication_date=tender.created_at.date() if tender.created_at else date.today(),
            deadline=tender.deadline.date() if tender.deadline else None,
            award_date=date.today(),
            status="awarded",
            archived_at=datetime.utcnow(),
            archived_by=archived_by,
            metadata={
                "original_tender_id": str(tender.id),
                "raw_content": tender.raw_content,
                "parsed_content": tender.parsed_content,
                "source": tender.source
            }
        )

        db.add(historical_tender)
        db.flush()  # Get historical_tender.id

        # 3. Create PastProposal
        past_proposal = PastProposal(
            id=uuid4(),
            historical_tender_id=historical_tender.id,
            our_company_id=proposal.user_id,  # Assuming user_id is company_id
            our_company_name=settings.company_name if hasattr(settings, 'company_name') else "ScorpiusAO Client",
            status=proposal_status,
            score_obtained=score_obtained,
            max_score=Decimal("100.00"),
            rank=rank,
            total_bidders=total_bidders,
            sections=proposal.sections,
            lessons_learned=lessons_learned or "",
            win_factors=win_factors or [],
            improvement_areas=improvement_areas or [],
            metadata={
                "original_proposal_id": str(proposal.id),
                "compliance_score": proposal.compliance_score,
                "version": proposal.version
            }
        )

        db.add(past_proposal)
        db.commit()
        db.refresh(historical_tender)
        db.refresh(past_proposal)

        # 4. Create RAG embeddings (if requested)
        embeddings_created = 0
        if create_embeddings and proposal.sections:
            try:
                # Convert sections to format expected by RAG service
                sections_list = []
                for section_num, section_data in proposal.sections.items():
                    sections_list.append({
                        "section_number": section_num,
                        "title": section_data.get("title", ""),
                        "content": section_data.get("content", ""),
                        "page": section_data.get("page", 1),
                        "is_key_section": True,  # All proposal sections are key
                        "is_toc": False,
                        "level": section_data.get("level", 1)
                    })

                # Chunk sections
                chunks = rag_service.chunk_sections_semantic(
                    sections=sections_list,
                    max_tokens=1000,
                    min_tokens=100
                )

                # Ingest into RAG
                embeddings_created = rag_service.ingest_document_sync(
                    db=db,
                    document_id=str(past_proposal.id),
                    chunks=chunks,
                    document_type="past_proposal",
                    metadata={
                        "historical_tender_id": str(historical_tender.id),
                        "tender_title": historical_tender.title,
                        "organization": historical_tender.organization,
                        "reference_number": historical_tender.reference_number,
                        "status": past_proposal.status,
                        "score": float(past_proposal.score_obtained) if past_proposal.score_obtained else None,
                        "rank": past_proposal.rank,
                        "win_factors": past_proposal.win_factors,
                        "is_winning": past_proposal.is_winning_proposal
                    }
                )

            except Exception as e:
                # Log error but don't fail archiving
                print(f"⚠️  Failed to create embeddings for PastProposal {past_proposal.id}: {e}")

        # 5. Optionally delete original tender/proposal
        if delete_original:
            db.delete(proposal)
            db.delete(tender)
            db.commit()

        return {
            "historical_tender_id": str(historical_tender.id),
            "past_proposal_id": str(past_proposal.id),
            "embeddings_created": embeddings_created,
            "original_deleted": delete_original
        }


# Singleton instance
archive_service = ArchiveService()
```

---

#### Tâche 3.2: Créer endpoint API

**Fichier**: `backend/app/api/v1/endpoints/archive.py`

```python
"""
Archive endpoints - Archive tenders and proposals to historical tables.
"""
from typing import Optional
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.dependencies import get_db
from app.services.archive_service import archive_service


router = APIRouter()


class ArchiveTenderRequest(BaseModel):
    """Request schema for archiving a tender."""
    proposal_id: UUID = Field(..., description="UUID of proposal to archive")
    proposal_status: str = Field("won", description="Status: won, lost, shortlisted, withdrawn")
    score_obtained: Optional[Decimal] = Field(None, description="Final score obtained (e.g., 85.50)")
    rank: Optional[int] = Field(None, description="Rank among bidders (1 = winner)")
    total_bidders: Optional[int] = Field(None, description="Total number of bidders")
    lessons_learned: Optional[str] = Field(None, description="Post-mortem analysis")
    win_factors: Optional[list] = Field(None, description="Key success factors")
    improvement_areas: Optional[list] = Field(None, description="Areas for improvement")
    delete_original: bool = Field(False, description="Delete original tender/proposal after archiving")
    create_embeddings: bool = Field(True, description="Create RAG embeddings")


class ArchiveTenderResponse(BaseModel):
    """Response schema for archive operation."""
    success: bool
    historical_tender_id: str
    past_proposal_id: str
    embeddings_created: int
    original_deleted: bool
    message: str


@router.post(
    "/tenders/{tender_id}/archive",
    response_model=ArchiveTenderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Archive a tender to historical tables",
    description="Archive a completed tender and its proposal to historical_tenders and past_proposals tables. Optionally creates RAG embeddings for Knowledge Base."
)
async def archive_tender(
    tender_id: UUID,
    request: ArchiveTenderRequest,
    db: Session = Depends(get_db)
):
    """
    Archive a tender and proposal to historical tables.

    **Workflow**:
    1. Copy Tender → HistoricalTender
    2. Copy Proposal → PastProposal
    3. Create RAG embeddings (if requested)
    4. Optionally delete original tender/proposal

    **Use Cases**:
    - Won tender: `proposal_status="won"`, `rank=1`
    - Lost tender: `proposal_status="lost"`, `rank=2+`
    - Withdrawn: `proposal_status="withdrawn"`

    **Example**:
    ```json
    {
        "proposal_id": "123e4567-e89b-12d3-a456-426614174000",
        "proposal_status": "won",
        "score_obtained": 85.50,
        "rank": 1,
        "total_bidders": 5,
        "lessons_learned": "Strong technical memo, competitive pricing",
        "win_factors": ["price_competitive", "strong_references", "good_presentation"],
        "delete_original": false,
        "create_embeddings": true
    }
    ```
    """
    try:
        result = archive_service.archive_tender(
            db=db,
            tender_id=tender_id,
            proposal_id=request.proposal_id,
            proposal_status=request.proposal_status,
            score_obtained=request.score_obtained,
            rank=request.rank,
            total_bidders=request.total_bidders,
            lessons_learned=request.lessons_learned,
            win_factors=request.win_factors,
            improvement_areas=request.improvement_areas,
            delete_original=request.delete_original,
            create_embeddings=request.create_embeddings
        )

        return ArchiveTenderResponse(
            success=True,
            historical_tender_id=result["historical_tender_id"],
            past_proposal_id=result["past_proposal_id"],
            embeddings_created=result["embeddings_created"],
            original_deleted=result["original_deleted"],
            message=f"Tender archived successfully. Created {result['embeddings_created']} embeddings."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive tender: {str(e)}"
        )
```

---

#### Tâche 3.3: Enregistrer router dans API

**Fichier**: `backend/app/api/v1/api.py`

```python
# ... existing imports ...
from app.api.v1.endpoints import archive  # NEW

api_router = APIRouter()

# ... existing routers ...

# NEW: Archive router
api_router.include_router(
    archive.router,
    prefix="/archive",
    tags=["archive"]
)
```

---

### Jour 4: Tests E2E archivage

#### Tâche 4.1: Test E2E archive workflow

**Fichier**: `backend/tests/test_archive_e2e.py`

```python
"""
E2E tests for archive workflow (Tender → HistoricalTender + PastProposal).
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

from app.models.tender import Tender
from app.models.proposal import Proposal
from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal
from app.services.archive_service import archive_service


@pytest.fixture
def sample_active_tender_and_proposal(db_session):
    """Create a sample active tender + proposal for archiving."""
    # Create tender
    tender = Tender(
        id=uuid4(),
        title="VSGP - Test Archivage",
        organization="Établissement Public Test",
        reference_number="TEST-ARCHIVE-001",
        deadline=datetime(2025, 4, 15),
        status="awarded",
        source="manual_upload",
        raw_content="Sample content",
        parsed_content={"test": "data"}
    )
    db_session.add(tender)
    db_session.flush()

    # Create proposal
    proposal = Proposal(
        id=uuid4(),
        tender_id=tender.id,
        user_id=uuid4(),
        sections={
            "1": {
                "title": "Contexte et périmètre",
                "content": "Notre entreprise propose une solution complète d'infogérance...",
                "page": 1,
                "level": 1
            },
            "2": {
                "title": "Méthodologie",
                "content": "Nous utilisons la méthode Agile avec ITIL v4...",
                "page": 2,
                "level": 1
            }
        },
        compliance_score="85.5",
        status="submitted",
        version=1
    )
    db_session.add(proposal)
    db_session.commit()
    db_session.refresh(tender)
    db_session.refresh(proposal)

    yield tender, proposal

    # Cleanup
    db_session.query(PastProposal).filter(
        PastProposal.metadata["original_proposal_id"].astext == str(proposal.id)
    ).delete(synchronize_session=False)

    db_session.query(HistoricalTender).filter(
        HistoricalTender.metadata["original_tender_id"].astext == str(tender.id)
    ).delete(synchronize_session=False)

    db_session.commit()


@pytest.mark.e2e
@pytest.mark.slow
def test_archive_tender_basic(db_session, sample_active_tender_and_proposal):
    """Test 1: Basic archiving workflow."""
    tender, proposal = sample_active_tender_and_proposal

    result = archive_service.archive_tender(
        db=db_session,
        tender_id=tender.id,
        proposal_id=proposal.id,
        proposal_status="won",
        score_obtained=Decimal("85.50"),
        rank=1,
        total_bidders=5,
        delete_original=False,
        create_embeddings=False  # Skip embeddings for basic test
    )

    assert result["historical_tender_id"] is not None
    assert result["past_proposal_id"] is not None
    assert result["original_deleted"] is False

    # Verify HistoricalTender created
    historical_tender = db_session.query(HistoricalTender).filter(
        HistoricalTender.id == result["historical_tender_id"]
    ).first()

    assert historical_tender is not None
    assert historical_tender.title == tender.title
    assert historical_tender.reference_number == tender.reference_number
    assert historical_tender.metadata["original_tender_id"] == str(tender.id)

    # Verify PastProposal created
    past_proposal = db_session.query(PastProposal).filter(
        PastProposal.id == result["past_proposal_id"]
    ).first()

    assert past_proposal is not None
    assert past_proposal.historical_tender_id == historical_tender.id
    assert past_proposal.status == "won"
    assert past_proposal.score_obtained == Decimal("85.50")
    assert past_proposal.rank == 1
    assert past_proposal.sections == proposal.sections


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.rag
def test_archive_tender_with_embeddings(db_session, sample_active_tender_and_proposal):
    """Test 2: Archiving with RAG embeddings creation."""
    tender, proposal = sample_active_tender_and_proposal

    result = archive_service.archive_tender(
        db=db_session,
        tender_id=tender.id,
        proposal_id=proposal.id,
        proposal_status="won",
        score_obtained=Decimal("90.00"),
        rank=1,
        win_factors=["price_competitive", "strong_references"],
        delete_original=False,
        create_embeddings=True  # Create RAG embeddings
    )

    assert result["embeddings_created"] > 0, "Should create at least 1 embedding"

    # Verify embeddings exist in document_embeddings table
    embeddings_count = db_session.execute(text("""
        SELECT COUNT(*) FROM document_embeddings
        WHERE document_id = :doc_id AND document_type = 'past_proposal'
    """), {"doc_id": result["past_proposal_id"]}).scalar()

    assert embeddings_count == result["embeddings_created"]


@pytest.mark.e2e
def test_archive_tender_with_lessons_learned(db_session, sample_active_tender_and_proposal):
    """Test 3: Archiving with post-mortem analysis."""
    tender, proposal = sample_active_tender_and_proposal

    lessons = "Notre mémo technique était très fort. Pricing compétitif. Présentation orale excellente."
    win_factors = ["strong_technical_memo", "competitive_price", "excellent_presentation"]
    improvement_areas = ["better_time_management", "more_references"]

    result = archive_service.archive_tender(
        db=db_session,
        tender_id=tender.id,
        proposal_id=proposal.id,
        proposal_status="won",
        lessons_learned=lessons,
        win_factors=win_factors,
        improvement_areas=improvement_areas,
        create_embeddings=False
    )

    past_proposal = db_session.query(PastProposal).filter(
        PastProposal.id == result["past_proposal_id"]
    ).first()

    assert past_proposal.lessons_learned == lessons
    assert past_proposal.win_factors == win_factors
    assert past_proposal.improvement_areas == improvement_areas


@pytest.mark.e2e
def test_archive_tender_delete_original(db_session, sample_active_tender_and_proposal):
    """Test 4: Archiving with deletion of original tender/proposal."""
    tender, proposal = sample_active_tender_and_proposal
    tender_id = tender.id
    proposal_id = proposal.id

    result = archive_service.archive_tender(
        db=db_session,
        tender_id=tender_id,
        proposal_id=proposal_id,
        proposal_status="won",
        delete_original=True,  # Delete original
        create_embeddings=False
    )

    assert result["original_deleted"] is True

    # Verify original tender deleted
    original_tender = db_session.query(Tender).filter(Tender.id == tender_id).first()
    assert original_tender is None

    # Verify original proposal deleted
    original_proposal = db_session.query(Proposal).filter(Proposal.id == proposal_id).first()
    assert original_proposal is None

    # Verify historical versions exist
    historical_tender = db_session.query(HistoricalTender).filter(
        HistoricalTender.id == result["historical_tender_id"]
    ).first()
    assert historical_tender is not None


@pytest.mark.e2e
def test_archive_tender_invalid_proposal(db_session, sample_active_tender_and_proposal):
    """Test 5: Error handling - proposal doesn't belong to tender."""
    tender, _ = sample_active_tender_and_proposal

    # Create unrelated proposal
    other_tender = Tender(
        id=uuid4(),
        title="Other Tender",
        reference_number="OTHER-001",
        status="new"
    )
    db_session.add(other_tender)
    db_session.flush()

    other_proposal = Proposal(
        id=uuid4(),
        tender_id=other_tender.id,
        user_id=uuid4(),
        sections={},
        status="draft"
    )
    db_session.add(other_proposal)
    db_session.commit()

    # Try to archive with mismatched proposal
    with pytest.raises(ValueError, match="does not belong to Tender"):
        archive_service.archive_tender(
            db=db_session,
            tender_id=tender.id,
            proposal_id=other_proposal.id,
            proposal_status="won",
            create_embeddings=False
        )

    # Cleanup
    db_session.delete(other_proposal)
    db_session.delete(other_tender)
    db_session.commit()
```

**Lancer les tests**:
```bash
pytest tests/test_archive_e2e.py -v -s
```

---

### 📋 Checklist Phase 2 (J3-J4)

- [ ] Créer `app/services/archive_service.py` (ArchiveService class)
- [ ] Créer `app/api/v1/endpoints/archive.py` (API endpoint)
- [ ] Enregistrer router dans `app/api/v1/api.py`
- [ ] Créer `tests/test_archive_e2e.py` (5 tests E2E)
- [ ] Test archivage basique (sans embeddings)
- [ ] Test archivage avec embeddings RAG
- [ ] Test lessons_learned et win_factors
- [ ] Test delete_original option
- [ ] Test error handling (invalid proposal)
- [ ] Valider tous tests passent
- [ ] Commit Git: "feat: Add archive service and endpoint for tender archiving (Issue #2)"

---

## 📦 Phase 3: RAG Ingestion Knowledge Base (J5-J6)

### 🎯 Objectif
Adapter RAG Service pour ingestion batch des past_proposals et créer script d'ingestion.

---

### Jour 5: Adaptation RAG Service

#### Tâche 5.1: Méthode batch ingestion dans RAG Service

**Fichier**: `backend/app/services/rag_service.py` (ajout de méthode)

```python
# Add to RAGService class

def ingest_all_past_proposals_sync(
    self,
    db: Session,
    batch_size: int = 10,
    status_filter: Optional[str] = "won"
) -> Dict[str, Any]:
    """
    Batch ingest all past proposals for RAG Knowledge Base.

    Args:
        db: Database session
        batch_size: Number of proposals to process per batch
        status_filter: Filter by status ('won', 'lost', 'all')

    Returns:
        Dict with total_proposals, total_embeddings, errors
    """
    from app.models.past_proposal import PastProposal
    from app.models.historical_tender import HistoricalTender

    # Query past proposals
    query = db.query(PastProposal).join(HistoricalTender)

    if status_filter and status_filter != "all":
        query = query.filter(PastProposal.status == status_filter)

    past_proposals = query.all()

    total_proposals = len(past_proposals)
    total_embeddings = 0
    errors = []

    print(f"\n🚀 Starting batch ingestion of {total_proposals} past proposals...")

    for i, proposal in enumerate(past_proposals, 1):
        try:
            print(f"\n[{i}/{total_proposals}] Processing PastProposal {proposal.id}...")

            # Convert sections to list format
            sections_list = []
            for section_num, section_data in proposal.sections.items():
                sections_list.append({
                    "section_number": section_num,
                    "title": section_data.get("title", ""),
                    "content": section_data.get("content", ""),
                    "page": section_data.get("page", 1),
                    "is_key_section": True,
                    "is_toc": False,
                    "level": section_data.get("level", 1)
                })

            # Chunk sections
            chunks = self.chunk_sections_semantic(
                sections=sections_list,
                max_tokens=1000,
                min_tokens=100
            )

            # Get tender metadata
            tender = proposal.historical_tender

            # Ingest
            embeddings_count = self.ingest_document_sync(
                db=db,
                document_id=str(proposal.id),
                chunks=chunks,
                document_type="past_proposal",
                metadata={
                    "historical_tender_id": str(tender.id),
                    "tender_title": tender.title,
                    "organization": tender.organization,
                    "reference_number": tender.reference_number,
                    "status": proposal.status,
                    "score": float(proposal.score_obtained) if proposal.score_obtained else None,
                    "rank": proposal.rank,
                    "win_factors": proposal.win_factors,
                    "is_winning": proposal.is_winning_proposal
                }
            )

            total_embeddings += embeddings_count
            print(f"   ✅ Created {embeddings_count} embeddings")

        except Exception as e:
            error_msg = f"Failed to ingest PastProposal {proposal.id}: {str(e)}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")

    print(f"\n✅ Batch ingestion complete:")
    print(f"   Total proposals: {total_proposals}")
    print(f"   Total embeddings: {total_embeddings}")
    print(f"   Errors: {len(errors)}")

    return {
        "total_proposals": total_proposals,
        "total_embeddings": total_embeddings,
        "errors": errors
    }
```

---

### Jour 6: Script batch et tests

#### Tâche 6.1: Script CLI batch ingestion

**Fichier**: `backend/scripts/ingest_past_proposals.py`

```python
"""
Batch ingest all past proposals for RAG Knowledge Base.

Usage:
    python scripts/ingest_past_proposals.py --status won
    python scripts/ingest_past_proposals.py --status all
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.rag_service import rag_service


def main():
    parser = argparse.ArgumentParser(description="Batch ingest past proposals for RAG Knowledge Base")
    parser.add_argument(
        "--status",
        choices=["won", "lost", "all"],
        default="won",
        help="Filter proposals by status (default: won)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing (default: 10)"
    )

    args = parser.parse_args()

    # Create database session
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("=" * 80)
        print("🚀 BATCH INGESTION - PAST PROPOSALS FOR RAG KNOWLEDGE BASE")
        print("=" * 80)
        print(f"Status filter: {args.status}")
        print(f"Batch size: {args.batch_size}")
        print()

        # Run batch ingestion
        result = rag_service.ingest_all_past_proposals_sync(
            db=db,
            batch_size=args.batch_size,
            status_filter=args.status
        )

        print("\n" + "=" * 80)
        print("✅ BATCH INGESTION COMPLETE")
        print("=" * 80)
        print(f"Total proposals: {result['total_proposals']}")
        print(f"Total embeddings: {result['total_embeddings']}")
        print(f"Errors: {len(result['errors'])}")

        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Chmod executable**:
```bash
chmod +x backend/scripts/ingest_past_proposals.py
```

---

#### Tâche 6.2: Tests RAG retrieval avec Knowledge Base

**Fichier**: `backend/tests/test_rag_knowledge_base.py`

```python
"""
Tests for RAG Knowledge Base retrieval (past_proposals).
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date

from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal
from app.services.rag_service import rag_service


@pytest.fixture
def sample_past_proposals_in_db(db_session):
    """Create sample past proposals with embeddings for testing."""
    # Create 2 historical tenders
    tender1 = HistoricalTender(
        id=uuid4(),
        title="Infogérance infrastructure datacenter - Région Île-de-France",
        organization="Conseil Régional IDF",
        reference_number="IDF-2024-001",
        award_date=date(2024, 6, 1),
        total_amount=Decimal("800000.00"),
        status="awarded"
    )

    tender2 = HistoricalTender(
        id=uuid4(),
        title="Support technique informatique - Ville de Paris",
        organization="Mairie de Paris",
        reference_number="PARIS-2024-002",
        award_date=date(2024, 8, 15),
        total_amount=Decimal("400000.00"),
        status="awarded"
    )

    db_session.add(tender1)
    db_session.add(tender2)
    db_session.flush()

    # Create past proposals
    proposal1 = PastProposal(
        id=uuid4(),
        historical_tender_id=tender1.id,
        our_company_id=uuid4(),
        status="won",
        score_obtained=Decimal("88.00"),
        rank=1,
        sections={
            "1": {
                "title": "Méthodologie ITIL",
                "content": "Notre méthodologie s'appuie sur ITIL v4 avec des processus de gestion des incidents, problèmes et changements. Nous utilisons ServiceNow comme outil ITSM.",
                "page": 1
            },
            "2": {
                "title": "Plan de transition",
                "content": "La transition se fera en 3 phases sur 6 mois avec formation des équipes et transfert de compétences progressif.",
                "page": 2
            }
        },
        win_factors=["itil_methodology", "servicenow_expertise"]
    )

    proposal2 = PastProposal(
        id=uuid4(),
        historical_tender_id=tender2.id,
        our_company_id=uuid4(),
        status="won",
        score_obtained=Decimal("92.00"),
        rank=1,
        sections={
            "1": {
                "title": "Organisation support",
                "content": "Notre centre de support dispose de 3 niveaux (N1, N2, N3) avec des SLA garantis: P1 sous 30min, P2 sous 4h, P3 sous 24h.",
                "page": 1
            }
        },
        win_factors=["strong_sla", "multilevel_support"]
    )

    db_session.add(proposal1)
    db_session.add(proposal2)
    db_session.commit()

    # Create embeddings
    for proposal in [proposal1, proposal2]:
        sections_list = [
            {
                "section_number": num,
                "title": data.get("title", ""),
                "content": data.get("content", ""),
                "page": data.get("page", 1),
                "is_key_section": True,
                "is_toc": False,
                "level": 1
            }
            for num, data in proposal.sections.items()
        ]

        chunks = rag_service.chunk_sections_semantic(sections_list)
        rag_service.ingest_document_sync(
            db=db_session,
            document_id=str(proposal.id),
            chunks=chunks,
            document_type="past_proposal",
            metadata={
                "status": proposal.status,
                "score": float(proposal.score_obtained)
            }
        )

    yield [proposal1, proposal2]

    # Cleanup (cascade will delete embeddings)
    db_session.delete(proposal1)
    db_session.delete(proposal2)
    db_session.delete(tender1)
    db_session.delete(tender2)
    db_session.commit()


@pytest.mark.integration
@pytest.mark.rag
def test_retrieve_past_proposals_by_query(db_session, sample_past_proposals_in_db):
    """Test retrieval of past proposals by semantic query."""
    query = "Quelle est votre méthodologie ITIL ?"

    results = rag_service.retrieve_relevant_content_sync(
        db=db_session,
        query=query,
        top_k=5,
        document_type="past_proposal"
    )

    assert len(results) > 0, "Should retrieve at least 1 result"
    assert results[0]["similarity_score"] > 0.5, "Top result should have high similarity"

    # Verify content contains ITIL
    top_result_content = results[0]["content"].lower()
    assert "itil" in top_result_content or "servicenow" in top_result_content


@pytest.mark.integration
@pytest.mark.rag
def test_retrieve_winning_proposals_only(db_session, sample_past_proposals_in_db):
    """Test filtering retrieval to winning proposals only."""
    query = "Plan de transition"

    results = rag_service.retrieve_relevant_content_sync(
        db=db_session,
        query=query,
        top_k=10,
        document_type="past_proposal",
        metadata_filter={"status": "won"}
    )

    assert len(results) > 0
    # Verify all results are from winning proposals
    for result in results:
        assert result.get("metadata", {}).get("status") == "won"


@pytest.mark.integration
@pytest.mark.rag
def test_batch_ingestion_method(db_session, sample_past_proposals_in_db):
    """Test batch ingestion method."""
    # Delete existing embeddings
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM document_embeddings WHERE document_type = 'past_proposal'"))
    db_session.commit()

    # Run batch ingestion
    result = rag_service.ingest_all_past_proposals_sync(
        db=db_session,
        status_filter="won"
    )

    assert result["total_proposals"] == 2
    assert result["total_embeddings"] > 0
    assert len(result["errors"]) == 0
```

**Lancer les tests**:
```bash
pytest tests/test_rag_knowledge_base.py -v -s
```

---

### 📋 Checklist Phase 3 (J5-J6)

- [ ] Ajouter méthode `ingest_all_past_proposals_sync()` dans `rag_service.py`
- [ ] Créer `scripts/ingest_past_proposals.py` (CLI batch script)
- [ ] Tester script batch sur données réelles
- [ ] Créer `tests/test_rag_knowledge_base.py` (3 tests)
- [ ] Test retrieval par query sémantique
- [ ] Test filtrage winning proposals only
- [ ] Test batch ingestion method
- [ ] Valider tous tests passent
- [ ] Commit Git: "feat: Add batch RAG ingestion for past proposals Knowledge Base (Issue #2)"

---

## 📦 Phase 4: Intégration LLM Service (J7)

### 🎯 Objectif
Enrichir `llm_service.generate_response_section()` pour utiliser RAG Knowledge Base.

---

### Jour 7: Enrichissement LLM avec Knowledge Base

#### Tâche 7.1: Modifier LLM Service pour utiliser KB

**Fichier**: `backend/app/services/llm_service.py` (modification méthode)

```python
# Modify generate_response_section() method in LLMService class

def generate_response_section(
    self,
    db: Session,  # NEW: Add db parameter
    section_title: str,
    section_requirements: str,
    tender_context: Dict[str, Any],
    company_context: Optional[Dict[str, Any]] = None,
    use_knowledge_base: bool = True,  # NEW: Flag to use KB
    kb_top_k: int = 3  # NEW: Number of KB results to retrieve
) -> Dict[str, Any]:
    """
    Generate a response section using LLM with optional Knowledge Base enrichment.

    Args:
        db: Database session (for RAG retrieval)
        section_title: Title of section to generate
        section_requirements: Requirements extracted from tender
        tender_context: Context about current tender
        company_context: Optional company information
        use_knowledge_base: If True, retrieve similar past proposals from KB
        kb_top_k: Number of KB results to include in context

    Returns:
        Dict with generated_content, sources, cost
    """
    from app.services.rag_service import rag_service

    # 1. Build base prompt
    prompt_parts = [
        f"# Section à rédiger: {section_title}\n",
        f"## Exigences du cahier des charges:\n{section_requirements}\n",
        f"## Contexte de l'appel d'offres:\n",
        f"Organisation: {tender_context.get('organization', 'N/A')}\n",
        f"Titre: {tender_context.get('title', 'N/A')}\n",
    ]

    if company_context:
        prompt_parts.append(f"\n## Informations entreprise:\n{company_context}\n")

    # 2. NEW: Retrieve similar sections from Knowledge Base
    kb_context = ""
    sources = []

    if use_knowledge_base and db:
        try:
            # Query: Combine section title + requirements
            kb_query = f"{section_title}\n{section_requirements}"

            # Retrieve from past_proposals
            kb_results = rag_service.retrieve_relevant_content_sync(
                db=db,
                query=kb_query,
                top_k=kb_top_k,
                document_type="past_proposal",
                metadata_filter={"status": "won"}  # Only winning proposals
            )

            if kb_results:
                kb_context += "\n## 📚 Exemples de réponses gagnantes (appels d'offres passés):\n\n"

                for i, result in enumerate(kb_results, 1):
                    metadata = result.get("metadata", {})
                    score = metadata.get("score", "N/A")
                    tender_title = metadata.get("tender_title", "N/A")

                    kb_context += f"### Exemple {i} (Score: {score}/100 - {tender_title}):\n"
                    kb_context += f"{result['content']}\n\n"

                    sources.append({
                        "type": "past_proposal",
                        "tender_title": tender_title,
                        "score": score,
                        "similarity": result["similarity_score"]
                    })

                prompt_parts.append(kb_context)

        except Exception as e:
            print(f"⚠️  Failed to retrieve Knowledge Base context: {e}")
            # Continue without KB if it fails

    # 3. Add generation instruction
    prompt_parts.append("""
## Instructions de génération:
- Rédigez une réponse complète et professionnelle pour cette section
- Adaptez les exemples ci-dessus au contexte spécifique de cet appel d'offres
- Utilisez un ton formel et confiant
- Intégrez des éléments techniques concrets
- Longueur: 300-500 mots

Générez la réponse:
""")

    full_prompt = "\n".join(prompt_parts)

    # 4. Call Claude API
    try:
        response = self.sync_client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.3,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )

        generated_content = response.content[0].text

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 0.003 / 1000) + (output_tokens * 0.015 / 1000)

        return {
            "generated_content": generated_content,
            "sources": sources,
            "cost": cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "kb_used": len(sources) > 0
        }

    except Exception as e:
        raise ValueError(f"LLM generation failed: {str(e)}")
```

---

#### Tâche 7.2: Tests intégration LLM + KB

**Fichier**: `backend/tests/test_llm_with_kb.py`

```python
"""
Integration tests for LLM Service with Knowledge Base.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date

from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal
from app.services.llm_service import LLMService
from app.services.rag_service import rag_service


@pytest.fixture
def llm_with_kb_context(db_session):
    """Create Knowledge Base context for LLM testing."""
    # Create historical tender
    tender = HistoricalTender(
        id=uuid4(),
        title="Infogérance Datacenter - Référence",
        organization="Référence Org",
        reference_number="REF-KB-001",
        status="awarded"
    )
    db_session.add(tender)
    db_session.flush()

    # Create winning proposal with methodology section
    proposal = PastProposal(
        id=uuid4(),
        historical_tender_id=tender.id,
        our_company_id=uuid4(),
        status="won",
        score_obtained=Decimal("90.00"),
        rank=1,
        sections={
            "3": {
                "title": "Méthodologie projet",
                "content": """Notre méthodologie s'appuie sur les frameworks ITIL v4 et PRINCE2.
                Nous organisons le projet en 4 phases:
                1. Initialisation et cadrage (1 mois)
                2. Transition et formation (2 mois)
                3. Run et amélioration continue (ongoing)
                4. Bilan et optimisation (trimestriel)

                Nous utilisons des outils collaboratifs (Jira, Confluence) et assurons
                une gouvernance hebdomadaire avec COPIL mensuel.""",
                "page": 5
            }
        },
        win_factors=["strong_methodology", "itil_prince2"]
    )
    db_session.add(proposal)
    db_session.commit()

    # Create embeddings
    sections_list = [{
        "section_number": "3",
        "title": proposal.sections["3"]["title"],
        "content": proposal.sections["3"]["content"],
        "page": 5,
        "is_key_section": True,
        "is_toc": False,
        "level": 1
    }]

    chunks = rag_service.chunk_sections_semantic(sections_list)
    rag_service.ingest_document_sync(
        db=db_session,
        document_id=str(proposal.id),
        chunks=chunks,
        document_type="past_proposal",
        metadata={
            "status": "won",
            "score": 90.0,
            "tender_title": tender.title
        }
    )

    yield tender, proposal

    # Cleanup
    db_session.delete(proposal)
    db_session.delete(tender)
    db_session.commit()


@pytest.mark.integration
@pytest.mark.slow
def test_llm_generate_with_knowledge_base(db_session, llm_with_kb_context):
    """Test LLM generation with Knowledge Base enrichment."""
    llm_service = LLMService()

    result = llm_service.generate_response_section(
        db=db_session,
        section_title="Méthodologie de mise en œuvre",
        section_requirements="Décrire la méthodologie projet, les phases, les outils et la gouvernance",
        tender_context={
            "organization": "Nouvelle Organisation Test",
            "title": "Infogérance IT - Test"
        },
        use_knowledge_base=True,
        kb_top_k=3
    )

    # Assertions
    assert result["generated_content"] is not None
    assert len(result["generated_content"]) > 100, "Generated content should be substantial"
    assert result["kb_used"] is True, "Knowledge Base should be used"
    assert len(result["sources"]) > 0, "Should have KB sources"

    # Verify sources are from winning proposals
    for source in result["sources"]:
        assert source["type"] == "past_proposal"
        assert source["score"] == 90.0

    # Verify generated content quality (contains methodology keywords)
    content_lower = result["generated_content"].lower()
    assert any(keyword in content_lower for keyword in ["méthodologie", "phase", "gouvernance", "itil", "projet"])


@pytest.mark.integration
def test_llm_generate_without_knowledge_base(db_session):
    """Test LLM generation WITHOUT Knowledge Base (baseline)."""
    llm_service = LLMService()

    result = llm_service.generate_response_section(
        db=db_session,
        section_title="Organisation support",
        section_requirements="Décrire l'organisation du support (niveaux, horaires, SLA)",
        tender_context={
            "organization": "Test Org",
            "title": "Support IT"
        },
        use_knowledge_base=False  # Disable KB
    )

    assert result["generated_content"] is not None
    assert result["kb_used"] is False, "Knowledge Base should NOT be used"
    assert len(result["sources"]) == 0, "Should have NO KB sources"


@pytest.mark.integration
@pytest.mark.slow
def test_llm_kb_improves_quality(db_session, llm_with_kb_context):
    """Test that KB improves response quality (comparison test)."""
    llm_service = LLMService()

    # Generate WITH KB
    result_with_kb = llm_service.generate_response_section(
        db=db_session,
        section_title="Méthodologie",
        section_requirements="Méthodologie projet",
        tender_context={"organization": "Test", "title": "Test"},
        use_knowledge_base=True
    )

    # Generate WITHOUT KB
    result_without_kb = llm_service.generate_response_section(
        db=db_session,
        section_title="Méthodologie",
        section_requirements="Méthodologie projet",
        tender_context={"organization": "Test", "title": "Test"},
        use_knowledge_base=False
    )

    # KB version should be longer (more detailed)
    assert len(result_with_kb["generated_content"]) >= len(result_without_kb["generated_content"])

    # KB version should mention ITIL (from example)
    assert "itil" in result_with_kb["generated_content"].lower() or "prince2" in result_with_kb["generated_content"].lower()
```

**Lancer les tests**:
```bash
pytest tests/test_llm_with_kb.py -v -s
```

---

### 📋 Checklist Phase 4 (J7)

- [ ] Modifier `llm_service.generate_response_section()` pour intégrer KB
- [ ] Ajouter paramètres `use_knowledge_base` et `kb_top_k`
- [ ] Implémenter retrieval RAG dans méthode
- [ ] Formatter KB context dans prompt LLM
- [ ] Créer `tests/test_llm_with_kb.py` (3 tests)
- [ ] Test génération WITH KB (sources présentes)
- [ ] Test génération WITHOUT KB (baseline)
- [ ] Test comparaison qualité (KB améliore réponse)
- [ ] Valider tous tests passent
- [ ] Commit Git: "feat: Integrate RAG Knowledge Base into LLM response generation (Issue #2)"

---

## 🎯 Validation Finale et Déploiement

### Checklist Globale (Toutes Phases)

#### Base de Données
- [ ] Migration Alembic créée et appliquée
- [ ] Tables `historical_tenders` et `past_proposals` créées
- [ ] Index créés (reference_number, status, archived_at, etc.)
- [ ] Relations FK fonctionnelles (CASCADE DELETE)
- [ ] Contrainte UNIQUE (tender + company) validée

#### Modèles SQLAlchemy
- [ ] `HistoricalTender` model complet
- [ ] `PastProposal` model complet
- [ ] Relations bidirectionnelles testées
- [ ] Méthodes `to_dict()` implémentées
- [ ] Properties (`is_winning_proposal`, `win_rate_percentage`)

#### Services
- [ ] `ArchiveService` créé et testé
- [ ] `RAGService.ingest_all_past_proposals_sync()` ajouté
- [ ] `LLMService.generate_response_section()` enrichi avec KB
- [ ] Error handling robuste

#### API Endpoints
- [ ] `POST /archive/tenders/{id}/archive` créé
- [ ] Request/Response schemas Pydantic
- [ ] Documentation OpenAPI auto-générée
- [ ] Tests E2E endpoint

#### Scripts CLI
- [ ] `scripts/ingest_past_proposals.py` créé
- [ ] Paramètres CLI (status, batch-size)
- [ ] Logging informatif
- [ ] Error handling

#### Tests
- [ ] `test_historical_models.py` (6 tests) ✅
- [ ] `test_archive_e2e.py` (5 tests) ✅
- [ ] `test_rag_knowledge_base.py` (3 tests) ✅
- [ ] `test_llm_with_kb.py` (3 tests) ✅
- [ ] **Total: 17 tests** pour cette fonctionnalité

#### Documentation
- [ ] ISSUE_2_RAG_KNOWLEDGE_BASE_ANALYSIS.md ✅
- [ ] IMPLEMENTATION_PLAN_SOLUTION_1.md (ce fichier) ✅
- [ ] Code docstrings complets
- [ ] README mis à jour (si nécessaire)

#### Git
- [ ] 4 commits structurés (1 par phase)
- [ ] Messages clairs avec référence (Issue #2)
- [ ] Branch `feature/historical-kb-solution1` créée
- [ ] Pull Request vers `main`

---

## 🚀 Commandes de Test Complet

```bash
# 1. Tests modèles
pytest tests/test_historical_models.py -v

# 2. Tests archivage
pytest tests/test_archive_e2e.py -v -s

# 3. Tests RAG KB
pytest tests/test_rag_knowledge_base.py -v -s

# 4. Tests LLM + KB
pytest tests/test_llm_with_kb.py -v -s

# 5. Tous les tests de la feature
pytest tests/test_historical_models.py tests/test_archive_e2e.py tests/test_rag_knowledge_base.py tests/test_llm_with_kb.py -v

# 6. Coverage
pytest tests/test_historical_models.py tests/test_archive_e2e.py tests/test_rag_knowledge_base.py tests/test_llm_with_kb.py --cov=app --cov-report=html

# 7. Test archivage manuel d'un tender réel
python scripts/ingest_past_proposals.py --status won
```

---

## 📈 Métriques de Succès

| Métrique | Cible | Validation |
|----------|-------|------------|
| Tests passés | 17/17 | pytest -v |
| Coverage code | >80% | pytest --cov |
| Migration réussie | ✅ | alembic upgrade head |
| Archivage manuel | ✅ | POST /archive/tenders/{id}/archive |
| Batch ingestion | ✅ | scripts/ingest_past_proposals.py |
| KB retrieval | Recall@3 >70% | Test manuel avec queries |
| LLM + KB qualité | Amélioration visible | Comparaison avec/sans KB |
| Performance | <5s archivage | Mesure sur tender réel |
| API docs | 100% endpoints | /docs Swagger UI |

---

## 🔄 Workflow Utilisateur Final

### Scenario 1: Archivage d'un tender gagné

```bash
# 1. Tender terminé, nous avons gagné
# 2. Bid manager remplit post-mortem
curl -X POST "http://localhost:8000/api/v1/archive/tenders/{tender_id}/archive" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "123e4567-e89b-12d3-a456-426614174000",
    "proposal_status": "won",
    "score_obtained": 88.50,
    "rank": 1,
    "total_bidders": 7,
    "lessons_learned": "Mémo technique fort, pricing compétitif",
    "win_factors": ["strong_technical_memo", "competitive_price", "itil_expertise"],
    "create_embeddings": true
  }'

# 3. Système crée HistoricalTender + PastProposal + Embeddings RAG
# 4. Knowledge Base enrichie automatiquement
```

### Scenario 2: Génération réponse avec KB

```python
# Frontend appelle endpoint de génération (futur Sprint 3)
POST /api/v1/proposals/{proposal_id}/generate-section

{
  "section_title": "Méthodologie projet",
  "section_requirements": "Décrire phases, outils, gouvernance",
  "use_knowledge_base": true
}

# Backend:
# 1. Retrieve top 3 similar sections from past_proposals (won)
# 2. Inject in LLM prompt as examples
# 3. Generate enriched response
# 4. Return with sources for transparency
```

---

## 📞 Support et Questions

**Issue GitHub**: [#2 - RAG Knowledge Base](https://github.com/cisbeo/scorpiusAO/issues/2)

**Questions fréquentes**:

**Q: Faut-il archiver tous les tenders ou seulement les gagnés ?**
R: Archiver tous (won + lost). Les perdus sont utiles pour analyse (ce qui n'a PAS marché). Filtrer par `status="won"` lors du retrieval RAG.

**Q: Que faire si archivage échoue à mi-chemin (HistoricalTender créé mais PastProposal rate) ?**
R: Transaction rollback automatique (SQLAlchemy). Rien n'est committé si une partie échoue.

**Q: Performance avec 1000+ past_proposals ?**
R: pgvector + index ivfflat scale jusqu'à 100k+ embeddings. Monitoring requis au-delà.

**Q: Peut-on archiver plusieurs proposals pour le même tender (multi-soumissions) ?**
R: Oui si `our_company_id` différent (multi-tenancy). Sinon, contrainte UNIQUE bloque.

---

**Auteur**: Équipe Backend ScorpiusAO
**Date**: 3 octobre 2025
**Version**: 1.0 - Plan détaillé complet
**Status**: ✅ Prêt pour implémentation Sprint 2
