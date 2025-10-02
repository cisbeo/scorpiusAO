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

    async def ingest_kb_document(
        self,
        db: AsyncSession,
        kb_document_id: UUID,
        content: str,
        document_type: str,
        metadata: Dict[str, Any] | None = None
    ) -> int:
        """
        Ingest Knowledge Base document into vector database.

        Args:
            db: Database session
            kb_document_id: KB document UUID
            content: Document content
            document_type: Type (past_proposal, case_study, certification, documentation, template, historical_tender)
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
                document_id=kb_document_id,
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

    async def ingest_document(
        self,
        db: AsyncSession,
        document_id: UUID,
        content: str,
        document_type: str,
        metadata: Dict[str, Any] | None = None
    ) -> int:
        """
        Legacy method - redirects to ingest_kb_document.
        Kept for backward compatibility.
        """
        return await self.ingest_kb_document(
            db, document_id, content, document_type, metadata
        )

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

    async def find_similar_historical_tenders(
        self,
        db: AsyncSession,
        tender_description: str,
        limit: int = 5,
        include_lost: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar historical tenders based on description.

        Args:
            db: Database session
            tender_description: Current tender description/requirements
            limit: Number of similar tenders to return
            include_lost: Include lost tenders in results

        Returns:
            List of similar historical tenders with metadata
        """
        # Create query embedding
        query_embedding = await self.create_embedding(tender_description)

        # Build filter based on include_lost
        result_filter = ""
        if not include_lost:
            result_filter = "AND metadata->>'result' = 'won'"

        # Find similar historical tenders
        sql = text(f"""
            SELECT
                de.document_id,
                de.metadata,
                AVG(1 - (de.embedding <=> :query_embedding)) as avg_similarity
            FROM document_embeddings de
            WHERE de.document_type = 'historical_tender'
            {result_filter}
            GROUP BY de.document_id, de.metadata
            ORDER BY avg_similarity DESC
            LIMIT :limit
        """)

        result = await db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "limit": limit
            }
        )

        rows = result.fetchall()

        return [
            {
                "historical_tender_id": str(row.document_id),
                "similarity_score": float(row.avg_similarity),
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
        Legacy method - use find_similar_historical_tenders instead.
        Kept for backward compatibility.
        """
        # Get tender content to create embedding
        from app.models.tender import Tender
        stmt = select(Tender).where(Tender.id == tender_id)
        result = await db.execute(stmt)
        tender = result.scalar_one_or_none()

        if not tender:
            return []

        # Use description/requirements to find similar
        description = tender.description or tender.title
        return await self.find_similar_historical_tenders(
            db, description, limit, include_lost=True
        )

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

    # === USE CASE #1: Auto-Suggestion par Critère ===
    async def suggest_content_for_criterion(
        self,
        db: AsyncSession,
        criterion_description: str,
        top_k: int = 3,
        document_types: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest relevant content for a specific tender criterion.

        Use Case #1 implementation: Auto-suggestions from KB.

        Args:
            db: Database session
            criterion_description: Description of the criterion to address
            top_k: Number of suggestions to return
            document_types: Filter by KB document types (default: past_proposal, case_study, documentation)

        Returns:
            List of relevant content suggestions with scores
        """
        if document_types is None:
            document_types = ['past_proposal', 'case_study', 'documentation']

        results = await self.retrieve_relevant_content(
            db,
            query=criterion_description,
            top_k=top_k,
            document_types=document_types
        )

        return results

    # === USE CASE #2: Recherche Sémantique Libre ===
    async def semantic_search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Free-form semantic search across Knowledge Base.

        Use Case #2 implementation: Manual semantic search.

        Args:
            db: Database session
            query: User's search query
            top_k: Number of results to return
            filters: Optional filters (document_type, tags, etc.)

        Returns:
            List of matching documents with similarity scores
        """
        document_types = filters.get('document_types') if filters else None

        results = await self.retrieve_relevant_content(
            db,
            query=query,
            top_k=top_k,
            document_types=document_types
        )

        return results

    # === USE CASE #3: Références Clients Contextuelles ===
    async def find_relevant_case_studies(
        self,
        db: AsyncSession,
        tender_requirements: str,
        sector: str | None = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find relevant client case studies for tender.

        Use Case #3 implementation: Contextual client references.

        Args:
            db: Database session
            tender_requirements: Tender requirements/description
            sector: Optional sector filter
            top_k: Number of case studies to return

        Returns:
            List of relevant case studies
        """
        results = await self.retrieve_relevant_content(
            db,
            query=tender_requirements,
            top_k=top_k,
            document_types=['case_study']
        )

        # Filter by sector if provided
        if sector:
            results = [
                r for r in results
                if r.get('metadata', {}).get('client_sector') == sector
            ][:top_k]

        return results

    # === USE CASE #4: Compliance & Certifications Auto-Proof ===
    async def find_compliance_documents(
        self,
        db: AsyncSession,
        requirement: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find certifications and compliance documents for requirement.

        Use Case #4 implementation: Auto-proof compliance.

        Args:
            db: Database session
            requirement: Compliance requirement description
            top_k: Number of documents to return

        Returns:
            List of relevant certifications and compliance docs
        """
        results = await self.retrieve_relevant_content(
            db,
            query=requirement,
            top_k=top_k,
            document_types=['certification', 'documentation']
        )

        return results

    # === USE CASE #5: Smart Templates Assembly ===
    async def find_templates(
        self,
        db: AsyncSession,
        section_description: str,
        template_type: str | None = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find relevant templates for a section.

        Use Case #5 implementation: Smart template assembly.

        Args:
            db: Database session
            section_description: Description of section to write
            template_type: Optional template type filter
            top_k: Number of templates to return

        Returns:
            List of relevant templates
        """
        results = await self.retrieve_relevant_content(
            db,
            query=section_description,
            top_k=top_k,
            document_types=['template']
        )

        # Filter by template type if provided
        if template_type:
            results = [
                r for r in results
                if r.get('metadata', {}).get('template_type') == template_type
            ][:top_k]

        return results


# Global instance
rag_service = RAGService()
