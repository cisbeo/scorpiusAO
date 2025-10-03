"""
Archive endpoints - Archive tenders and proposals to historical tables.
"""
from typing import Optional
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.models.base import get_db
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
