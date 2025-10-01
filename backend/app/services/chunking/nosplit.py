"""
No-split chunking strategy for short documents.
"""
from typing import List, Dict, Any, Optional
import logging
from .base import ChunkingStrategy, Chunk

logger = logging.getLogger(__name__)


class NoSplitChunkingStrategy(ChunkingStrategy):
    """
    No-split chunking for short documents.

    Use case: template (short reusable blocks)

    Algorithm:
    - If document < max_chunk_size -> single chunk
    - If document > max_chunk_size -> fallback to FixedChunkingStrategy
    - No overlap (Q2: 0 tokens for nosplit)
    """

    def __init__(
        self,
        target_chunk_size: int = 512,
        max_chunk_size: int = 1024,  # Q1: 1024 max for templates
        overlap: int = 0,            # Q2: 0 overlap for nosplit
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize no-split chunking strategy.

        Args:
            target_chunk_size: Target tokens per chunk (unused for nosplit)
            max_chunk_size: Maximum tokens per chunk (Q1: 1024)
            overlap: Overlap in tokens (Q2: 0 for nosplit)
            encoding_name: tiktoken encoding
        """
        super().__init__(target_chunk_size, max_chunk_size, overlap, encoding_name)
        logger.debug(
            f"NoSplitChunkingStrategy initialized: max={max_chunk_size}"
        )

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Return single chunk if possible, otherwise split with fallback.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List with 1 Chunk (or more if text too large)
        """
        metadata = metadata or {}

        if not text or not text.strip():
            logger.warning("Empty text provided to NoSplitChunkingStrategy")
            return []

        token_count = self.get_token_count(text)

        # Case 1: Fits in single chunk
        if token_count <= self.max_chunk_size:
            logger.debug(
                f"Text fits in single chunk ({token_count} <= {self.max_chunk_size})"
            )

            return [
                Chunk(
                    text=text,
                    index=0,
                    total_chunks=1,
                    token_count=token_count,
                    metadata={
                        **metadata,
                        "chunking_strategy": "nosplit"
                    },
                    content_type="template"
                )
            ]

        # Case 2: Too large, fallback to fixed chunking
        else:
            logger.warning(
                f"Text too large for nosplit ({token_count} > {self.max_chunk_size}), "
                f"falling back to FixedChunkingStrategy"
            )

            from .fixed import FixedChunkingStrategy

            fallback_strategy = FixedChunkingStrategy(
                target_chunk_size=self.target_chunk_size,
                max_chunk_size=self.max_chunk_size,
                overlap=50  # Use standard 50 tokens for fallback
            )

            chunks = fallback_strategy.chunk(text, metadata)

            # Update metadata to indicate fallback
            for chunk in chunks:
                chunk.metadata["chunking_strategy"] = "nosplit_fallback"
                chunk.metadata["fallback_reason"] = (
                    f"Text too large: {token_count} tokens > {self.max_chunk_size}"
                )
                chunk.content_type = "template"

            logger.info(
                f"NoSplitChunkingStrategy fallback created {len(chunks)} chunks"
            )

            return chunks
