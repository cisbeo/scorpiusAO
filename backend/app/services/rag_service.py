"""
RAG Service for semantic search using pgvector.
"""
from typing import List, Dict, Any
from uuid import UUID
from openai import OpenAI, AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session  # For sync operations
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.document import DocumentEmbedding


class RAGService:
    """Service for Retrieval Augmented Generation."""

    def __init__(self):
        if settings.openai_api_key:
            # Sync client for Celery tasks
            self.sync_client = OpenAI(api_key=settings.openai_api_key)
            # Async client for FastAPI endpoints
            self.async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            self.sync_client = None
            self.async_client = None

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
        if not self.async_client:
            raise ValueError("OpenAI API key not configured")

        response = await self.async_client.embeddings.create(
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

    # ========== SYNCHRONOUS METHODS FOR CELERY TASKS ==========

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def create_embedding_sync(self, text: str) -> List[float]:
        """
        Create embedding vector for text (SYNC version for Celery).

        Args:
            text: Text to embed (max ~8000 tokens for text-embedding-3-small)

        Returns:
            Embedding vector (1536 dimensions)
        """
        if not self.sync_client:
            raise ValueError("OpenAI API key not configured")

        try:
            response = self.sync_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ OpenAI embedding error: {e}")
            raise

    def chunk_sections_semantic(
        self,
        sections: List[Dict[str, Any]],
        max_tokens: int = 1000,
        min_tokens: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Semantic chunking based on structured sections from parser.

        Strategy:
        1. Filter TOC sections (skip)
        2. Small sections (<100 tokens): Merge with next if possible
        3. Medium sections (100-1000 tokens): Keep as-is (1 section = 1 chunk)
        4. Large sections (>1000 tokens): Split with 200 token overlap

        Args:
            sections: List of section dicts from DocumentSection
            max_tokens: Max tokens per chunk (default 1000)
            min_tokens: Min tokens for standalone chunk (default 100)

        Returns:
            List of chunks with text + rich metadata
        """
        chunks = []

        # Filter TOC sections
        content_sections = [s for s in sections if not s.get("is_toc", False)]

        # Sort by page and line
        content_sections.sort(key=lambda s: (s.get("page", 0), s.get("line", 0)))

        i = 0
        while i < len(content_sections):
            section = content_sections[i]

            # Build section text
            section_number = section.get("section_number", "")
            title = section.get("title", "")
            content = section.get("content", "")

            section_text = f"Section {section_number}: {title}\n\n{content}" if section_number else f"{title}\n\n{content}"

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = len(section_text) // 4

            if estimated_tokens < min_tokens and i + 1 < len(content_sections):
                # SMALL: Try merge with next
                next_section = content_sections[i + 1]
                next_num = next_section.get("section_number", "")
                next_title = next_section.get("title", "")
                next_content = next_section.get("content", "")
                next_text = f"Section {next_num}: {next_title}\n\n{next_content}" if next_num else f"{next_title}\n\n{next_content}"

                merged_text = section_text + "\n\n" + next_text

                if len(merged_text) // 4 <= max_tokens:
                    # Merge successful
                    chunks.append({
                        "text": merged_text,
                        "metadata": {
                            "section_numbers": [section.get("section_number"), next_section.get("section_number")],
                            "pages": list(set([section.get("page"), next_section.get("page")])),
                            "is_key_section": section.get("is_key_section") or next_section.get("is_key_section"),
                            "is_merged": True
                        }
                    })
                    i += 2
                    continue

            if estimated_tokens <= max_tokens:
                # MEDIUM: Keep as-is
                chunks.append({
                    "text": section_text,
                    "metadata": {
                        "section_number": section.get("section_number"),
                        "page": section.get("page"),
                        "is_key_section": section.get("is_key_section", False),
                        "parent_number": section.get("parent_number"),
                        "level": section.get("level", 1)
                    }
                })
            else:
                # LARGE: Split with overlap
                words = section_text.split()
                chunk_size_words = max_tokens * 4  # Approx words
                overlap_words = (self.chunk_overlap * 4) // 4  # 200 tokens default

                part = 0
                for j in range(0, len(words), chunk_size_words - overlap_words):
                    chunk_words = words[j:j + chunk_size_words]
                    chunk_text = " ".join(chunk_words)

                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "section_number": section.get("section_number"),
                            "page": section.get("page"),
                            "is_key_section": section.get("is_key_section", False),
                            "chunk_part": part,
                            "is_split": True
                        }
                    })
                    part += 1

            i += 1

        print(f"  📦 Semantic chunking: {len(content_sections)} sections → {len(chunks)} chunks")

        return chunks

    def ingest_document_sync(
        self,
        db: Session,
        document_id: UUID,
        chunks: List[Dict[str, Any]],
        document_type: str,
        metadata: Dict[str, Any] | None = None
    ) -> int:
        """
        Ingest document chunks into vector DB (SYNC for Celery).

        Args:
            db: Sync database session
            document_id: Document UUID
            chunks: Pre-chunked sections with metadata
            document_type: Type (tender, proposal, etc.)
            metadata: Additional metadata

        Returns:
            Number of chunks ingested
        """
        metadata = metadata or {}
        count = 0
        batch = []

        print(f"  📦 Creating embeddings for {len(chunks)} chunks...")

        for chunk_data in chunks:
            # Create embedding
            embedding = self.create_embedding_sync(chunk_data["text"])

            # Prepare record
            doc_embedding = DocumentEmbedding(
                document_id=document_id,
                document_type=document_type,
                chunk_text=chunk_data["text"],
                embedding=embedding,
                meta_data={
                    **metadata,
                    **chunk_data.get("metadata", {}),
                    "chunk_index": count,
                    "total_chunks": len(chunks)
                }
            )

            batch.append(doc_embedding)
            count += 1

            # Batch insert every 100 chunks
            if len(batch) >= 100:
                db.bulk_save_objects(batch)
                db.commit()
                print(f"    ✓ {count}/{len(chunks)} chunks...")
                batch = []

        # Insert remaining
        if batch:
            db.bulk_save_objects(batch)
            db.commit()

        print(f"  ✅ Ingested {count} chunks")
        return count

    def retrieve_relevant_content_sync(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        document_ids: List[str] | None = None,
        document_types: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant content using semantic search (SYNC for Celery).

        Args:
            db: Sync database session
            query: Search query
            top_k: Number of results
            document_ids: Filter by specific document IDs
            document_types: Filter by types

        Returns:
            List of relevant chunks with similarity scores
        """
        # Create query embedding
        query_embedding = self.create_embedding_sync(query)

        # Build SQL filters
        filters = []

        if document_ids:
            ids_str = ", ".join([f"'{id}'" for id in document_ids])
            filters.append(f"document_id IN ({ids_str})")

        if document_types:
            types_str = ", ".join([f"'{t}'" for t in document_types])
            filters.append(f"document_type IN ({types_str})")

        where_clause = " AND ".join(filters) if filters else "1=1"

        # Execute vector search
        # Convert embedding to string format for PostgreSQL
        emb_str = str(query_embedding)

        sql = text(f"""
            SELECT
                id,
                document_id,
                document_type,
                chunk_text,
                meta_data,
                1 - (embedding <=> '{emb_str}'::vector) as similarity
            FROM document_embeddings
            WHERE {where_clause}
            ORDER BY embedding <=> '{emb_str}'::vector
            LIMIT :top_k
        """)

        result = db.execute(sql, {"top_k": top_k})

        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "document_id": str(row.document_id),
                "document_type": row.document_type,
                "chunk_text": row.chunk_text,
                "similarity_score": float(row.similarity),
                "metadata": row.meta_data
            }
            for row in rows
        ]

    def find_similar_tenders_sync(
        self,
        db: Session,
        tender_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past tenders (SYNC for Celery).

        Uses first document of tender as representative for similarity.

        Args:
            db: Sync database session
            tender_id: Current tender ID
            limit: Number of similar tenders

        Returns:
            List of similar tenders with avg similarity
        """
        from app.models.tender_document import TenderDocument

        # Get first document ID of tender
        stmt = select(TenderDocument.id).where(
            TenderDocument.tender_id == tender_id
        ).limit(1)

        result = db.execute(stmt)
        first_doc = result.scalar_one_or_none()

        if not first_doc:
            return []

        # Get first embedding of this document
        stmt = select(DocumentEmbedding.embedding).where(
            DocumentEmbedding.document_id == first_doc
        ).limit(1)

        result = db.execute(stmt)
        current_embedding_row = result.first()

        if not current_embedding_row:
            return []

        current_embedding = current_embedding_row[0]

        # Find similar tenders by avg embedding similarity
        sql = text("""
            SELECT DISTINCT
                td.tender_id,
                AVG(1 - (de.embedding <=> :query_embedding::vector)) as avg_similarity
            FROM document_embeddings de
            JOIN tender_documents td ON td.id = de.document_id
            WHERE td.tender_id != :current_tender_id
            GROUP BY td.tender_id
            ORDER BY avg_similarity DESC
            LIMIT :limit
        """)

        result = db.execute(
            sql,
            {
                "query_embedding": current_embedding,
                "current_tender_id": str(tender_id),
                "limit": limit
            }
        )

        rows = result.fetchall()

        return [
            {
                "tender_id": str(row.tender_id),
                "similarity_score": float(row.avg_similarity)
            }
            for row in rows
        ]


# Global instance
rag_service = RAGService()
