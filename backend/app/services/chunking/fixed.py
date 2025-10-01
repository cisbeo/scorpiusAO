"""
Fixed-size chunking strategy with token-based overlap.
"""
from typing import List, Dict, Any, Optional
import logging
from .base import ChunkingStrategy, Chunk

logger = logging.getLogger(__name__)


class FixedChunkingStrategy(ChunkingStrategy):
    """
    Fixed-size chunking with token-based overlap.

    Use case: Fallback for unstructured text.

    Algorithm:
    1. Tokenize entire text using tiktoken
    2. Create chunks of target_chunk_size tokens
    3. Add overlap tokens from previous chunk
    4. Generate Chunk objects with metadata
    """

    def __init__(
        self,
        target_chunk_size: int = 512,
        max_chunk_size: int = 1024,
        overlap: int = 50,  # Q2: 50 tokens for fixed strategy
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize fixed chunking strategy.

        Args:
            target_chunk_size: Target tokens per chunk (Q1: 512)
            max_chunk_size: Maximum tokens per chunk (Q1: 1024)
            overlap: Overlap in tokens (Q2: 50 for fixed)
            encoding_name: tiktoken encoding
        """
        super().__init__(target_chunk_size, max_chunk_size, overlap, encoding_name)
        logger.debug(
            f"FixedChunkingStrategy initialized: target={target_chunk_size}, "
            f"max={max_chunk_size}, overlap={overlap}"
        )

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into fixed-size chunks with overlap.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        metadata = metadata or {}

        if not text or not text.strip():
            logger.warning("Empty text provided to FixedChunkingStrategy")
            return []

        # Tokenize entire text
        try:
            tokens = self.encoder.encode(text)
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise

        chunks_text = []
        start = 0

        while start < len(tokens):
            # Extract chunk tokens
            end = min(start + self.target_chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]

            # Decode tokens back to text
            try:
                chunk_text = self.encoder.decode(chunk_tokens)
                chunks_text.append(chunk_text)
            except Exception as e:
                logger.error(f"Error decoding chunk: {e}")
                raise

            # Move start with overlap
            start = end - self.overlap

        # Create Chunk objects
        chunks = [
            self._create_chunk(
                text=chunk_text,
                index=idx,
                total_chunks=len(chunks_text),
                base_metadata={
                    **metadata,
                    "chunking_strategy": "fixed",
                    "chunk_size_tokens": self.target_chunk_size,
                    "overlap_tokens": self.overlap
                },
                content_type="text"
            )
            for idx, chunk_text in enumerate(chunks_text)
        ]

        logger.info(
            f"FixedChunkingStrategy created {len(chunks)} chunks "
            f"from {len(tokens)} tokens"
        )

        return chunks
