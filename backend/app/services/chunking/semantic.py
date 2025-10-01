"""
Semantic chunking strategy by paragraphs and lists.
"""
import re
from typing import List, Dict, Any, Optional
import logging
from .base import ChunkingStrategy, Chunk

logger = logging.getLogger(__name__)


class SemanticChunkingStrategy(ChunkingStrategy):
    """
    Semantic chunking by paragraphs and lists.

    Use case: certification, short structured documents

    Algorithm:
    1. Split by paragraph boundaries (2+ newlines)
    2. Detect lists (- bullet, 1. numbered)
    3. Group paragraphs to reach target_chunk_size (Q1: 256-512 tokens)
    4. Never split within paragraph or list
    5. No overlap (Q2: 0 tokens for semantic strategy)
    """

    # Paragraph separator (2+ newlines)
    PARAGRAPH_SEPARATOR = re.compile(r'\n{2,}')

    # List patterns
    BULLET_LIST_PATTERN = re.compile(r'^[\-\*\+]\s+', re.MULTILINE)
    NUMBERED_LIST_PATTERN = re.compile(r'^\d+\.\s+', re.MULTILINE)

    def __init__(
        self,
        target_chunk_size: int = 256,  # Q1: 256 tokens for certification
        max_chunk_size: int = 512,     # Q1: 512 max for certification
        overlap: int = 0,              # Q2: 0 overlap for semantic
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize semantic chunking strategy.

        Args:
            target_chunk_size: Target tokens per chunk (Q1: 256 for cert)
            max_chunk_size: Maximum tokens per chunk (Q1: 512 for cert)
            overlap: Overlap in tokens (Q2: 0 for semantic)
            encoding_name: tiktoken encoding
        """
        super().__init__(target_chunk_size, max_chunk_size, overlap, encoding_name)
        logger.debug(
            f"SemanticChunkingStrategy initialized: target={target_chunk_size}, "
            f"max={max_chunk_size}, overlap={overlap}"
        )

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text by semantic paragraphs.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        metadata = metadata or {}

        if not text or not text.strip():
            logger.warning("Empty text provided to SemanticChunkingStrategy")
            return []

        # 1. Split into paragraphs
        paragraphs = self._split_paragraphs(text)
        logger.debug(f"Split text into {len(paragraphs)} paragraphs")

        # 2. Detect content types (text, list, table)
        typed_paragraphs = [
            {
                'text': p,
                'type': self._detect_content_type(p),
                'tokens': self.get_token_count(p)
            }
            for p in paragraphs
        ]

        # 3. Group paragraphs into chunks
        chunks = self._group_paragraphs(typed_paragraphs, metadata)

        logger.info(
            f"SemanticChunkingStrategy created {len(chunks)} chunks "
            f"from {len(paragraphs)} paragraphs"
        )

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Args:
            text: Input text

        Returns:
            List of paragraphs
        """
        paragraphs = self.PARAGRAPH_SEPARATOR.split(text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _detect_content_type(self, paragraph: str) -> str:
        """
        Detect content type of paragraph.

        Args:
            paragraph: Paragraph text

        Returns:
            Content type (text, bullet_list, numbered_list, table)
        """
        # Check for bullet lists
        if self.BULLET_LIST_PATTERN.search(paragraph):
            return "bullet_list"

        # Check for numbered lists
        if self.NUMBERED_LIST_PATTERN.search(paragraph):
            return "numbered_list"

        # Check for table (simple heuristic: contains |)
        if '|' in paragraph and paragraph.count('|') >= 4:
            return "table"

        return "text"

    def _group_paragraphs(
        self,
        paragraphs: List[Dict[str, Any]],
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Group paragraphs into chunks targeting chunk_size.

        Algorithm:
        - Start with empty chunk
        - Add paragraphs until target_chunk_size reached
        - If single paragraph > max_chunk_size, keep as single chunk
          (never split paragraph - semantic integrity)

        Args:
            paragraphs: List of paragraph dicts
            base_metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        chunks = []
        current_chunk_paragraphs = []
        current_chunk_tokens = 0

        for para in paragraphs:
            # Case 1: Single paragraph exceeds max_chunk_size
            # Keep as single chunk to preserve semantic integrity
            if para['tokens'] > self.max_chunk_size:
                logger.debug(
                    f"Paragraph exceeds max_chunk_size ({para['tokens']} > "
                    f"{self.max_chunk_size}), keeping as single chunk"
                )

                # Flush current chunk first
                if current_chunk_paragraphs:
                    chunk_text = "\n\n".join(p['text'] for p in current_chunk_paragraphs)
                    content_types = list(set(p['type'] for p in current_chunk_paragraphs))

                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            index=len(chunks),
                            total_chunks=0,  # Updated later
                            token_count=current_chunk_tokens,
                            metadata={
                                **base_metadata,
                                "chunking_strategy": "semantic",
                                "paragraph_count": len(current_chunk_paragraphs)
                            },
                            content_type=content_types[0] if len(content_types) == 1 else "mixed"
                        )
                    )
                    current_chunk_paragraphs = []
                    current_chunk_tokens = 0

                # Add large paragraph as single chunk
                chunks.append(
                    Chunk(
                        text=para['text'],
                        index=len(chunks),
                        total_chunks=0,
                        token_count=para['tokens'],
                        metadata={
                            **base_metadata,
                            "chunking_strategy": "semantic",
                            "paragraph_count": 1,
                            "oversized": True
                        },
                        content_type=para['type']
                    )
                )
                continue

            # Case 2: Adding paragraph keeps chunk under target
            if current_chunk_tokens + para['tokens'] <= self.target_chunk_size:
                current_chunk_paragraphs.append(para)
                current_chunk_tokens += para['tokens']

            # Case 3: Adding would exceed target -> finish current chunk
            else:
                if current_chunk_paragraphs:
                    chunk_text = "\n\n".join(p['text'] for p in current_chunk_paragraphs)
                    content_types = list(set(p['type'] for p in current_chunk_paragraphs))

                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            index=len(chunks),
                            total_chunks=0,  # Updated later
                            token_count=current_chunk_tokens,
                            metadata={
                                **base_metadata,
                                "chunking_strategy": "semantic",
                                "paragraph_count": len(current_chunk_paragraphs)
                            },
                            content_type=content_types[0] if len(content_types) == 1 else "mixed"
                        )
                    )

                # Start new chunk with current paragraph
                current_chunk_paragraphs = [para]
                current_chunk_tokens = para['tokens']

        # Add last chunk
        if current_chunk_paragraphs:
            chunk_text = "\n\n".join(p['text'] for p in current_chunk_paragraphs)
            content_types = list(set(p['type'] for p in current_chunk_paragraphs))

            chunks.append(
                Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    total_chunks=0,
                    token_count=current_chunk_tokens,
                    metadata={
                        **base_metadata,
                        "chunking_strategy": "semantic",
                        "paragraph_count": len(current_chunk_paragraphs)
                    },
                    content_type=content_types[0] if len(content_types) == 1 else "mixed"
                )
            )

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks
