"""
RAG Service for semantic search using pgvector.
"""
from typing import List, Dict, Any
from uuid import UUID
import asyncio
import hashlib
import json
import logging
import warnings
from openai import AsyncOpenAI, OpenAI, OpenAIError, RateLimitError, APIError
import redis.asyncio as redis
import redis as redis_sync
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import settings
from app.models.document import DocumentEmbedding
from app.services.chunking.factory import get_chunking_strategy
from app.services.chunking.base import Chunk

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval Augmented Generation."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. Please set it in .env file or environment variables."
            )

        # Async client for API endpoints
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        # Sync client for Celery tasks
        self.sync_client = OpenAI(api_key=settings.openai_api_key)

        self.embedding_model = settings.embedding_model
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

        # Redis clients for caching (lazy initialization)
        self.redis_client: redis.Redis | None = None
        self.redis_sync_client: redis_sync.Redis | None = None

        # Cache TTL (30 days)
        self.cache_ttl = 30 * 24 * 3600

        logger.info(f"RAGService initialized with model: {self.embedding_model}")

    async def _get_redis(self) -> redis.Redis:
        """Get or create async Redis client."""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(settings.redis_url)
        return self.redis_client

    def _get_redis_sync(self) -> redis_sync.Redis:
        """Get or create sync Redis client."""
        if self.redis_sync_client is None:
            self.redis_sync_client = redis_sync.from_url(settings.redis_url)
        return self.redis_sync_client

    def _cache_key(self, text: str) -> str:
        """
        Generate cache key from text using SHA256 hash.

        Args:
            text: Input text

        Returns:
            Redis cache key
        """
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"embedding:{self.embedding_model}:{text_hash}"

    async def _get_cached_embedding(self, text: str) -> List[float] | None:
        """
        Get embedding from Redis cache.

        Args:
            text: Input text

        Returns:
            Cached embedding or None if not found
        """
        try:
            cache = await self._get_redis()
            cache_key = self._cache_key(text)
            cached = await cache.get(cache_key)

            if cached:
                logger.debug(f"Cache hit for embedding (key: {cache_key[:20]}...)")
                return json.loads(cached)

            logger.debug(f"Cache miss for embedding (key: {cache_key[:20]}...)")
            return None

        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
            return None

    async def _set_cached_embedding(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding in Redis cache.

        Args:
            text: Input text
            embedding: Embedding vector
        """
        try:
            cache = await self._get_redis()
            cache_key = self._cache_key(text)
            await cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding (key: {cache_key[:20]}..., TTL: {self.cache_ttl}s)")

        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    def _get_cached_embedding_sync(self, text: str) -> List[float] | None:
        """
        Get embedding from Redis cache (sync).

        Args:
            text: Input text

        Returns:
            Cached embedding or None if not found
        """
        try:
            cache = self._get_redis_sync()
            cache_key = self._cache_key(text)
            cached = cache.get(cache_key)

            if cached:
                logger.debug(f"Cache hit for embedding (key: {cache_key[:20]}...)")
                return json.loads(cached)

            logger.debug(f"Cache miss for embedding (key: {cache_key[:20]}...)")
            return None

        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
            return None

    def _set_cached_embedding_sync(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding in Redis cache (sync).

        Args:
            text: Input text
            embedding: Embedding vector
        """
        try:
            cache = self._get_redis_sync()
            cache_key = self._cache_key(text)
            cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding (key: {cache_key[:20]}..., TTL: {self.cache_ttl}s)")

        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding vector for text with retry logic.

        Automatically retries on:
        - Rate limit errors (429)
        - Temporary API errors (5xx)

        Args:
            text: Text to embed (max 8191 tokens for text-embedding-3-small)

        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)

        Raises:
            OpenAIError: If API call fails after retries
            ValueError: If text is empty or too long
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate if too long (rough estimate: 1 token ≈ 4 chars)
        max_chars = 8191 * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} characters for embedding")

        # Check cache first
        cached_embedding = await self._get_cached_embedding(text)
        if cached_embedding:
            return cached_embedding

        try:
            logger.debug(f"Creating embedding for text (length: {len(text)} chars)")

            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            # Cache the result
            await self._set_cached_embedding(text, embedding)

            logger.debug(f"Embedding created successfully (dimensions: {len(embedding)})")
            return embedding

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating embedding: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def create_embedding_sync(self, text: str) -> List[float]:
        """
        Synchronous version of create_embedding for Celery workers.

        Automatically retries on:
        - Rate limit errors (429)
        - Temporary API errors (5xx)

        Args:
            text: Text to embed (max 8191 tokens for text-embedding-3-small)

        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)

        Raises:
            OpenAIError: If API call fails after retries
            ValueError: If text is empty or too long
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate if too long (rough estimate: 1 token ≈ 4 chars)
        max_chars = 8191 * 4
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} characters for embedding")

        # Check cache first
        cached_embedding = self._get_cached_embedding_sync(text)
        if cached_embedding:
            return cached_embedding

        try:
            logger.debug(f"Creating embedding (sync) for text (length: {len(text)} chars)")

            response = self.sync_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            # Cache the result
            self._set_cached_embedding_sync(text, embedding)

            logger.debug(f"Embedding created successfully (dimensions: {len(embedding)})")
            return embedding

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating embedding: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts in a single API call (async).

        Optimized for cost: 1 API call instead of N calls.
        OpenAI limit: max 100 inputs per request.

        Args:
            texts: List of texts to embed (max 100)

        Returns:
            List of embedding vectors in same order as input texts

        Raises:
            ValueError: If texts list is empty or has more than 100 items
            OpenAIError: If API call fails after retries
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        if len(texts) > 100:
            raise ValueError(
                f"Too many texts ({len(texts)}). OpenAI limit is 100 per batch. "
                "Split into multiple batches."
            )

        # Filter out empty texts and keep track of indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            logger.info(f"Creating batch embeddings for {len(valid_texts)} texts")

            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=valid_texts,
                encoding_format="float"
            )

            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]

            logger.info(
                f"Batch embeddings created successfully "
                f"({len(embeddings)} embeddings, {len(embeddings[0])} dimensions)"
            )

            # Reconstruct full list with None for empty texts
            result = [None] * len(texts)
            for idx, embedding in zip(valid_indices, embeddings):
                result[idx] = embedding

            return result

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded on batch: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error on batch: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI error on batch: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating batch embeddings: {e}")
            raise

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def create_embeddings_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """
        Synchronous version of create_embeddings_batch for Celery workers.

        Create embeddings for multiple texts in a single API call.
        OpenAI limit: max 100 inputs per request.

        Args:
            texts: List of texts to embed (max 100)

        Returns:
            List of embedding vectors in same order as input texts

        Raises:
            ValueError: If texts list is empty or has more than 100 items
            OpenAIError: If API call fails after retries
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        if len(texts) > 100:
            raise ValueError(
                f"Too many texts ({len(texts)}). OpenAI limit is 100 per batch. "
                "Split into multiple batches."
            )

        # Filter out empty texts and keep track of indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            logger.info(f"Creating batch embeddings (sync) for {len(valid_texts)} texts")

            response = self.sync_client.embeddings.create(
                model=self.embedding_model,
                input=valid_texts,
                encoding_format="float"
            )

            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]

            logger.info(
                f"Batch embeddings created successfully "
                f"({len(embeddings)} embeddings, {len(embeddings[0])} dimensions)"
            )

            # Reconstruct full list with None for empty texts
            result = [None] * len(texts)
            for idx, embedding in zip(valid_indices, embeddings):
                result[idx] = embedding

            return result

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded on batch: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error on batch: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI error on batch: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating batch embeddings: {e}")
            raise

    def chunk_text(self, text: str) -> List[str]:
        """
        DEPRECATED: Use smart chunking strategies instead.

        This method will be removed in PHASE 3.
        Use ingest_document() with document_type for smart chunking.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Q7: Backward compatibility with deprecation warning
        warnings.warn(
            "chunk_text() is deprecated and will be removed in PHASE 3. "
            "Use ingest_document() with document_type for smart chunking strategies.",
            DeprecationWarning,
            stacklevel=2
        )

        # Redirect to FixedChunkingStrategy
        from app.services.chunking.fixed import FixedChunkingStrategy

        strategy = FixedChunkingStrategy(
            target_chunk_size=self.chunk_size,
            max_chunk_size=self.chunk_size * 2,
            overlap=self.chunk_overlap
        )

        chunks = strategy.chunk(text)
        return [chunk.text for chunk in chunks]

    async def ingest_document(
        self,
        db: AsyncSession,
        document_id: UUID,
        content: str,
        document_type: str,
        metadata: Dict[str, Any] | None = None
    ) -> int:
        """
        Ingest document into vector database with smart chunking (PHASE 2).

        Automatically selects optimal chunking strategy based on document_type:
        - past_proposal: SectionChunkingStrategy (512-1024 tokens, H1-H3 detection)
        - certification: SemanticChunkingStrategy (256-512 tokens, paragraphs)
        - case_study: SectionChunkingStrategy (512-1024 tokens)
        - documentation: SectionChunkingStrategy (512-1024 tokens)
        - template: NoSplitChunkingStrategy (single chunk if possible)

        Enriched metadata (Q5 - all 5 fields):
        - section_title, section_level, section_number, parent_section, content_type

        Args:
            db: Database session
            document_id: Unique document identifier
            content: Document content
            document_type: Type of document (past_proposal, certification, etc.)
            metadata: Additional base metadata

        Returns:
            Number of chunks created
        """
        metadata = metadata or {}

        # PHASE 2: Use smart chunking strategy (Q1-Q6 validated)
        strategy = get_chunking_strategy(document_type=document_type)

        chunks: List[Chunk] = strategy.chunk(content, metadata)

        logger.info(
            f"Chunking document {document_id} ({document_type}) with "
            f"{strategy.__class__.__name__}: {len(chunks)} chunks created"
        )

        count = 0
        for chunk in chunks:
            # Create embedding
            embedding = await self.create_embedding(chunk.text)

            # Store in database with enriched metadata
            doc_embedding = DocumentEmbedding(
                document_id=document_id,
                document_type=document_type,
                chunk_text=chunk.text,
                embedding=embedding,
                metadata={
                    **chunk.metadata,
                    # Core chunk metadata
                    "chunk_index": chunk.index,
                    "total_chunks": chunk.total_chunks,
                    "token_count": chunk.token_count,
                    # Q5: All 5 section metadata fields
                    "section_title": chunk.section_title,
                    "section_level": chunk.section_level,
                    "section_number": chunk.section_number,
                    "parent_section": chunk.parent_section,
                    "content_type": chunk.content_type
                }
            )

            db.add(doc_embedding)
            count += 1

        await db.commit()

        logger.info(
            f"Successfully ingested document {document_id}: {count} chunks stored"
        )

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
                meta_data as metadata,
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
