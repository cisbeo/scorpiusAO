"""
Base classes for chunking strategies.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import tiktoken
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Represents a text chunk with enriched metadata.

    Attributes:
        text: The chunk text content
        index: Chunk index (0-based)
        total_chunks: Total number of chunks in document
        token_count: Number of tokens in this chunk
        metadata: Base metadata dictionary
        section_title: Title of the section (if applicable)
        section_level: Header level (H1, H2, H3)
        section_number: Section number (e.g., "2.3.1")
        parent_section: Parent section title
        content_type: Type of content (text, section, list, table, template)
    """
    text: str
    index: int
    total_chunks: int
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Section metadata (Q5: all 5 fields)
    section_title: Optional[str] = None
    section_level: Optional[str] = None  # H1, H2, H3
    section_number: Optional[str] = None  # "2.3.1"
    parent_section: Optional[str] = None

    # Content type
    content_type: str = "text"  # text, section, list, table, code, template


class ChunkingStrategy(ABC):
    """
    Abstract base class for chunking strategies.

    All chunking strategies must implement the chunk() method.
    """

    def __init__(
        self,
        target_chunk_size: int = 512,
        max_chunk_size: int = 1024,
        overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize chunking strategy.

        Args:
            target_chunk_size: Target tokens per chunk (Q1: 512 default)
            max_chunk_size: Maximum tokens per chunk (Q1: 1024 default)
            overlap: Overlap in tokens between chunks (Q2: adaptive per strategy)
            encoding_name: tiktoken encoding (cl100k_base for OpenAI)
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

        # Initialize tiktoken encoder (Q3: validated)
        try:
            self.encoder = tiktoken.get_encoding(encoding_name)
            logger.debug(f"Initialized {self.__class__.__name__} with {encoding_name} encoding")
        except Exception as e:
            logger.error(f"Failed to initialize tiktoken encoder: {e}")
            raise

    def get_token_count(self, text: str) -> int:
        """
        Count tokens using tiktoken (exact for OpenAI).

        Args:
            text: Input text

        Returns:
            Token count
        """
        if not text:
            return 0

        try:
            return len(self.encoder.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens, using estimation: {e}")
            # Fallback: rough estimation (1 token ≈ 4 chars)
            return len(text) // 4

    @abstractmethod
    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into chunks with strategy-specific logic.

        Args:
            text: Text to chunk
            metadata: Base metadata to include in all chunks

        Returns:
            List of Chunk objects
        """
        pass

    def _create_chunk(
        self,
        text: str,
        index: int,
        total_chunks: int,
        base_metadata: Dict[str, Any],
        **kwargs
    ) -> Chunk:
        """
        Helper to create Chunk object with common metadata.

        Args:
            text: Chunk text
            index: Chunk index (0-based)
            total_chunks: Total number of chunks
            base_metadata: Base metadata dict
            **kwargs: Additional Chunk attributes (section_title, etc.)

        Returns:
            Chunk object
        """
        return Chunk(
            text=text,
            index=index,
            total_chunks=total_chunks,
            token_count=self.get_token_count(text),
            metadata=base_metadata,
            **kwargs
        )
