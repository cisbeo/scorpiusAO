"""
RAG Service for semantic search using pgvector.
"""
from typing import List, Dict, Any
from uuid import UUID
import openai
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import DocumentEmbedding


class RAGService:
    """Service for Retrieval Augmented Generation."""

    def __init__(self):
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
        self.embedding_model = settings.embedding_model
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        response = await openai.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            if chunk:
                chunks.append(chunk)

        return chunks

    async def ingest_document(
        self,
        db: AsyncSession,
        document_id: UUID,
        content: str,
        document_type: str,
        metadata: Dict[str, Any] | None = None
    ) -> int:
        """
        Ingest document into vector database.

        Args:
            db: Database session
            document_id: Unique document identifier
            content: Document content
            document_type: Type of document (tender, proposal, certification, etc.)
            metadata: Additional metadata

        Returns:
            Number of chunks created
        """
        chunks = self.chunk_text(content)
        metadata = metadata or {}

        count = 0
        for idx, chunk in enumerate(chunks):
            embedding = await self.create_embedding(chunk)

            doc_embedding = DocumentEmbedding(
                document_id=document_id,
                document_type=document_type,
                chunk_text=chunk,
                embedding=embedding,
                metadata={
                    **metadata,
                    "chunk_index": idx,
                    "total_chunks": len(chunks)
                }
            )

            db.add(doc_embedding)
            count += 1

        await db.commit()
        return count

    async def retrieve_relevant_content(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        document_types: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant content using semantic search.

        Args:
            db: Database session
            query: Search query
            top_k: Number of results to return
            document_types: Filter by document types

        Returns:
            List of relevant chunks with similarity scores
        """
        query_embedding = await self.create_embedding(query)

        # Build SQL query for cosine similarity search
        type_filter = ""
        if document_types:
            types_str = ", ".join([f"'{t}'" for t in document_types])
            type_filter = f"AND document_type IN ({types_str})"

        sql = text(f"""
            SELECT
                id,
                document_id,
                document_type,
                chunk_text,
                metadata,
                1 - (embedding <=> :query_embedding) as similarity
            FROM document_embeddings
            WHERE 1=1 {type_filter}
            ORDER BY embedding <=> :query_embedding
            LIMIT :top_k
        """)

        result = await db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "top_k": top_k
            }
        )

        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "document_id": str(row.document_id),
                "document_type": row.document_type,
                "chunk_text": row.chunk_text,
                "similarity_score": float(row.similarity),
                "metadata": row.metadata
            }
            for row in rows
        ]

    async def find_similar_tenders(
        self,
        db: AsyncSession,
        tender_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past tenders.

        Args:
            db: Database session
            tender_id: Current tender ID
            limit: Number of similar tenders to return

        Returns:
            List of similar tenders
        """
        # Get current tender's embeddings
        stmt = select(DocumentEmbedding).where(
            DocumentEmbedding.document_id == tender_id,
            DocumentEmbedding.document_type == "tender"
        ).limit(1)

        result = await db.execute(stmt)
        current_embedding = result.scalar_one_or_none()

        if not current_embedding:
            return []

        # Find similar tenders
        sql = text("""
            SELECT DISTINCT
                document_id,
                AVG(1 - (embedding <=> :query_embedding)) as avg_similarity
            FROM document_embeddings
            WHERE document_type = 'tender'
            AND document_id != :current_id
            GROUP BY document_id
            ORDER BY avg_similarity DESC
            LIMIT :limit
        """)

        result = await db.execute(
            sql,
            {
                "query_embedding": str(current_embedding.embedding),
                "current_id": str(tender_id),
                "limit": limit
            }
        )

        rows = result.fetchall()

        return [
            {
                "document_id": str(row.document_id),
                "similarity_score": float(row.avg_similarity)
            }
            for row in rows
        ]

    async def rerank_results(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results for improved relevance.

        Args:
            query: Original search query
            candidates: Initial search results
            top_k: Number of top results to return

        Returns:
            Reranked results
        """
        # TODO: Implement reranking logic
        # Could use cross-encoder or other reranking model
        return candidates[:top_k]


# Global instance
rag_service = RAGService()
