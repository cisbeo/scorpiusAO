"""
API endpoints for BOAMP (Bulletin Officiel des Annonces des Marchés Publics) integration.
"""
from datetime import datetime, timedelta, date
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.boamp_publication import BOAMPPublication
from app.schemas.boamp import (
    BOAMPPublicationResponse,
    BOAMPPublicationList,
    BOAMPSyncRequest,
    BOAMPSyncResponse,
    BOAMPImportRequest,
    BOAMPImportResponse,
    BOAMPStatsResponse,
)
from app.tasks.boamp_tasks import (
    fetch_boamp_publications_task,
    import_boamp_as_tender_task,
)

router = APIRouter()


@router.get("/publications", response_model=BOAMPPublicationList)
async def list_boamp_publications(
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="Filter by status (new, imported, ignored, error)"),
    date_from: Optional[date] = Query(None, description="Filter publications from this date"),
    date_to: Optional[date] = Query(None, description="Filter publications until this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """
    List BOAMP publications with pagination and filters.

    Returns paginated list of BOAMP publications.
    """
    # Build query
    query = select(BOAMPPublication)

    # Apply filters
    filters = []
    if status_filter:
        filters.append(BOAMPPublication.status == status_filter)
    if date_from:
        filters.append(BOAMPPublication.publication_date >= date_from)
    if date_to:
        filters.append(BOAMPPublication.publication_date <= date_to)

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(BOAMPPublication)
    if filters:
        count_query = count_query.where(and_(*filters))

    result = await db.execute(count_query)
    total = result.scalar()

    # Apply pagination
    query = query.order_by(BOAMPPublication.publication_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    publications = result.scalars().all()

    # Convert to response
    items = [BOAMPPublicationResponse.model_validate(pub) for pub in publications]

    return BOAMPPublicationList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total
    )


@router.get("/publications/{publication_id}", response_model=BOAMPPublicationResponse)
async def get_boamp_publication(
    publication_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single BOAMP publication by ID.

    Returns full publication details including raw_data.
    """
    stmt = select(BOAMPPublication).where(BOAMPPublication.id == publication_id)
    result = await db.execute(stmt)
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOAMP publication {publication_id} not found"
        )

    return BOAMPPublicationResponse.model_validate(publication)


@router.post("/publications/{publication_id}/import", response_model=BOAMPImportResponse)
async def import_boamp_publication(
    publication_id: UUID,
    db: AsyncSession = Depends(get_db),
    request: BOAMPImportRequest = BOAMPImportRequest()
):
    """
    Import a BOAMP publication as a Tender.

    Creates a new Tender record from BOAMP publication data and triggers processing pipeline.
    """
    # Check publication exists
    stmt = select(BOAMPPublication).where(BOAMPPublication.id == publication_id)
    result = await db.execute(stmt)
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOAMP publication {publication_id} not found"
        )

    # Check not already imported
    if publication.status == "imported":
        return BOAMPImportResponse(
            status="already_imported",
            tender_id=publication.matched_tender_id,
            message=f"Publication already imported as tender {publication.matched_tender_id}"
        )

    # Trigger async import task
    task = import_boamp_as_tender_task.delay(str(publication_id))

    return BOAMPImportResponse(
        status="processing",
        task_id=task.id,
        message="Import task started. Check task status for completion."
    )


@router.post("/sync", response_model=BOAMPSyncResponse)
async def sync_boamp_publications(
    request: BOAMPSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger BOAMP publications sync.

    Fetches latest publications from BOAMP API and saves them to database.
    Normally runs automatically every hour via Celery Beat.
    """
    # Trigger async fetch task
    task = fetch_boamp_publications_task.delay(
        days_back=request.days_back,
        limit=request.limit
    )

    return BOAMPSyncResponse(
        status="processing",
        task_id=task.id,
        message=f"Sync task started. Fetching publications from last {request.days_back} days."
    )


@router.get("/stats", response_model=BOAMPStatsResponse)
async def get_boamp_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics about BOAMP publications.

    Returns counts by status, recent activity, and aggregate metrics.
    """
    # Total count by status
    stmt = select(
        BOAMPPublication.status,
        func.count(BOAMPPublication.id).label("count")
    ).group_by(BOAMPPublication.status)

    result = await db.execute(stmt)
    status_counts = {row.status: row.count for row in result}

    # Total publications
    total = sum(status_counts.values())

    # Publications in last 24h
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    stmt = select(func.count()).select_from(BOAMPPublication).where(
        BOAMPPublication.created_at >= cutoff_24h
    )
    result = await db.execute(stmt)
    last_24h = result.scalar()

    # Publications in last 7 days
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    stmt = select(func.count()).select_from(BOAMPPublication).where(
        BOAMPPublication.created_at >= cutoff_7d
    )
    result = await db.execute(stmt)
    last_7d = result.scalar()

    # Average days to deadline (for active publications with deadline)
    stmt = select(func.avg(
        func.extract('epoch', BOAMPPublication.deadline - func.current_date()) / 86400
    )).select_from(BOAMPPublication).where(
        and_(
            BOAMPPublication.deadline.isnot(None),
            BOAMPPublication.deadline >= func.current_date(),
            BOAMPPublication.status == 'new'
        )
    )
    result = await db.execute(stmt)
    avg_days = result.scalar()

    # Total contract value (montant)
    stmt = select(func.sum(BOAMPPublication.montant)).select_from(BOAMPPublication)
    result = await db.execute(stmt)
    total_montant = result.scalar()

    return BOAMPStatsResponse(
        total_publications=total,
        new_count=status_counts.get('new', 0),
        imported_count=status_counts.get('imported', 0),
        ignored_count=status_counts.get('ignored', 0),
        error_count=status_counts.get('error', 0),
        publications_last_24h=last_24h,
        publications_last_7d=last_7d,
        avg_days_to_deadline=float(avg_days) if avg_days else None,
        total_montant=float(total_montant) if total_montant else None,
    )


@router.patch("/publications/{publication_id}/ignore")
async def ignore_boamp_publication(
    publication_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a BOAMP publication as ignored.

    Use this for publications that are not relevant and should be hidden.
    """
    stmt = select(BOAMPPublication).where(BOAMPPublication.id == publication_id)
    result = await db.execute(stmt)
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOAMP publication {publication_id} not found"
        )

    publication.status = "ignored"
    await db.commit()

    return {"status": "success", "message": "Publication marked as ignored"}
