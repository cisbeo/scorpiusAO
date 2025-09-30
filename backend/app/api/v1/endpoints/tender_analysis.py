"""
Tender analysis endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.base import get_db
from app.models.tender import Tender
from app.models.tender_analysis import TenderAnalysis
from app.schemas.tender_analysis import TenderAnalysisResponse, AnalysisStatusResponse

router = APIRouter()


@router.get("/{tender_id}/analysis", response_model=TenderAnalysisResponse)
async def get_analysis(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get analysis results for a tender.
    """
    stmt = select(TenderAnalysis).where(TenderAnalysis.tender_id == tender_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. The tender may not have been analyzed yet."
        )

    return analysis


@router.get("/{tender_id}/analysis/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current status of tender analysis.
    """
    # Get tender
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Get analysis if exists
    stmt = select(TenderAnalysis).where(TenderAnalysis.tender_id == tender_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        # No analysis started yet
        return {
            "tender_id": tender_id,
            "status": "pending",
            "current_step": None,
            "progress": 0,
            "steps_completed": [],
            "estimated_time_remaining": None,
            "error_message": None
        }

    # Calculate progress based on status
    progress_map = {
        "pending": 0,
        "processing": 50,
        "completed": 100,
        "failed": 0
    }

    return {
        "tender_id": tender_id,
        "status": analysis.analysis_status,
        "current_step": None if analysis.analysis_status == "completed" else "processing",
        "progress": progress_map.get(analysis.analysis_status, 0),
        "steps_completed": [],
        "estimated_time_remaining": None if analysis.analysis_status in ["completed", "failed"] else "5-10 minutes",
        "error_message": analysis.error_message if analysis.analysis_status == "failed" else None
    }
