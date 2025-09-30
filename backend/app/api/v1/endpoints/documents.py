"""
Document management endpoints.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_documents():
    """List all documents in the knowledge base."""
    # TODO: Implement document listing
    return []


@router.post("/ingest")
async def ingest_document():
    """Ingest a document into the RAG knowledge base."""
    # TODO: Implement document ingestion
    return {"message": "Document ingestion not yet implemented"}
