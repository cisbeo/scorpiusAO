# 📊 Analyse Issue #2 - RAG Knowledge Base (past_proposals & historical_tenders)

**Issue GitHub**: [#2 - RAG Implementation for Knowledge Base](https://github.com/cisbeo/scorpiusAO/issues/2)
**Date**: 3 octobre 2025
**Status**: 🔍 Analyse en cours
**Priorité**: MOYENNE (Sprint 2)

---

## 🎯 Contexte

### Situation Actuelle

**RAG Service implémenté (Sprint 1 - Solution 5.5)**:
- ✅ Q&A sur tender actuel (`document_type="tender"`)
- ✅ Endpoint `/tenders/{id}/ask` avec cache Redis
- ✅ Embeddings OpenAI text-embedding-3-small (1536 dim)
- ✅ Recherche vectorielle pgvector (cosine similarity)
- ✅ Métriques validées: Recall@5: 100%, Coût: $0.016/tender

**RAG Knowledge Base planifié (Sprint 2)**:
- ⏳ Ingestion `past_proposals` (propositions gagnantes passées)
- ⏳ Ingestion `historical_tenders` (appels d'offres historiques)
- ⏳ Ingestion `case_studies`, `certifications`, `references`
- ⏳ Utilisation pour génération de réponses (contexte entreprise)

### Problème Identifié (Issue #2)

**Modèle SQLAlchemy manquant**:
- `app/models/past_proposal.py` n'existe pas
- `app/models/historical_tender.py` n'existe pas
- Relation bidirectionnelle à définir entre les deux entités

**Questions architecturales**:
1. Comment modéliser la relation `HistoricalTender ↔ PastProposal` ?
2. Faut-il dupliquer les données des tables `tenders` et `proposals` existantes ?
3. Comment gérer le cycle de vie (tender actuel → historical après fin) ?
4. Quelle granularité pour les embeddings (par proposition entière ou par section) ?

---

## 🏗️ Architecture Actuelle

### Modèles Existants

```
tenders (table existante)
├── id: UUID
├── title, organization, reference_number
├── deadline, status, source
├── raw_content, parsed_content (JSON)
└── Relations: documents, analysis, criteria

proposals (table existante)
├── id: UUID
├── tender_id: FK(tenders.id)
├── user_id: UUID
├── sections: JSON
├── compliance_score, status, version
└── Relations: (commentées pour l'instant)

document_embeddings (table RAG - Sprint 1)
├── id: UUID
├── document_id: UUID (référence générique)
├── document_type: VARCHAR (tender, past_proposal, case_study, etc.)
├── chunk_text: TEXT
├── embedding: vector(1536)
├── metadata: JSONB
└── Index: ivfflat (embedding vector_cosine_ops)
```

### Flux Actuel (Sprint 1 - Q&A Tender)

```
1. Upload PDF → TenderDocument
2. Parse sections → DocumentSection
3. Chunk sections → RAG Service
4. Create embeddings → document_embeddings (document_type="tender")
5. User Q&A → Retrieve + LLM → Answer
```

---

## 🎨 3 Solutions Proposées

### 📌 Solution 1: Tables Séparées avec Vue Unifiée (Recommandée)

**Architecture**:
```sql
-- Nouvelles tables dédiées
CREATE TABLE historical_tenders (
    id UUID PRIMARY KEY,
    title VARCHAR(500),
    organization VARCHAR(200),
    reference_number VARCHAR(100),
    publication_date DATE,
    deadline DATE,
    award_date DATE,
    total_amount NUMERIC(12,2),
    status VARCHAR(50) DEFAULT 'awarded',
    archived_at TIMESTAMP,
    metadata JSONB,  -- Stocke raw_content, parsed_content
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE past_proposals (
    id UUID PRIMARY KEY,
    historical_tender_id UUID REFERENCES historical_tenders(id) ON DELETE CASCADE,
    our_company_id UUID,  -- Si multi-tenancy
    status VARCHAR(50),  -- 'won', 'lost', 'shortlisted'
    score_obtained NUMERIC(5,2),
    rank INTEGER,
    sections JSONB,  -- Contenu complet de la proposition
    lessons_learned TEXT,
    win_factors TEXT[],  -- Array de facteurs de succès
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Contrainte: une seule proposition par entreprise par tender
    UNIQUE(historical_tender_id, our_company_id)
);

-- Relation: One-to-Many (HistoricalTender 1 → N PastProposals)
-- Un tender historique peut avoir plusieurs propositions (concurrents)
-- Mais on ne stocke que NOTRE proposition (our_company_id)
```

**Modèle SQLAlchemy**:
```python
# app/models/historical_tender.py
class HistoricalTender(Base):
    __tablename__ = "historical_tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), nullable=False)
    organization = Column(String(200))
    reference_number = Column(String(100), index=True)
    publication_date = Column(Date)
    deadline = Column(Date)
    award_date = Column(Date)
    total_amount = Column(Numeric(12, 2))
    status = Column(String(50), default="awarded")
    archived_at = Column(DateTime(timezone=True))
    metadata = Column(JSON)  # raw_content, parsed_content
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relation One-to-Many
    past_proposals = relationship(
        "PastProposal",
        back_populates="historical_tender",
        cascade="all, delete-orphan"
    )

# app/models/past_proposal.py
class PastProposal(Base):
    __tablename__ = "past_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    historical_tender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    our_company_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50))  # won, lost, shortlisted
    score_obtained = Column(Numeric(5, 2))
    rank = Column(Integer)
    sections = Column(JSON)
    lessons_learned = Column(Text)
    win_factors = Column(ARRAY(String))
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relation Many-to-One
    historical_tender = relationship(
        "HistoricalTender",
        back_populates="past_proposals"
    )

    __table_args__ = (
        UniqueConstraint('historical_tender_id', 'our_company_id'),
    )
```

**Ingestion RAG**:
```python
# Approche 1: Embeddings par section
for proposal in past_proposals:
    sections = proposal.sections  # JSON
    chunks = rag_service.chunk_sections_semantic(sections)
    rag_service.ingest_document_sync(
        db=db,
        document_id=str(proposal.id),
        chunks=chunks,
        document_type="past_proposal",
        metadata={
            "historical_tender_id": str(proposal.historical_tender_id),
            "status": proposal.status,
            "score": float(proposal.score_obtained),
            "win_factors": proposal.win_factors
        }
    )

# Approche 2: Embeddings du tender historique (pour similarité)
for tender in historical_tenders:
    text = f"{tender.title}\n{tender.metadata.get('description', '')}"
    rag_service.ingest_document_sync(
        db=db,
        document_id=str(tender.id),
        chunks=[{"content": text}],
        document_type="historical_tender",
        metadata={
            "organization": tender.organization,
            "amount": float(tender.total_amount) if tender.total_amount else None
        }
    )
```

**Migration Tender → Historical**:
```python
# Script de migration (manuel ou automatique après award_date)
def archive_tender_to_historical(tender_id: UUID, proposal_id: UUID):
    """
    Migre un tender actuel + notre proposition vers l'historique.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()

    # 1. Créer historical_tender
    historical = HistoricalTender(
        id=uuid4(),
        title=tender.title,
        organization=tender.organization,
        reference_number=tender.reference_number,
        publication_date=tender.created_at.date(),
        deadline=tender.deadline.date() if tender.deadline else None,
        award_date=datetime.utcnow().date(),
        status="awarded",
        archived_at=datetime.utcnow(),
        metadata={
            "original_tender_id": str(tender.id),
            "raw_content": tender.raw_content,
            "parsed_content": tender.parsed_content
        }
    )
    db.add(historical)
    db.flush()

    # 2. Créer past_proposal
    past_proposal = PastProposal(
        id=uuid4(),
        historical_tender_id=historical.id,
        our_company_id=proposal.user_id,
        status="won",  # Ou demander à l'utilisateur
        score_obtained=Decimal(proposal.compliance_score) if proposal.compliance_score else None,
        sections=proposal.sections,
        lessons_learned="",  # À remplir manuellement
        win_factors=[],
        metadata={"original_proposal_id": str(proposal.id)}
    )
    db.add(past_proposal)
    db.commit()

    # 3. Créer embeddings
    # ... (voir code ci-dessus)

    # 4. Optionnel: Supprimer tender/proposal originaux
    # db.delete(tender)
    # db.commit()
```

**✅ Avantages**:
1. **Séparation claire** entre données actives (tenders) et archivées (historical)
2. **Pas de duplication** de schéma (tables différentes avec colonnes adaptées)
3. **Métadonnées spécifiques** à l'historique (award_date, score, win_factors)
4. **Performance** optimale (queries sur historical_tenders sans polluer tenders)
5. **Évolutivité** facile (ajout colonnes spécifiques historique sans impacter tenders)
6. **RAG optimisé** (metadata ciblée pour retrieval: won/lost, score, etc.)
7. **Migration contrôlée** (archivage explicite après award)

**❌ Inconvénients**:
1. **Duplication de données** (tender existant copié dans historical)
2. **Migration manuelle** (script à lancer pour archiver)
3. **2 modèles à maintenir** (Tender + HistoricalTender)
4. **Complexité accrue** (2 pipelines: tenders actifs + historiques)

**🎯 Cas d'usage idéal**:
- Entreprise avec beaucoup de tenders (>100/an)
- Besoin de recherche performante dans l'historique
- Métadonnées spécifiques historique importantes (win rate, score, etc.)
- Archivage réglementaire requis

---

### 📌 Solution 2: Status-Based avec Flag `is_archived` (Simple)

**Architecture**:
```sql
-- Réutiliser tables existantes avec flag
ALTER TABLE tenders ADD COLUMN is_archived BOOLEAN DEFAULT false;
ALTER TABLE tenders ADD COLUMN archived_at TIMESTAMP;
ALTER TABLE tenders ADD COLUMN award_date DATE;
ALTER TABLE tenders ADD COLUMN total_amount NUMERIC(12,2);

ALTER TABLE proposals ADD COLUMN is_archived BOOLEAN DEFAULT false;
ALTER TABLE proposals ADD COLUMN score_obtained NUMERIC(5,2);
ALTER TABLE proposals ADD COLUMN rank INTEGER;
ALTER TABLE proposals ADD COLUMN lessons_learned TEXT;
ALTER TABLE proposals ADD COLUMN win_factors TEXT[];

-- Index pour performance
CREATE INDEX idx_tenders_archived ON tenders(is_archived, archived_at);
CREATE INDEX idx_proposals_archived ON proposals(is_archived);
```

**Modèle SQLAlchemy** (modification des modèles existants):
```python
# app/models/tender.py
class Tender(Base):
    __tablename__ = "tenders"

    # Colonnes existantes...
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), nullable=False, index=True)
    # ...

    # Nouvelles colonnes pour archivage
    is_archived = Column(Boolean, default=False, index=True)
    archived_at = Column(DateTime(timezone=True))
    award_date = Column(Date)
    total_amount = Column(Numeric(12, 2))

# app/models/proposal.py
class Proposal(Base):
    __tablename__ = "proposals"

    # Colonnes existantes...
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"))
    # ...

    # Nouvelles colonnes pour archivage
    is_archived = Column(Boolean, default=False, index=True)
    score_obtained = Column(Numeric(5, 2))
    rank = Column(Integer)
    lessons_learned = Column(Text)
    win_factors = Column(ARRAY(String))
```

**Ingestion RAG**:
```python
# Requête pour récupérer proposals archivées
archived_proposals = db.query(Proposal).filter(
    Proposal.is_archived == True,
    Proposal.status == "won"  # Seulement propositions gagnantes
).all()

for proposal in archived_proposals:
    chunks = rag_service.chunk_sections_semantic(proposal.sections)
    rag_service.ingest_document_sync(
        db=db,
        document_id=str(proposal.id),
        chunks=chunks,
        document_type="past_proposal",  # Même table, type différent
        metadata={
            "tender_id": str(proposal.tender_id),
            "status": proposal.status,
            "score": float(proposal.score_obtained) if proposal.score_obtained else None,
            "is_archived": True
        }
    )
```

**Migration (simple flag)**:
```python
def archive_tender(tender_id: UUID, proposal_id: UUID, status: str = "won"):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()

    # Flag archivage
    tender.is_archived = True
    tender.archived_at = datetime.utcnow()

    proposal.is_archived = True
    proposal.status = status  # won, lost, shortlisted

    db.commit()

    # Créer embeddings
    # ... (voir code ci-dessus)
```

**Queries**:
```python
# Tenders actifs
active_tenders = db.query(Tender).filter(Tender.is_archived == False).all()

# Tenders archivés (historique)
historical_tenders = db.query(Tender).filter(Tender.is_archived == True).all()

# Propositions gagnantes (Knowledge Base)
won_proposals = db.query(Proposal).filter(
    Proposal.is_archived == True,
    Proposal.status == "won"
).all()
```

**✅ Avantages**:
1. **Simplicité extrême** (1 migration Alembic, pas de nouveaux modèles)
2. **Pas de duplication** de schéma (réutilisation tables existantes)
3. **Migration instantanée** (UPDATE is_archived = true)
4. **1 seul pipeline** (même code pour actifs/archivés)
5. **Facile à maintenir** (moins de code, moins de bugs)
6. **Rollback facile** (UPDATE is_archived = false si erreur)
7. **Relations existantes** conservées (tender ↔ proposal)

**❌ Inconvénients**:
1. **Pollution de la table tenders** (mélange actifs + archivés)
2. **Performance dégradée** (index sur is_archived nécessaire, table plus large)
3. **Queries complexes** (ALWAYS filter is_archived dans tous les endpoints)
4. **Risque d'oubli** (oublier le filtre → afficher tenders archivés par erreur)
5. **Moins de flexibilité** (colonnes historique mélangées avec colonnes actives)
6. **Coût de migration** (ALTER TABLE sur table potentiellement grande)

**🎯 Cas d'usage idéal**:
- MVP rapide (Sprint 2 avec peu de temps)
- Petit volume de tenders (<50/an)
- Équipe réduite (moins de code à maintenir)
- Pas de métadonnées spécifiques historique complexes

---

### 📌 Solution 3: Polymorphic Inheritance avec STI (Single Table Inheritance)

**Architecture**:
```sql
-- Table unifiée avec discriminateur
CREATE TABLE tenders (
    id UUID PRIMARY KEY,
    tender_type VARCHAR(50) NOT NULL,  -- 'active', 'historical'
    title VARCHAR(500),
    -- ... colonnes communes ...

    -- Colonnes spécifiques active (nullable)
    deadline TIMESTAMP,
    status VARCHAR(50),

    -- Colonnes spécifiques historical (nullable)
    award_date DATE,
    total_amount NUMERIC(12,2),
    archived_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tenders_type ON tenders(tender_type);

-- Idem pour proposals
CREATE TABLE proposals (
    id UUID PRIMARY KEY,
    proposal_type VARCHAR(50) NOT NULL,  -- 'draft', 'submitted', 'past'
    tender_id UUID REFERENCES tenders(id),
    -- ... colonnes communes ...

    -- Colonnes spécifiques past (nullable)
    score_obtained NUMERIC(5,2),
    rank INTEGER,
    lessons_learned TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

**Modèle SQLAlchemy** (Polymorphic):
```python
# app/models/tender.py
class TenderBase(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    organization = Column(String(200))
    reference_number = Column(String(100))

    # Colonnes communes
    raw_content = Column(Text)
    parsed_content = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Colonnes spécifiques (nullable)
    deadline = Column(DateTime(timezone=True))  # Pour active
    status = Column(String(50))  # Pour active
    award_date = Column(Date)  # Pour historical
    total_amount = Column(Numeric(12, 2))  # Pour historical
    archived_at = Column(DateTime(timezone=True))  # Pour historical

    __mapper_args__ = {
        "polymorphic_identity": "tender_base",
        "polymorphic_on": tender_type,
        "with_polymorphic": "*"
    }

class ActiveTender(TenderBase):
    """Tender actif (en cours)"""
    __mapper_args__ = {
        "polymorphic_identity": "active"
    }

class HistoricalTender(TenderBase):
    """Tender historique (archivé)"""
    __mapper_args__ = {
        "polymorphic_identity": "historical"
    }
```

**Usage**:
```python
# Créer tender actif
active = ActiveTender(
    title="Appel d'offres infogérance",
    deadline=datetime(2025, 4, 15),
    status="new"
)
db.add(active)

# Archiver (polymorphic update)
historical = HistoricalTender(
    id=active.id,  # Même ID
    title=active.title,
    award_date=datetime.utcnow().date(),
    total_amount=Decimal("500000.00")
)
db.merge(historical)  # Update du type

# Query
actives = db.query(ActiveTender).all()  # Filtre auto tender_type='active'
historicals = db.query(HistoricalTender).all()  # Filtre auto tender_type='historical'
```

**✅ Avantages**:
1. **Table unique** (pas de duplication de schéma)
2. **Type safety** (ActiveTender vs HistoricalTender dans le code)
3. **Queries automatiques** (SQLAlchemy filtre tender_type automatiquement)
4. **Flexibilité** (ajout de nouveaux types: DraftTender, TemplateTender, etc.)
5. **Migrations simples** (UPDATE tender_type pour archiver)

**❌ Inconvénients**:
1. **Colonnes nullable** (deadline nullable pour historical, award_date nullable pour active)
2. **Validation complexe** (vérifier cohérence colonnes selon type)
3. **Performance** (index sur tender_type + colonnes nullable moins efficaces)
4. **Confusion potentielle** (colonnes inutilisées selon type)
5. **Moins standard** (pattern STI moins courant en Python/FastAPI)
6. **Risque de bloat** (table très large avec beaucoup de types)

**🎯 Cas d'usage idéal**:
- Besoin de multiples types de tenders (active, draft, template, historical, archived, deleted)
- Équipe familière avec l'ORM polymorphique
- Besoin de queries type-safe dans le code

---

## 📊 Comparaison des 3 Solutions

| Critère | Solution 1: Tables Séparées | Solution 2: Flag `is_archived` | Solution 3: Polymorphic STI |
|---------|---------------------------|-------------------------------|---------------------------|
| **Complexité implémentation** | 🟡 Moyenne (2 nouveaux modèles) | 🟢 Faible (1 migration) | 🔴 Élevée (polymorphic ORM) |
| **Performance queries** | 🟢 Excellente (tables séparées) | 🟡 Moyenne (index required) | 🟡 Moyenne (discriminator) |
| **Maintenance** | 🟡 Moyenne (2 modèles) | 🟢 Faible (1 modèle) | 🔴 Élevée (validation complexe) |
| **Duplication de données** | 🔴 Oui (copie explicite) | 🟢 Non (même table) | 🟢 Non (même table) |
| **Flexibilité métadonnées** | 🟢 Excellente (colonnes dédiées) | 🟡 Moyenne (colonnes mixtes) | 🟡 Moyenne (nullable) |
| **Risque d'erreur** | 🟢 Faible (séparation claire) | 🔴 Élevé (oubli filtre) | 🟡 Moyen (validation type) |
| **Scalabilité** | 🟢 Excellente (archivage DB) | 🟡 Moyenne (table grosse) | 🟡 Moyenne (table grosse) |
| **Migration facile** | 🔴 Non (script complexe) | 🟢 Oui (UPDATE simple) | 🟢 Oui (UPDATE type) |
| **RAG metadata qualité** | 🟢 Excellente (dédiée) | 🟡 Bonne (mixte) | 🟡 Bonne (mixte) |
| **Coût développement** | 🔴 Élevé (2-3 jours) | 🟢 Faible (1 jour) | 🔴 Élevé (3-4 jours) |

**Légende**: 🟢 Bon | 🟡 Moyen | 🔴 Problématique

---

## 🎯 Recommandation Finale

### Pour ScorpiusAO (contexte actuel)

**Recommandation: Solution 1 (Tables Séparées)** 🏆

**Justification**:

1. **Volume attendu élevé** (entreprise visant >100 tenders/an)
2. **Métadonnées spécifiques critiques** (win_factors, lessons_learned pour ML futur)
3. **Performance RAG cruciale** (retrieval sur milliers de propositions)
4. **Archivage réglementaire** (séparation claire actifs/archivés)
5. **Sprint 2 planifié** (2 semaines disponibles pour implémentation propre)
6. **Évolution ML** (Solution 5.6 Adaptive nécessite métadonnées qualité)

**Alternative Sprint 2 MVP**: **Solution 2 (Flag is_archived)**

Si contrainte temps forte (1 semaine au lieu de 2), démarrer avec Solution 2 puis migrer vers Solution 1 au Sprint 3.

**À éviter**: Solution 3 (STI) - Complexité disproportionnée pour le besoin.

---

## 🚀 Plan d'Implémentation (Solution 1 Recommandée)

### Phase 1: Modèles et Migration (2 jours)

**Tâches**:
1. ✅ Créer `app/models/historical_tender.py`
2. ✅ Créer `app/models/past_proposal.py`
3. ✅ Migration Alembic (CREATE TABLE historical_tenders, past_proposals)
4. ✅ Tests unitaires modèles (relations, contraintes)

### Phase 2: Script d'Archivage (1 jour)

**Tâches**:
1. ✅ Fonction `archive_tender_to_historical(tender_id, proposal_id, status)`
2. ✅ Endpoint API `POST /tenders/{id}/archive`
3. ✅ Validation (tender terminé, proposal existe)
4. ✅ Tests E2E archivage

### Phase 3: RAG Ingestion (2 jours)

**Tâches**:
1. ✅ Adapter `rag_service.ingest_document_sync()` pour past_proposals
2. ✅ Script batch `ingest_all_past_proposals.py`
3. ✅ Metadata optimization (win_factors, score, etc.)
4. ✅ Tests RAG retrieval avec document_type="past_proposal"

### Phase 4: Integration Response Generation (2 jours)

**Tâches**:
1. ✅ Modifier `llm_service.generate_response_section()` pour utiliser RAG KB
2. ✅ Retrieval hybrid (current tender + past_proposals)
3. ✅ Prompt enrichment avec contexte historique
4. ✅ Tests qualité réponse (avec/sans KB)

**Total estimé**: 7 jours ouvrés (Sprint 2 = 10 jours)

---

## 📝 Code de Démarrage (Solution 1)

### Migration Alembic

```python
# alembic/versions/xxx_add_historical_models.py
"""Add historical_tenders and past_proposals tables

Revision ID: xxx
Revises: yyy
Create Date: 2025-10-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'historical_tenders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('organization', sa.String(200)),
        sa.Column('reference_number', sa.String(100)),
        sa.Column('publication_date', sa.Date),
        sa.Column('deadline', sa.Date),
        sa.Column('award_date', sa.Date),
        sa.Column('total_amount', sa.Numeric(12, 2)),
        sa.Column('status', sa.String(50), server_default='awarded'),
        sa.Column('archived_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_historical_tenders_ref', 'historical_tenders', ['reference_number'])

    op.create_table(
        'past_proposals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('historical_tender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('our_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50)),
        sa.Column('score_obtained', sa.Numeric(5, 2)),
        sa.Column('rank', sa.Integer),
        sa.Column('sections', postgresql.JSON),
        sa.Column('lessons_learned', sa.Text),
        sa.Column('win_factors', postgresql.ARRAY(sa.String)),
        sa.Column('metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['historical_tender_id'], ['historical_tenders.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('historical_tender_id', 'our_company_id', name='uq_past_proposal_tender_company')
    )
    op.create_index('idx_past_proposals_tender', 'past_proposals', ['historical_tender_id'])
    op.create_index('idx_past_proposals_status', 'past_proposals', ['status'])

def downgrade():
    op.drop_table('past_proposals')
    op.drop_table('historical_tenders')
```

---

## 🔗 Prochaines Étapes

1. **Valider la solution** avec l'équipe (Solution 1 ou 2)
2. **Créer issue GitHub** détaillée avec tasks
3. **Planifier Sprint 2** (2 semaines)
4. **Implémenter Phase 1** (modèles + migration)
5. **Tester E2E** avec VSGP-AO archivé

**Issue GitHub #2 - Status**: 🔍 Analyse complétée → ⏳ En attente validation

---

**Auteur**: Équipe ScorpiusAO
**Date**: 3 octobre 2025
**Version**: 1.0
