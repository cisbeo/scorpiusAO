"""
SQLAlchemy models.
"""
from app.models.base import Base
from app.models.tender import Tender, TenderCriterion
from app.models.tender_document import TenderDocument
from app.models.document_section import DocumentSection
from app.models.tender_analysis import TenderAnalysis
from app.models.similar_tender import SimilarTender

# Historical models for RAG Knowledge Base
from app.models.historical_tender import HistoricalTender
from app.models.past_proposal import PastProposal

__all__ = [
    "Base",
    "Tender",
    "TenderCriterion",
    "TenderDocument",
    "DocumentSection",
    "TenderAnalysis",
    "SimilarTender",
    # Historical models
    "HistoricalTender",
    "PastProposal",
]
