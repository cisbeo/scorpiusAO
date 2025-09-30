"""
AI analysis endpoints.
"""
from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.schemas.analysis import AnalysisResponse, CriteriaExtractionResponse

router = APIRouter()


@router.get("/tenders/{tender_id}", response_model=AnalysisResponse)
async def get_tender_analysis(tender_id: UUID):
    """
    Get AI analysis results for a tender.
    """
    # TODO: Retrieve analysis from database
    raise HTTPException(status_code=404, detail="Analysis not found")


@router.get("/tenders/{tender_id}/criteria", response_model=CriteriaExtractionResponse)
async def get_tender_criteria(tender_id: UUID):
    """
    Get extracted criteria from tender document.
    """
    # TODO: Retrieve criteria extraction results
    raise HTTPException(status_code=404, detail="Criteria not found")


@router.post("/tenders/{tender_id}/reanalyze", status_code=202)
async def reanalyze_tender(tender_id: UUID):
    """
    Trigger re-analysis of a tender.
    """
    # TODO: Queue re-analysis task
    return {"message": "Re-analysis queued", "tender_id": str(tender_id)}
