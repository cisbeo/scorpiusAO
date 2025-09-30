"""
Tender document management endpoints.
"""
import os
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.base import get_db
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.schemas.tender_document import TenderDocumentResponse, TenderDocumentWithContent
from app.tasks.tender_tasks import process_tender_document
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/{tender_id}/documents/upload", response_model=TenderDocumentResponse, status_code=201)
async def upload_document(
    tender_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for a tender.

    Args:
        tender_id: UUID of the tender
        file: PDF file to upload
        document_type: Type of document (CCTP, RC, AE, BPU, DUME, ANNEXE)
    """
    # Verify tender exists
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate document type
    valid_types = ["CCTP", "RC", "AE", "BPU", "DUME", "ANNEXE"]
    if document_type.upper() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Upload to MinIO
    file_id = str(uuid.uuid4())
    file_path = f"tenders/{tender_id}/documents/{file_id}_{file.filename}"

    try:
        storage_service.upload_file(
            file_content=content,
            object_name=file_path,
            content_type=file.content_type or "application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # Create document record
    document = TenderDocument(
        tender_id=tender_id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        document_type=document_type.upper(),
        extraction_status="pending"
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Trigger async processing
    print(f"🚀 Triggering async document processing for document {document.id}")
    task = process_tender_document.delay(str(document.id))
    print(f"✅ Task queued: {task.id}")

    return document


@router.get("/{tender_id}/documents", response_model=List[TenderDocumentResponse])
async def list_documents(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    List all documents for a tender.
    """
    # Verify tender exists
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Get documents
    stmt = select(TenderDocument).where(TenderDocument.tender_id == tender_id)
    result = await db.execute(stmt)
    documents = result.scalars().all()

    return documents


@router.get("/{tender_id}/documents/{document_id}", response_model=TenderDocumentWithContent)
async def get_document(
    tender_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific document with its extracted content.
    """
    stmt = select(TenderDocument).where(
        TenderDocument.id == document_id,
        TenderDocument.tender_id == tender_id
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.delete("/{tender_id}/documents/{document_id}", status_code=204)
async def delete_document(
    tender_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document.
    """
    stmt = select(TenderDocument).where(
        TenderDocument.id == document_id,
        TenderDocument.tender_id == tender_id
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # TODO: Delete file from MinIO

    await db.delete(document)
    await db.commit()


@router.post("/{tender_id}/analyze", status_code=202)
async def analyze_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger analysis of all tender documents.
    """
    # Verify tender exists
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Check if documents exist
    stmt = select(TenderDocument).where(TenderDocument.tender_id == tender_id)
    result = await db.execute(stmt)
    documents = result.scalars().all()

    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No documents found for this tender. Please upload documents first."
        )

    # Update tender status
    tender.status = "processing"
    await db.commit()

    # Trigger async analysis
    from app.tasks.tender_tasks import process_tender_documents
    process_tender_documents.delay(tender_id)

    return {
        "message": "Analysis started",
        "tender_id": tender_id,
        "document_count": len(documents)
    }
