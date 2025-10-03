# 🎯 PLAN DÉTAILLÉ - RAG Service MVP v2.0 (Priorité 1)

**Durée estimée** : 2-3 jours
**Objectif** : RAG Service opérationnel avec chunking sémantique, méthodes synchrones, endpoint Q&A, validation recall@5 > 80%

**Date** : 3 octobre 2025
**Sprint** : Sprint 1-2 (Solution 5 MVP)

---

## 📊 VUE D'ENSEMBLE

### ✅ État Actuel (Ce qui fonctionne)
- ✅ Parser Service : extraction PDF + sections structurées (377 sections VSGP-AO)
- ✅ LLM Service : analyse Claude ($0.12/tender, 8s)
- ✅ Celery Pipeline : 6 étapes dont 4 complètes
- ✅ Table `document_embeddings` avec pgvector (Vector 1536)
- ✅ Méthodes async RAG définies

### ❌ État Actuel (Ce qui manque - CRITIQUE)
- ❌ **Méthodes synchrones RAG** pour Celery (toutes async actuellement)
- ❌ **Chunking sémantique** (actuellement word-based basique)
- ❌ **Embeddings non créés** dans pipeline (STEP 2 commenté ligne 300)
- ❌ **Similar tenders non recherchés** (STEP 5 commenté ligne 357)
- ❌ **Endpoint Q&A** absent (`/tenders/{id}/ask`)
- ❌ **Tests validation** (recall@5, latence)

---

## 🏗️ ARCHITECTURE CIBLE

```
📄 PDF → Parser Service → Sections structurées (377 sections)
                                    ↓
                          RAG Service
                            ↓
                    Chunking Sémantique
                    (1 section = 1 chunk si <1000 tokens)
                            ↓
                    OpenAI text-embedding-3-small
                            ↓
                    PostgreSQL + pgvector (1536 dim)
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
    Celery Pipeline                      Endpoint /ask
    (auto-ingestion)                     (Q&A + cache)
        ↓                                       ↓
    Similar Tenders              Claude + RAG Context → Answer
                                                ↓
                                        Citations sources
```

---

## 🚀 JOUR 1 - Backend RAG Core (6-8h)

### **TÂCHE 1.1 - Méthodes Synchrones pour Celery** (2-3h)

**Objectif** : Créer versions sync de toutes les méthodes RAG pour Celery

#### 📁 Fichier: `backend/app/services/rag_service.py`

**1.1.1 - Ajouter client OpenAI synchrone**

```python
from openai import OpenAI  # Client sync
import openai  # Pour async
from tenacity import retry, stop_after_attempt, wait_exponential

class RAGService:
    def __init__(self):
        # Existing async client
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key

        # NEW: Sync client for Celery
        self.sync_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

        self.embedding_model = settings.embedding_model
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
```

**1.1.2 - Créer `create_embedding_sync()`**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def create_embedding_sync(self, text: str) -> List[float]:
    """
    Create embedding vector for text (SYNC version for Celery).

    Args:
        text: Text to embed (max ~8000 tokens)

    Returns:
        Embedding vector (1536 dimensions)
    """
    if not self.sync_client:
        raise ValueError("OpenAI API key not configured")

    try:
        response = self.sync_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ OpenAI embedding error: {e}")
        raise
```

**1.1.3 - Créer `ingest_document_sync()`**

```python
def ingest_document_sync(
    self,
    db: Session,  # Sync session
    document_id: UUID,
    chunks: List[Dict[str, Any]],
    document_type: str,
    metadata: Dict[str, Any] | None = None
) -> int:
    """
    Ingest document chunks into vector DB (SYNC).

    Args:
        db: Sync database session
        document_id: Document UUID
        chunks: Pre-chunked sections with metadata
        document_type: Type (tender, proposal, etc.)
        metadata: Additional metadata

    Returns:
        Number of chunks ingested
    """
    from app.models.document import DocumentEmbedding

    metadata = metadata or {}
    count = 0
    batch = []

    print(f"  📦 Creating embeddings for {len(chunks)} chunks...")

    for chunk_data in chunks:
        # Create embedding
        embedding = self.create_embedding_sync(chunk_data["text"])

        # Prepare record
        doc_embedding = DocumentEmbedding(
            document_id=document_id,
            document_type=document_type,
            chunk_text=chunk_data["text"],
            embedding=embedding,
            meta_data={
                **metadata,
                **chunk_data.get("metadata", {}),
                "chunk_index": count,
                "total_chunks": len(chunks)
            }
        )

        batch.append(doc_embedding)
        count += 1

        # Batch insert every 100 chunks
        if len(batch) >= 100:
            db.bulk_save_objects(batch)
            db.commit()
            print(f"    ✓ {count}/{len(chunks)} chunks...")
            batch = []

    # Insert remaining
    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    print(f"  ✅ Ingested {count} chunks")
    return count
```

**1.1.4 - Créer `retrieve_relevant_content_sync()`**

```python
def retrieve_relevant_content_sync(
    self,
    db: Session,
    query: str,
    top_k: int = 5,
    document_ids: List[str] | None = None,
    document_types: List[str] | None = None
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant content using semantic search (SYNC).

    Args:
        db: Sync database session
        query: Search query
        top_k: Number of results
        document_ids: Filter by specific document IDs
        document_types: Filter by types

    Returns:
        List of relevant chunks with similarity scores
    """
    from sqlalchemy import text

    # Create query embedding
    query_embedding = self.create_embedding_sync(query)

    # Build SQL filters
    filters = []

    if document_ids:
        ids_str = ", ".join([f"'{id}'" for id in document_ids])
        filters.append(f"document_id IN ({ids_str})")

    if document_types:
        types_str = ", ".join([f"'{t}'" for t in document_types])
        filters.append(f"document_type IN ({types_str})")

    where_clause = " AND ".join(filters) if filters else "1=1"

    # Execute vector search
    sql = text(f"""
        SELECT
            id,
            document_id,
            document_type,
            chunk_text,
            meta_data,
            1 - (embedding <=> :query_embedding::vector) as similarity
        FROM document_embeddings
        WHERE {where_clause}
        ORDER BY embedding <=> :query_embedding::vector
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query_embedding": query_embedding,
            "top_k": top_k
        }
    )

    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "document_id": str(row.document_id),
            "document_type": row.document_type,
            "chunk_text": row.chunk_text,
            "similarity_score": float(row.similarity),
            "metadata": row.meta_data
        }
        for row in rows
    ]
```

**1.1.5 - Créer `find_similar_tenders_sync()`**

```python
def find_similar_tenders_sync(
    self,
    db: Session,
    tender_id: UUID,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find similar past tenders (SYNC).

    Uses first document of tender as representative for similarity.

    Args:
        db: Sync database session
        tender_id: Current tender ID
        limit: Number of similar tenders

    Returns:
        List of similar tenders with avg similarity
    """
    from sqlalchemy import select, text
    from app.models.document import DocumentEmbedding
    from app.models.tender_document import TenderDocument

    # Get first document ID of tender
    stmt = select(TenderDocument.id).where(
        TenderDocument.tender_id == tender_id
    ).limit(1)

    result = db.execute(stmt)
    first_doc = result.scalar_one_or_none()

    if not first_doc:
        return []

    # Get first embedding of this document
    stmt = select(DocumentEmbedding.embedding).where(
        DocumentEmbedding.document_id == first_doc
    ).limit(1)

    result = db.execute(stmt)
    current_embedding = result.scalar_one_or_none()

    if not current_embedding:
        return []

    # Find similar tenders by avg embedding similarity
    sql = text("""
        SELECT DISTINCT
            td.tender_id,
            AVG(1 - (de.embedding <=> :query_embedding::vector)) as avg_similarity
        FROM document_embeddings de
        JOIN tender_documents td ON td.id = de.document_id
        WHERE td.tender_id != :current_tender_id
        GROUP BY td.tender_id
        ORDER BY avg_similarity DESC
        LIMIT :limit
    """)

    result = db.execute(
        sql,
        {
            "query_embedding": current_embedding.embedding,
            "current_tender_id": str(tender_id),
            "limit": limit
        }
    )

    rows = result.fetchall()

    return [
        {
            "tender_id": str(row.tender_id),
            "similarity_score": float(row.avg_similarity)
        }
        for row in rows
    ]
```

**✅ Livrable 1.1** : 5 nouvelles méthodes synchrones dans `rag_service.py`

---

### **TÂCHE 1.2 - Chunking Sémantique Basé Sections** (2-3h)

**Objectif** : Chunking intelligent préservant la structure et le contexte

#### 📁 Fichier: `backend/app/services/rag_service.py`

**1.2.1 - Créer `chunk_sections_semantic()`**

```python
def chunk_sections_semantic(
    self,
    sections: List[Dict[str, Any]],
    max_tokens: int = 1000,
    min_tokens: int = 100
) -> List[Dict[str, Any]]:
    """
    Semantic chunking based on structured sections from parser.

    Strategy:
    1. Filter TOC sections (skip)
    2. Small sections (<100 tokens): Merge with next if possible
    3. Medium sections (100-1000 tokens): Keep as-is (1 section = 1 chunk)
    4. Large sections (>1000 tokens): Split with 200 token overlap

    Args:
        sections: List of section dicts from DocumentSection
        max_tokens: Max tokens per chunk (default 1000)
        min_tokens: Min tokens for standalone chunk (default 100)

    Returns:
        List of chunks with text + rich metadata
    """
    chunks = []

    # Filter TOC sections
    content_sections = [s for s in sections if not s.get("is_toc", False)]

    # Sort by page and line
    content_sections.sort(key=lambda s: (s.get("page", 0), s.get("line", 0)))

    i = 0
    while i < len(content_sections):
        section = content_sections[i]

        # Build section text
        section_number = section.get("section_number", "")
        title = section.get("title", "")
        content = section.get("content", "")

        section_text = f"Section {section_number}: {title}\n\n{content}" if section_number else f"{title}\n\n{content}"

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(section_text) // 4

        if estimated_tokens < min_tokens and i + 1 < len(content_sections):
            # SMALL: Try merge with next
            next_section = content_sections[i + 1]
            next_num = next_section.get("section_number", "")
            next_title = next_section.get("title", "")
            next_content = next_section.get("content", "")
            next_text = f"Section {next_num}: {next_title}\n\n{next_content}" if next_num else f"{next_title}\n\n{next_content}"

            merged_text = section_text + "\n\n" + next_text

            if len(merged_text) // 4 <= max_tokens:
                # Merge successful
                chunks.append({
                    "text": merged_text,
                    "metadata": {
                        "section_numbers": [section.get("section_number"), next_section.get("section_number")],
                        "pages": list(set([section.get("page"), next_section.get("page")])),
                        "is_key_section": section.get("is_key_section") or next_section.get("is_key_section"),
                        "is_merged": True
                    }
                })
                i += 2
                continue

        if estimated_tokens <= max_tokens:
            # MEDIUM: Keep as-is
            chunks.append({
                "text": section_text,
                "metadata": {
                    "section_number": section.get("section_number"),
                    "page": section.get("page"),
                    "is_key_section": section.get("is_key_section", False),
                    "parent_number": section.get("parent_number"),
                    "level": section.get("level", 1)
                }
            })
        else:
            # LARGE: Split with overlap
            words = section_text.split()
            chunk_size_words = (max_tokens * 4)  # Approx words
            overlap_words = (self.chunk_overlap * 4) // 4  # 200 tokens default

            part = 0
            for j in range(0, len(words), chunk_size_words - overlap_words):
                chunk_words = words[j:j + chunk_size_words]
                chunk_text = " ".join(chunk_words)

                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "section_number": section.get("section_number"),
                        "page": section.get("page"),
                        "is_key_section": section.get("is_key_section", False),
                        "chunk_part": part,
                        "is_split": True
                    }
                })
                part += 1

        i += 1

    print(f"  📦 Semantic chunking: {len(content_sections)} sections → {len(chunks)} chunks")

    return chunks
```

**✅ Livrable 1.2** : Méthode chunking sémantique dans `rag_service.py`

---

### **TÂCHE 1.3 - Tests Unitaires RAG Core** (2h)

**Objectif** : Valider les nouvelles méthodes avec tests

#### 📁 Fichier: `backend/tests/test_rag_service.py`

```python
"""Tests for RAG Service."""
import pytest
from uuid import uuid4
from app.services.rag_service import rag_service
from app.models.base import get_celery_session


class TestRAGServiceSync:
    """Test suite for sync RAG methods."""

    def test_create_embedding_sync(self):
        """Test sync embedding creation."""
        text = "Quels sont les critères d'évaluation ?"

        embedding = rag_service.create_embedding_sync(text)

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        print(f"✅ Embedding: {len(embedding)} dimensions")

    def test_chunk_sections_semantic(self):
        """Test semantic chunking."""
        sections = [
            {
                "section_number": "1",
                "title": "Introduction",
                "content": "Courte intro.",
                "page": 1,
                "is_toc": False,
                "is_key_section": False
            },
            {
                "section_number": "2",
                "title": "Critères",
                "content": "Technique 60%, prix 40%.",
                "page": 2,
                "is_toc": False,
                "is_key_section": True
            }
        ]

        chunks = rag_service.chunk_sections_semantic(sections)

        assert len(chunks) >= 1
        assert "text" in chunks[0]
        assert "metadata" in chunks[0]
        print(f"✅ Chunks: {len(chunks)}")

    def test_ingest_and_retrieve(self):
        """Test E2E ingestion and retrieval."""
        db = get_celery_session()

        try:
            test_doc_id = uuid4()
            chunks = [
                {
                    "text": "Critères: technique 60%, financier 40%.",
                    "metadata": {"section_number": "4.1", "is_key_section": True}
                }
            ]

            # Ingest
            count = rag_service.ingest_document_sync(
                db=db,
                document_id=test_doc_id,
                chunks=chunks,
                document_type="tender"
            )

            assert count == 1

            # Retrieve
            results = rag_service.retrieve_relevant_content_sync(
                db=db,
                query="critères d'évaluation",
                top_k=1
            )

            assert len(results) >= 1
            assert results[0]["similarity_score"] > 0.5
            print(f"✅ Top similarity: {results[0]['similarity_score']:.2f}")

            # Cleanup
            from app.models.document import DocumentEmbedding
            db.query(DocumentEmbedding).filter_by(document_id=test_doc_id).delete()
            db.commit()

        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**✅ Livrable 1.3** : Suite tests unitaires `test_rag_service.py`

---

## 🚀 JOUR 2 - Intégration + Endpoint Q&A (6-8h)

### **TÂCHE 2.1 - Intégration Pipeline Celery** (2-3h)

**Objectif** : Compléter STEP 2 et STEP 5 du pipeline

#### 📁 Fichier: `backend/app/tasks/tender_tasks.py`

**2.1.1 - Compléter STEP 2: Create embeddings** (ligne 300)

```python
# STEP 2: Create embeddings
print(f"🔍 Step 2/6: Creating embeddings")

from app.models.document_section import DocumentSection

total_chunks = 0

for doc in documents:
    # Load sections from DB
    sections_query = db.query(DocumentSection).filter_by(
        document_id=doc.id,
        is_toc=False
    ).all()

    if not sections_query:
        print(f"  ⚠️  No sections for {doc.filename}")
        continue

    # Convert to dicts
    sections_data = [
        {
            "section_number": s.section_number,
            "title": s.title,
            "content": s.content or "",
            "page": s.page,
            "is_key_section": s.is_key_section,
            "parent_number": s.parent_number,
            "level": s.level,
            "is_toc": s.is_toc
        }
        for s in sections_query
    ]

    # Semantic chunking
    chunks = rag_service.chunk_sections_semantic(
        sections=sections_data,
        max_tokens=1000,
        min_tokens=100
    )

    # Ingest
    try:
        count = rag_service.ingest_document_sync(
            db=db,
            document_id=doc.id,
            chunks=chunks,
            document_type="tender",
            metadata={
                "tender_id": str(tender_id),
                "filename": doc.filename
            }
        )
        total_chunks += count
        print(f"  ✓ {doc.filename}: {len(sections_data)} sections → {count} chunks")
    except Exception as e:
        print(f"  ❌ Embeddings failed for {doc.filename}: {e}")

print(f"  ✓ Total: {total_chunks} chunks")
```

**2.1.2 - Compléter STEP 5: Similar tenders** (ligne 357)

```python
# STEP 5: Find similar tenders
print(f"🔎 Step 5/6: Finding similar tenders")

try:
    similar = rag_service.find_similar_tenders_sync(
        db=db,
        tender_id=tender_id,
        limit=5
    )

    analysis.similar_tenders = similar
    print(f"  ✓ Found {len(similar)} similar tenders")

    if similar:
        top = similar[0]
        print(f"  Top: {top['tender_id']} (score: {top['similarity_score']:.2f})")

except Exception as e:
    print(f"  ⚠️  Similar search failed: {e}")
    analysis.similar_tenders = []
```

**2.1.3 - Ajouter champ `similar_tenders` au modèle**

#### 📁 Fichier: `backend/app/models/tender_analysis.py`

```python
# Add to TenderAnalysis class
similar_tenders = Column(JSON, default=[])
```

**2.1.4 - Créer migration**

```bash
cd backend
alembic revision --autogenerate -m "Add similar_tenders to tender_analysis"
alembic upgrade head
```

**✅ Livrable 2.1** : Pipeline Celery complet avec embeddings automatiques

---

### **TÂCHE 2.2 - Endpoint Q&A avec Cache** (3-4h)

**Objectif** : Créer endpoint `/tenders/{id}/ask` avec RAG + Claude + Cache

#### 📁 Fichier: `backend/app/schemas/search.py`

**2.2.1 - Ajouter schemas Q&A**

```python
class TenderQuestionRequest(BaseModel):
    """Tender Q&A request."""
    question: str = Field(..., min_length=5, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class TenderQuestionResponse(BaseModel):
    """Tender Q&A response."""
    question: str
    answer: str
    sources: List[SearchResult]
    confidence: float = Field(..., ge=0, le=1)
    cached: bool = False
```

#### 📁 Fichier: `backend/app/core/prompts.py`

**2.2.2 - Ajouter prompt Q&A**

```python
TENDER_QA_PROMPT = """Tu es un expert en appels d'offres publics français.

QUESTION :
{question}

CONTEXTE (extrait du tender) :
{context}

Réponds précisément en te basant UNIQUEMENT sur le contexte.
Si l'info n'est pas présente, dis "Information non trouvée dans le tender".
Cite les sections sources (numéros)."""
```

#### 📁 Fichier: `backend/app/api/v1/endpoints/tenders.py`

**2.2.3 - Implémenter endpoint**

```python
import hashlib
import json
import redis.asyncio as redis
from app.schemas.search import TenderQuestionRequest, TenderQuestionResponse, SearchResult

@router.post("/{tender_id}/ask", response_model=TenderQuestionResponse)
async def ask_question(
    tender_id: str,
    request: TenderQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Ask question about tender using RAG."""

    # 1. Verify tender
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(404, "Tender not found")

    # 2. Check cache
    redis_client = await redis.from_url(settings.redis_url)
    q_hash = hashlib.sha256(request.question.encode()).hexdigest()[:16]
    cache_key = f"tender_qa:{tender_id}:{q_hash}"

    cached = await redis_client.get(cache_key)
    if cached:
        return TenderQuestionResponse(**json.loads(cached), cached=True)

    # 3. Get document IDs
    from app.models.tender_document import TenderDocument
    stmt = select(TenderDocument.id).where(TenderDocument.tender_id == tender_id)
    result = await db.execute(stmt)
    doc_ids = [str(r[0]) for r in result.fetchall()]

    if not doc_ids:
        raise HTTPException(404, "No documents for this tender")

    # 4. RAG search
    from sqlalchemy import text

    query_emb = await rag_service.create_embedding(request.question)

    sql = text("""
        SELECT id, document_id, chunk_text, meta_data,
               1 - (embedding <=> :emb::vector) as similarity
        FROM document_embeddings
        WHERE document_id = ANY(:doc_ids)
        ORDER BY embedding <=> :emb::vector
        LIMIT :k
    """)

    result = await db.execute(sql, {
        "emb": query_emb,
        "doc_ids": doc_ids,
        "k": request.top_k
    })

    rows = result.fetchall()

    if not rows:
        raise HTTPException(404, "No embeddings found")

    # 5. Build context
    sources = []
    context_parts = []

    for row in rows:
        sources.append(SearchResult(
            document_id=str(row.document_id),
            document_type="tender",
            chunk_text=row.chunk_text,
            similarity_score=float(row.similarity),
            metadata=row.meta_data
        ))

        section = row.meta_data.get("section_number", "?")
        context_parts.append(f"[Section {section}]\n{row.chunk_text}")

    context = "\n\n".join(context_parts)

    # 6. Claude answer
    from app.core.prompts import TENDER_QA_PROMPT

    prompt = TENDER_QA_PROMPT.format(
        question=request.question,
        context=context
    )

    response = await llm_service.client.messages.create(
        model=llm_service.model,
        max_tokens=1000,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = response.content[0].text

    # 7. Calculate confidence
    top_sims = [s.similarity_score for s in sources[:3]]
    confidence = sum(top_sims) / len(top_sims) if top_sims else 0.0

    # 8. Response
    qa_response = TenderQuestionResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        confidence=confidence,
        cached=False
    )

    # 9. Cache (1h)
    await redis_client.setex(
        cache_key,
        3600,
        json.dumps(qa_response.model_dump(exclude={"cached"}))
    )

    return qa_response
```

**✅ Livrable 2.2** : Endpoint Q&A fonctionnel avec cache Redis

---

## 🚀 JOUR 3 - Tests et Validation (4-6h)

### **TÂCHE 3.1 - Test E2E sur VSGP-AO** (2-3h)

**Objectif** : Valider recall@5 > 80% sur questions réelles

#### 📁 Fichier: `scripts/tests/test_rag_e2e_vsgp.py`

```python
"""E2E RAG validation on VSGP-AO."""
import time
from sqlalchemy import select
from app.models.base import get_celery_session
from app.models.tender import Tender
from app.services.rag_service import rag_service


def test_rag_recall():
    """Validate recall@5 on VSGP-AO."""

    db = get_celery_session()

    # Load VSGP-AO
    stmt = select(Tender).where(Tender.title.like('%VSGP%'))
    result = db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        print("❌ VSGP-AO not found")
        return

    print(f"📄 Testing: {tender.title}\n")

    # Get doc IDs
    from app.models.tender_document import TenderDocument
    stmt = select(TenderDocument.id).where(TenderDocument.tender_id == tender.id)
    result = db.execute(stmt)
    doc_ids = [str(r[0]) for r in result.fetchall()]

    # Test cases
    test_cases = [
        {
            "question": "Quels sont les délais de remise ?",
            "expected_sections": ["2.3", "3.1"],
            "keywords": ["date limite", "remise"]
        },
        {
            "question": "Certifications obligatoires ?",
            "expected_sections": ["4.2"],
            "keywords": ["ISO", "certification"]
        },
        {
            "question": "Critères d'évaluation ?",
            "expected_sections": ["6.1"],
            "keywords": ["critère", "pondération"]
        },
        {
            "question": "Pénalités prévues ?",
            "expected_sections": ["7.3"],
            "keywords": ["pénalité"]
        },
        {
            "question": "Processus incidents ?",
            "expected_sections": ["8.2"],
            "keywords": ["incident", "processus"]
        }
    ]

    results = []

    for i, tc in enumerate(test_cases, 1):
        print(f"Test {i}/5: {tc['question']}")

        start = time.time()

        search_results = rag_service.retrieve_relevant_content_sync(
            db=db,
            query=tc["question"],
            top_k=5,
            document_ids=doc_ids
        )

        latency = time.time() - start

        # Recall
        retrieved = {r["metadata"].get("section_number") for r in search_results}
        expected = set(tc["expected_sections"])
        recall = len(retrieved & expected) / len(expected) if expected else 0

        # Keywords
        all_text = " ".join([r["chunk_text"].lower() for r in search_results])
        kw_found = sum(1 for kw in tc["keywords"] if kw.lower() in all_text)
        kw_coverage = kw_found / len(tc["keywords"])

        print(f"  ⏱️  {latency:.2f}s")
        print(f"  📊 Recall: {recall:.0%}")
        print(f"  🔑 Keywords: {kw_coverage:.0%}")
        print(f"  💯 Top sim: {search_results[0]['similarity_score']:.3f}\n")

        results.append({
            "recall": recall,
            "latency": latency,
            "kw_coverage": kw_coverage
        })

    # Aggregate
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_latency = sum(r["latency"] for r in results) / len(results)

    print("="*60)
    print(f"📊 FINAL METRICS")
    print(f"  Recall@5: {avg_recall:.1%} (target: >80%)")
    print(f"  Latency: {avg_latency:.2f}s (target: <2s)")

    assert avg_recall >= 0.80
    assert avg_latency <= 2.0

    print("\n✅ VALIDATION PASSED")

    db.close()


if __name__ == "__main__":
    test_rag_recall()
```

**✅ Livrable 3.1** : Script validation E2E avec métriques

---

### **TÂCHE 3.2 - Analyse Coûts** (1h)

#### 📁 Fichier: `scripts/tests/test_rag_cost.py`

```python
"""Analyze RAG costs."""
from app.models.base import get_celery_session
from app.models.document import DocumentEmbedding
from sqlalchemy import func


def analyze_costs():
    """Calculate embedding costs."""

    db = get_celery_session()

    # Count embeddings
    total = db.query(func.count(DocumentEmbedding.id)).scalar()

    # Cost calc
    # text-embedding-3-small: $0.00002 per 1K tokens
    # Avg 200 tokens/embedding
    tokens = total * 200
    cost = (tokens / 1000) * 0.00002

    print(f"📊 EMBEDDING STATS")
    print(f"  Total: {total:,}")
    print(f"  Est. tokens: {tokens:,}")
    print(f"  Cost: ${cost:.4f}")

    # Per tender
    from app.models.tender import Tender
    tenders = db.query(func.count(Tender.id)).scalar()
    cost_per = cost / tenders if tenders else 0

    print(f"  Tenders: {tenders}")
    print(f"  Cost/tender: ${cost_per:.4f} (target: <$0.02)")

    assert cost_per < 0.02

    print("\n✅ COST VALIDATION PASSED")

    db.close()


if __name__ == "__main__":
    analyze_costs()
```

**✅ Livrable 3.2** : Analyse coûts

---

### **TÂCHE 3.3 - Compléter Endpoints Search** (1-2h)

#### 📁 Fichier: `backend/app/api/v1/endpoints/search.py`

```python
@router.post("/", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Semantic search in knowledge base."""

    results = await rag_service.retrieve_relevant_content(
        db=db,
        query=request.query,
        top_k=request.limit,
        document_types=request.document_types
    )

    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results],
        total=len(results)
    )


@router.get("/similar-tenders/{tender_id}")
async def find_similar(
    tender_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Find similar tenders."""

    similar = await rag_service.find_similar_tenders(
        db=db,
        tender_id=tender_id,
        limit=limit
    )

    return {
        "tender_id": tender_id,
        "similar_tenders": similar
    }
```

**✅ Livrable 3.3** : Endpoints search complétés

---

## 📊 LIVRABLES FINAUX

### Code
1. ✅ `rag_service.py` : 6 méthodes sync + chunking sémantique
2. ✅ `tender_tasks.py` : STEP 2 & 5 complétés
3. ✅ `tenders.py` : Endpoint `/ask` avec cache
4. ✅ `prompts.py` : Prompt Q&A
5. ✅ `search.py` : Endpoints complétés
6. ✅ Migration : `similar_tenders` ajouté

### Tests
7. ✅ `test_rag_service.py` : Tests unitaires
8. ✅ `test_rag_e2e_vsgp.py` : Validation E2E
9. ✅ `test_rag_cost.py` : Analyse coûts

---

## 🎯 CRITÈRES DE SUCCÈS

- ✅ Pipeline crée embeddings automatiquement
- ✅ Endpoint `/ask` répond <3s
- ✅ Recall@5 > 80% sur VSGP-AO
- ✅ Cache hit rate >30%
- ✅ Coût <$0.02/tender
- ✅ Tests coverage >80%
- ✅ Latence <2s

---

## 🚀 COMMANDES

```bash
# Infrastructure
docker-compose up -d postgres redis

# Migration
cd backend
alembic upgrade head

# Tests
pytest backend/tests/test_rag_service.py -v
python scripts/tests/test_rag_e2e_vsgp.py
python scripts/tests/test_rag_cost.py

# API
uvicorn app.main:app --reload

# Celery
celery -A app.tasks.celery_app worker --loglevel=info
```

---

**Prêt à démarrer ? 🚀**
