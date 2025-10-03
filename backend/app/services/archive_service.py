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
            meta_data={
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
            our_company_name=getattr(settings, 'company_name', "ScorpiusAO Client"),
            status=proposal_status,
            score_obtained=score_obtained,
            max_score=Decimal("100.00"),
            rank=rank,
            total_bidders=total_bidders,
            sections=proposal.sections,
            lessons_learned=lessons_learned or "",
            win_factors=win_factors or [],
            improvement_areas=improvement_areas or [],
            meta_data={
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
