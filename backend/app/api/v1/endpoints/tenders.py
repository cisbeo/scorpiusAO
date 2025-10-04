"""
Tender management endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.tender import TenderCreate, TenderResponse, TenderList
from app.schemas.search import TenderQuestionRequest, TenderQuestionResponse
from app.models.tender import Tender
from app.models.base import get_db

router = APIRouter()


@router.post("/", response_model=TenderResponse, status_code=201)
async def create_tender(
    tender: TenderCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new tender in the database.
    """
    # Create tender record
    new_tender = Tender(
        title=tender.title,
        organization=tender.organization,
        reference_number=tender.reference_number,
        deadline=tender.deadline,
        raw_content=tender.raw_content,
        source=tender.source,
        status="new"
    )

    db.add(new_tender)
    await db.commit()
    await db.refresh(new_tender)

    return new_tender


@router.post("/upload", response_model=TenderResponse, status_code=201)
async def upload_tender_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload a tender document (PDF) and create tender from it.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # TODO: Implement document upload and parsing
    # 1. Save file to MinIO
    # 2. Extract text and metadata
    # 3. Create tender record
    # 4. Trigger async analysis

    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "title": file.filename,
        "status": "processing",
        "message": "Document uploaded successfully"
    }


@router.get("/", response_model=List[TenderList])
async def list_tenders(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all tenders with optional filtering.
    """
    query = select(Tender)

    if status:
        query = query.where(Tender.status == status)

    query = query.offset(skip).limit(limit).order_by(Tender.created_at.desc())

    result = await db.execute(query)
    tenders = result.scalars().all()

    return tenders


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(tender_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a specific tender by ID.
    """
    result = await db.execute(select(Tender).where(Tender.id == tender_id))
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    return tender


@router.delete("/{tender_id}", status_code=204)
async def delete_tender(tender_id: UUID):
    """
    Delete a tender and all associated data.
    """
    # TODO: Implement tender deletion
    pass


@router.post("/{tender_id}/ask", response_model=TenderQuestionResponse)
async def ask_question_about_tender(
    tender_id: str,
    request: TenderQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about a specific tender using RAG.

    Returns answer with source citations.
    """
    import hashlib
    import json
    import redis.asyncio as redis
    from sqlalchemy import text
    from app.schemas.search import SearchResult
    from app.services.rag_service import rag_service
    from app.services.llm_service import llm_service
    from app.core.prompts import TENDER_QA_PROMPT
    from app.core.config import settings

    # 1. Verify tender exists
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # 2. Check Redis cache
    redis_client = await redis.from_url(settings.redis_url)
    q_hash = hashlib.sha256(request.question.encode()).hexdigest()[:16]
    cache_key = f"tender_qa:{tender_id}:{q_hash}"

    cached = await redis_client.get(cache_key)
    if cached:
        return TenderQuestionResponse(**json.loads(cached), cached=True)

    # 3. Get document IDs for this tender
    from app.models.tender_document import TenderDocument
    stmt = select(TenderDocument.id).where(TenderDocument.tender_id == tender_id)
    result = await db.execute(stmt)
    doc_ids = [str(r[0]) for r in result.fetchall()]

    if not doc_ids:
        raise HTTPException(
            status_code=404,
            detail="No documents found for this tender"
        )

    # 4. RAG search for relevant chunks
    query_emb = await rag_service.create_embedding(request.question)

    # Build SQL with proper parameter binding for asyncpg (enriched with document filename)
    from sqlalchemy import bindparam
    sql = text("""
        SELECT
            de.id,
            de.document_id,
            de.document_type,
            de.chunk_text,
            de.meta_data,
            1 - (de.embedding <=> CAST(:emb AS vector)) as similarity,
            td.filename as document_filename,
            td.document_type as document_type_full
        FROM document_embeddings de
        LEFT JOIN tender_documents td ON de.document_id = td.id
        WHERE de.document_id = ANY(CAST(:doc_ids AS uuid[]))
        ORDER BY de.embedding <=> CAST(:emb AS vector)
        LIMIT :k
    """).bindparams(
        bindparam("emb", type_=None),
        bindparam("doc_ids", type_=None),
        bindparam("k", type_=None)
    )

    result = await db.execute(sql, {
        "emb": str(query_emb),
        "doc_ids": [str(d) for d in doc_ids],
        "k": request.top_k
    })

    rows = result.fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No embeddings found for this tender. The tender may not have been processed yet."
        )

    # 5. Build context from chunks
    sources = []
    context_parts = []

    for row in rows:
        # Enrich metadata with document filename
        enriched_metadata = row.meta_data.copy() if row.meta_data else {}
        enriched_metadata["document_filename"] = row.document_filename or "Unknown"
        enriched_metadata["document_type_full"] = row.document_type_full or row.document_type

        sources.append(SearchResult(
            document_id=str(row.document_id),
            document_type=row.document_type,
            chunk_text=row.chunk_text,
            similarity_score=float(row.similarity),
            metadata=enriched_metadata
        ))

        section = enriched_metadata.get("section_number", "?")
        page = enriched_metadata.get("page", "?")
        filename = row.document_filename or "Document inconnu"
        context_parts.append(f"[{filename} - Section {section}, Page {page}]\n{row.chunk_text}")

    context = "\n\n".join(context_parts)

    # 6. Generate answer with Claude
    prompt = TENDER_QA_PROMPT.format(
        question=request.question,
        context=context
    )

    print(f"🤖 Calling Claude for Q&A (context: {len(context)} chars)...")

    response = await llm_service.client.messages.create(
        model=llm_service.model,
        max_tokens=1000,
        temperature=0.3,  # Lower temp for factual answers
        messages=[{"role": "user", "content": prompt}]
    )

    answer = response.content[0].text

    # 7. Calculate confidence (avg similarity of top-3)
    top_sims = [s.similarity_score for s in sources[:3]]
    confidence = sum(top_sims) / len(top_sims) if top_sims else 0.0

    # 8. Prepare response
    qa_response = TenderQuestionResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        confidence=confidence,
        cached=False
    )

    # 9. Cache response (1 hour TTL)
    await redis_client.setex(
        cache_key,
        3600,
        json.dumps(qa_response.model_dump(exclude={"cached"}))
    )

    print(f"✅ Q&A completed (confidence: {confidence:.2f}, cached for 1h)")

    return qa_response
