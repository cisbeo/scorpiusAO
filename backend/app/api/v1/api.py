"""
API v1 router aggregation.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    tenders,
    analysis,
    documents,
    proposals,
    search,
    tender_documents,
    tender_analysis,
    archive
)

api_router = APIRouter()

api_router.include_router(
    tenders.router,
    prefix="/tenders",
    tags=["tenders"]
)

# Tender-specific routes (documents and analysis)
api_router.include_router(
    tender_documents.router,
    prefix="/tenders",
    tags=["tender-documents"]
)

api_router.include_router(
    tender_analysis.router,
    prefix="/tenders",
    tags=["tender-analysis"]
)

api_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["analysis"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

api_router.include_router(
    proposals.router,
    prefix="/proposals",
    tags=["proposals"]
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search"]
)

api_router.include_router(
    archive.router,
    prefix="/archive",
    tags=["archive"]
)
