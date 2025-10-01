"""
Factory for creating appropriate chunking strategies.
"""
from typing import Dict, Type
import logging
from .base import ChunkingStrategy
from .fixed import FixedChunkingStrategy
from .section import SectionChunkingStrategy
from .semantic import SemanticChunkingStrategy
from .nosplit import NoSplitChunkingStrategy

logger = logging.getLogger(__name__)

# Strategy map by document type (validated in Q1-Q6)
CHUNKING_STRATEGY_MAP = {
    # Knowledge Base types (Q1: validated sizes)
    "past_proposal": "section",      # Hiérarchie H1-H3, 512-1024 tokens
    "certification": "semantic",     # Paragraphes, 256-512 tokens
    "case_study": "section",         # Hiérarchie H1-H3, 512-1024 tokens
    "documentation": "section",      # Procédures, 512-1024 tokens
    "template": "nosplit",           # Blocs courts, 0-1024 tokens (single chunk)

    # Future: Tender Archive (PHASE 6)
    "past_tender_won": "section",
    "past_tender_strategic": "section"
}

# Strategy class registry
STRATEGY_CLASSES: Dict[str, Type[ChunkingStrategy]] = {
    "fixed": FixedChunkingStrategy,
    "section": SectionChunkingStrategy,
    "semantic": SemanticChunkingStrategy,
    "nosplit": NoSplitChunkingStrategy
}

# Strategy-specific configurations (Q1, Q2)
STRATEGY_CONFIGS = {
    "past_proposal": {
        "strategy": "section",
        "target_chunk_size": 512,
        "max_chunk_size": 1024,
        "overlap": 100  # Q2: 100 for section
    },
    "certification": {
        "strategy": "semantic",
        "target_chunk_size": 256,
        "max_chunk_size": 512,
        "overlap": 0  # Q2: 0 for semantic
    },
    "case_study": {
        "strategy": "section",
        "target_chunk_size": 512,
        "max_chunk_size": 1024,
        "overlap": 100  # Q2: 100 for section
    },
    "documentation": {
        "strategy": "section",
        "target_chunk_size": 512,
        "max_chunk_size": 1024,
        "overlap": 100  # Q2: 100 for section
    },
    "template": {
        "strategy": "nosplit",
        "target_chunk_size": 512,
        "max_chunk_size": 1024,
        "overlap": 0  # Q2: 0 for nosplit
    },
    # Future PHASE 6
    "past_tender_won": {
        "strategy": "section",
        "target_chunk_size": 512,
        "max_chunk_size": 1024,
        "overlap": 100
    },
    "past_tender_strategic": {
        "strategy": "section",
        "target_chunk_size": 512,
        "max_chunk_size": 1024,
        "overlap": 100
    }
}


def get_chunking_strategy(
    document_type: str,
    **kwargs
) -> ChunkingStrategy:
    """
    Get appropriate chunking strategy for document type.

    Uses validated configurations from Q1-Q6:
    - Q1: Target/max chunk sizes per type
    - Q2: Adaptive overlap per strategy
    - Q3: tiktoken for token counting
    - Q4: Regex for section detection
    - Q5: All 5 metadata fields
    - Q6: Priority tested types

    Args:
        document_type: Type of document (past_proposal, certification, etc.)
        **kwargs: Override strategy parameters (optional)

    Returns:
        ChunkingStrategy instance configured for document type

    Examples:
        >>> strategy = get_chunking_strategy("past_proposal")
        >>> chunks = strategy.chunk(text)

        >>> # Override default config
        >>> strategy = get_chunking_strategy("certification", target_chunk_size=128)
    """
    # Get config for document type (or default to fixed)
    config = STRATEGY_CONFIGS.get(document_type)

    if not config:
        logger.warning(
            f"Unknown document_type '{document_type}', using FixedChunkingStrategy"
        )
        strategy_name = "fixed"
        config = {
            "strategy": "fixed",
            "target_chunk_size": 512,
            "max_chunk_size": 1024,
            "overlap": 50
        }
    else:
        strategy_name = config["strategy"]

    # Get strategy class
    strategy_class = STRATEGY_CLASSES[strategy_name]

    # Merge config with kwargs (kwargs take precedence)
    final_config = {
        "target_chunk_size": config["target_chunk_size"],
        "max_chunk_size": config["max_chunk_size"],
        "overlap": config["overlap"],
        **kwargs  # Allow overrides
    }

    # Instantiate strategy
    strategy = strategy_class(**final_config)

    logger.info(
        f"Created {strategy_class.__name__} for '{document_type}' "
        f"(target={final_config['target_chunk_size']}, "
        f"max={final_config['max_chunk_size']}, "
        f"overlap={final_config['overlap']})"
    )

    return strategy
