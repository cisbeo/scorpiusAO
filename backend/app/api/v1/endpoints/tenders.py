"""
Tender management endpoints.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.tender import TenderCreate, TenderResponse, TenderList
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
