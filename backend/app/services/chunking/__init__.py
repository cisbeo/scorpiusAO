"""
Chunking strategies for smart document splitting.

This module provides adaptive chunking strategies for different document types.
"""
from .base import Chunk, ChunkingStrategy
from .fixed import FixedChunkingStrategy
from .section import SectionChunkingStrategy
from .semantic import SemanticChunkingStrategy
from .nosplit import NoSplitChunkingStrategy
from .factory import get_chunking_strategy, CHUNKING_STRATEGY_MAP

__all__ = [
    "Chunk",
    "ChunkingStrategy",
    "FixedChunkingStrategy",
    "SectionChunkingStrategy",
    "SemanticChunkingStrategy",
    "NoSplitChunkingStrategy",
    "get_chunking_strategy",
    "CHUNKING_STRATEGY_MAP",
]
