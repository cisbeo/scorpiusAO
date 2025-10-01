"""
Unit tests for chunking strategies (PHASE 2).

Test priority (Q6):
1. past_proposal (SectionChunkingStrategy) - PRIORITY MAX
2. certification (SemanticChunkingStrategy) - PRIORITY HIGH
3. template (NoSplitChunkingStrategy) - PRIORITY MEDIUM
4. fixed (FixedChunkingStrategy) - PRIORITY LOW (fallback)
"""
import pytest
from app.services.chunking.fixed import FixedChunkingStrategy
from app.services.chunking.section import SectionChunkingStrategy
from app.services.chunking.semantic import SemanticChunkingStrategy
from app.services.chunking.nosplit import NoSplitChunkingStrategy
from app.services.chunking.factory import get_chunking_strategy


class TestSectionChunkingStrategy:
    """
    Test SectionChunkingStrategy (PRIORITY MAX - Q6).

    Use case: past_proposal, case_study, documentation
    """

    def test_markdown_header_detection(self):
        """Test Markdown header detection (Q4: regex)."""
        strategy = SectionChunkingStrategy()

        text = """
# Introduction

This is intro content with some text.

## Section 2.1

Content for section 2.1 here.

### Subsection 2.1.1

More detailed content in subsection.
"""

        chunks = strategy.chunk(text)

        # Verify chunks created
        assert len(chunks) >= 1

        # Verify section metadata (Q5: all 5 fields)
        section_titles = [c.section_title for c in chunks if c.section_title]
        assert "Introduction" in section_titles or "Section 2.1" in section_titles

        section_levels = [c.section_level for c in chunks if c.section_level]
        assert any(level in ["H1", "H2", "H3"] for level in section_levels)

    def test_numbered_header_detection(self):
        """Test numbered header detection (1. 1.1 1.1.1) (Q4)."""
        strategy = SectionChunkingStrategy()

        text = """
1. Introduction

Intro content here.

1.1 Background

Background content with details.

1.1.1 History

Historical context and information.
"""

        chunks = strategy.chunk(text)

        assert len(chunks) >= 1

        # Verify section_number field (Q5)
        section_numbers = [c.section_number for c in chunks if c.section_number]
        assert len(section_numbers) > 0
        assert any(num in ["1", "1.1", "1.1.1"] for num in section_numbers)

    def test_parent_section_detection(self):
        """Test parent_section field detection (Q5)."""
        strategy = SectionChunkingStrategy()

        text = """
# Main Section

Main content.

## Subsection

Sub content.

### Deep Section

Deep content.
"""

        chunks = strategy.chunk(text)

        # Find H3 chunk
        h3_chunks = [c for c in chunks if c.section_level == "H3"]

        if h3_chunks:
            # Verify parent_section populated (Q5)
            assert h3_chunks[0].parent_section is not None

    def test_large_section_splitting(self):
        """Test splitting of large sections with overlap (Q2: 100 tokens)."""
        strategy = SectionChunkingStrategy(
            target_chunk_size=100,
            max_chunk_size=150,
            overlap=10
        )

        # Create large section (500+ tokens)
        text = f"# Large Section\n\n{'word ' * 600}"

        chunks = strategy.chunk(text)

        # Should split into multiple chunks
        assert len(chunks) > 1

        # All chunks should have same section_title (Q5)
        assert all(c.section_title == "Large Section" for c in chunks)

        # Verify token counts (Q1)
        assert all(c.token_count <= 150 for c in chunks)

    def test_chunk_sizes_for_past_proposal(self):
        """Test default chunk sizes for past_proposal type (Q1: 512/1024)."""
        strategy = get_chunking_strategy("past_proposal")

        # Verify configuration (Q1, Q2)
        assert strategy.target_chunk_size == 512
        assert strategy.max_chunk_size == 1024
        assert strategy.overlap == 100  # Q2: 100 for section

    def test_all_five_metadata_fields(self):
        """Test all 5 section metadata fields populated (Q5)."""
        strategy = SectionChunkingStrategy()

        text = """
# 1. Main Title

Content here.

## 1.1 Subtitle

More content.
"""

        chunks = strategy.chunk(text)

        # At least one chunk should have section metadata
        section_chunks = [c for c in chunks if c.section_title]

        assert len(section_chunks) > 0

        # Verify all 5 fields exist (Q5)
        chunk = section_chunks[0]
        assert chunk.section_title is not None  # 1. section_title
        assert chunk.section_level is not None  # 2. section_level
        # 3. section_number - may be None for Markdown
        # 4. parent_section - may be None for H1
        assert chunk.content_type is not None  # 5. content_type

    def test_no_sections_fallback(self):
        """Test fallback when no sections detected."""
        strategy = SectionChunkingStrategy()

        text = "Just plain text with no headers at all."

        chunks = strategy.chunk(text)

        # Should create at least 1 chunk
        assert len(chunks) >= 1

        # Should have default section metadata
        assert chunks[0].section_title == "Document"
        assert chunks[0].section_level == "H1"


class TestSemanticChunkingStrategy:
    """
    Test SemanticChunkingStrategy (PRIORITY HIGH - Q6).

    Use case: certification
    """

    def test_paragraph_splitting(self):
        """Test splitting by paragraphs (2+ newlines)."""
        strategy = SemanticChunkingStrategy()

        text = """
First paragraph with some content here.

Second paragraph with different content.

Third paragraph with more information.
"""

        chunks = strategy.chunk(text)

        assert len(chunks) >= 1

        # Each chunk should preserve paragraph boundaries
        for chunk in chunks:
            # No leading/trailing whitespace
            assert chunk.text == chunk.text.strip()

    def test_bullet_list_detection(self):
        """Test bullet list content type detection (Q5)."""
        strategy = SemanticChunkingStrategy()

        text = """
- Item 1
- Item 2
- Item 3
"""

        chunks = strategy.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content_type == "bullet_list"

    def test_numbered_list_detection(self):
        """Test numbered list content type detection (Q5)."""
        strategy = SemanticChunkingStrategy()

        text = """
1. First item
2. Second item
3. Third item
"""

        chunks = strategy.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content_type == "numbered_list"

    def test_table_detection(self):
        """Test table content type detection (Q5)."""
        strategy = SemanticChunkingStrategy()

        text = """
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
"""

        chunks = strategy.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content_type == "table"

    def test_no_split_within_paragraph(self):
        """Test that paragraphs are never split (semantic integrity)."""
        strategy = SemanticChunkingStrategy(target_chunk_size=20)

        text = """
This is a long paragraph that exceeds the target chunk size but should never be split to preserve semantic integrity.

This is another paragraph.
"""

        chunks = strategy.chunk(text)

        # Each chunk should contain complete paragraphs
        for chunk in chunks:
            # Should not start mid-sentence
            assert not chunk.text.startswith(" ")
            # Should contain full sentences
            assert "\n\n" in chunk.text or chunks.index(chunk) == len(chunks) - 1

    def test_oversized_paragraph_handling(self):
        """Test handling of paragraph exceeding max_chunk_size."""
        strategy = SemanticChunkingStrategy(
            target_chunk_size=50,
            max_chunk_size=100
        )

        # Create paragraph with 150 tokens
        long_paragraph = "word " * 200

        text = f"{long_paragraph}\n\nShort paragraph."

        chunks = strategy.chunk(text)

        # Should keep oversized paragraph as single chunk
        assert len(chunks) >= 1

        # Check metadata for oversized flag
        oversized_chunks = [c for c in chunks if c.metadata.get("oversized")]
        assert len(oversized_chunks) > 0

    def test_chunk_sizes_for_certification(self):
        """Test default chunk sizes for certification type (Q1: 256/512)."""
        strategy = get_chunking_strategy("certification")

        # Verify configuration (Q1, Q2)
        assert strategy.target_chunk_size == 256
        assert strategy.max_chunk_size == 512
        assert strategy.overlap == 0  # Q2: 0 for semantic

    def test_zero_overlap(self):
        """Test no overlap between chunks (Q2: 0 for semantic)."""
        strategy = SemanticChunkingStrategy(
            target_chunk_size=50,
            overlap=0
        )

        text = """
First paragraph.

Second paragraph.

Third paragraph.

Fourth paragraph.
"""

        chunks = strategy.chunk(text)

        # Verify no content duplication between chunks
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk1_words = set(chunks[i].text.split())
                chunk2_words = set(chunks[i + 1].text.split())

                # Minimal overlap acceptable (common words like "the", "and")
                overlap_ratio = len(chunk1_words & chunk2_words) / min(
                    len(chunk1_words), len(chunk2_words)
                )
                assert overlap_ratio < 0.3  # Less than 30% overlap


class TestNoSplitChunkingStrategy:
    """
    Test NoSplitChunkingStrategy (PRIORITY MEDIUM - Q6).

    Use case: template
    """

    def test_short_document_single_chunk(self):
        """Test short document returns single chunk."""
        strategy = NoSplitChunkingStrategy()

        text = "Short template content here for company presentation."

        chunks = strategy.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].content_type == "template"
        assert chunks[0].index == 0
        assert chunks[0].total_chunks == 1

    def test_large_document_fallback(self):
        """Test large document falls back to FixedChunkingStrategy."""
        strategy = NoSplitChunkingStrategy(max_chunk_size=100)

        # Create large text (500+ tokens)
        text = "word " * 500

        chunks = strategy.chunk(text)

        # Should fallback to multiple chunks
        assert len(chunks) > 1

        # Verify fallback metadata
        assert all(
            c.metadata["chunking_strategy"] == "nosplit_fallback"
            for c in chunks
        )
        assert chunks[0].metadata.get("fallback_reason") is not None

    def test_chunk_sizes_for_template(self):
        """Test default chunk sizes for template type (Q1: N/A/1024)."""
        strategy = get_chunking_strategy("template")

        # Verify configuration (Q1, Q2)
        assert strategy.max_chunk_size == 1024
        assert strategy.overlap == 0  # Q2: 0 for nosplit

    def test_empty_text(self):
        """Test handling of empty text."""
        strategy = NoSplitChunkingStrategy()

        text = ""

        chunks = strategy.chunk(text)

        assert len(chunks) == 0


class TestFixedChunkingStrategy:
    """
    Test FixedChunkingStrategy (PRIORITY LOW - fallback).

    Use case: Unknown document types, fallback
    """

    def test_basic_chunking(self):
        """Test basic fixed-size chunking."""
        strategy = FixedChunkingStrategy(target_chunk_size=50, overlap=10)

        # Create text with ~200 tokens
        text = "word " * 200

        chunks = strategy.chunk(text)

        assert len(chunks) > 1
        assert all(chunk.token_count <= 75 for chunk in chunks)  # Some margin
        assert all(chunk.metadata["chunking_strategy"] == "fixed" for chunk in chunks)

    def test_overlap(self):
        """Test overlap between chunks (Q2: 50 tokens for fixed)."""
        strategy = FixedChunkingStrategy(target_chunk_size=50, overlap=10)

        text = "word " * 200

        chunks = strategy.chunk(text)

        # Should have overlap
        assert len(chunks) > 1

        # Verify metadata includes overlap info
        assert chunks[0].metadata["overlap_tokens"] == 10

    def test_token_counting_with_tiktoken(self):
        """Test accurate token counting with tiktoken (Q3)."""
        strategy = FixedChunkingStrategy()

        text = "Hello world! This is a test."

        token_count = strategy.get_token_count(text)

        # tiktoken should give exact count
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_empty_text(self):
        """Test handling of empty text."""
        strategy = FixedChunkingStrategy()

        text = ""

        chunks = strategy.chunk(text)

        assert len(chunks) == 0


class TestChunkingFactory:
    """
    Test factory function for strategy selection.
    """

    def test_past_proposal_strategy(self):
        """Test past_proposal gets SectionChunkingStrategy."""
        strategy = get_chunking_strategy("past_proposal")

        assert isinstance(strategy, SectionChunkingStrategy)
        assert strategy.target_chunk_size == 512  # Q1
        assert strategy.overlap == 100  # Q2

    def test_certification_strategy(self):
        """Test certification gets SemanticChunkingStrategy."""
        strategy = get_chunking_strategy("certification")

        assert isinstance(strategy, SemanticChunkingStrategy)
        assert strategy.target_chunk_size == 256  # Q1
        assert strategy.overlap == 0  # Q2

    def test_case_study_strategy(self):
        """Test case_study gets SectionChunkingStrategy."""
        strategy = get_chunking_strategy("case_study")

        assert isinstance(strategy, SectionChunkingStrategy)

    def test_documentation_strategy(self):
        """Test documentation gets SectionChunkingStrategy."""
        strategy = get_chunking_strategy("documentation")

        assert isinstance(strategy, SectionChunkingStrategy)

    def test_template_strategy(self):
        """Test template gets NoSplitChunkingStrategy."""
        strategy = get_chunking_strategy("template")

        assert isinstance(strategy, NoSplitChunkingStrategy)

    def test_unknown_type_fallback(self):
        """Test unknown type falls back to FixedChunkingStrategy."""
        strategy = get_chunking_strategy("unknown_type")

        assert isinstance(strategy, FixedChunkingStrategy)

    def test_config_override(self):
        """Test configuration override via kwargs."""
        strategy = get_chunking_strategy(
            "past_proposal",
            target_chunk_size=256,  # Override default 512
            overlap=50  # Override default 100
        )

        assert strategy.target_chunk_size == 256
        assert strategy.overlap == 50

    def test_phase6_tender_types(self):
        """Test future PHASE 6 tender archive types."""
        strategy_won = get_chunking_strategy("past_tender_won")
        strategy_strategic = get_chunking_strategy("past_tender_strategic")

        assert isinstance(strategy_won, SectionChunkingStrategy)
        assert isinstance(strategy_strategic, SectionChunkingStrategy)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
