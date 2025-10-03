"""
Tests for RAG Service.
"""
import pytest
from uuid import uuid4
from app.services.rag_service import rag_service
from app.models.base import get_celery_session


class TestRAGServiceSync:
    """Test suite for synchronous RAG methods."""

    def test_create_embedding_sync(self):
        """Test sync embedding creation."""
        text = "Quels sont les critères d'évaluation de cet appel d'offres ?"

        embedding = rag_service.create_embedding_sync(text)

        assert len(embedding) == 1536  # text-embedding-3-small dimension
        assert all(isinstance(x, float) for x in embedding)
        print(f"✅ Embedding created: {len(embedding)} dimensions")

    def test_chunk_sections_semantic(self):
        """Test semantic chunking."""
        sections = [
            {
                "section_number": "1",
                "title": "Introduction",
                "content": "Ceci est une introduction courte.",
                "page": 1,
                "line": 0,
                "is_toc": False,
                "is_key_section": False,
                "parent_number": None,
                "level": 1
            },
            {
                "section_number": "2",
                "title": "Critères d'évaluation",
                "content": "Les critères sont les suivants: technique (60%), prix (40%).",
                "page": 2,
                "line": 10,
                "is_toc": False,
                "is_key_section": True,
                "parent_number": None,
                "level": 1
            },
            {
                "section_number": "3",
                "title": "Table des matières",
                "content": "Page 1 ... 5\nPage 2 ... 10",
                "page": 1,
                "line": 5,
                "is_toc": True,  # Should be filtered out
                "is_key_section": False,
                "parent_number": None,
                "level": 1
            }
        ]

        chunks = rag_service.chunk_sections_semantic(sections, max_tokens=1000, min_tokens=100)

        # TOC should be filtered out
        assert len(chunks) <= 2

        # Check metadata preservation
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert "section_number" in chunk["metadata"] or "section_numbers" in chunk["metadata"]

        print(f"✅ Chunking: {len(sections)} sections → {len(chunks)} chunks")

    def test_ingest_and_retrieve_sync(self):
        """Test E2E ingestion and retrieval."""
        db = get_celery_session()

        try:
            # Prepare test chunks
            test_doc_id = uuid4()
            chunks = [
                {
                    "text": "Les critères d'évaluation sont: technique 60%, financier 40%.",
                    "metadata": {"section_number": "4.1", "page": 5, "is_key_section": True}
                },
                {
                    "text": "La date limite de remise des offres est le 15 novembre 2024.",
                    "metadata": {"section_number": "2.3", "page": 3, "is_key_section": True}
                }
            ]

            # Ingest
            count = rag_service.ingest_document_sync(
                db=db,
                document_id=test_doc_id,
                chunks=chunks,
                document_type="tender",
                metadata={"test": True}
            )

            assert count == 2
            print(f"✅ Ingested {count} chunks")

            # Retrieve
            query = "Quels sont les critères d'évaluation ?"
            results = rag_service.retrieve_relevant_content_sync(
                db=db,
                query=query,
                top_k=1,
                document_types=["tender"]
            )

            assert len(results) >= 1
            assert results[0]["similarity_score"] > 0.5
            assert "critères" in results[0]["chunk_text"].lower()

            print(f"✅ Retrieved {len(results)} results, top similarity: {results[0]['similarity_score']:.2f}")

            # Cleanup
            from app.models.document import DocumentEmbedding
            db.query(DocumentEmbedding).filter_by(document_id=test_doc_id).delete()
            db.commit()

        finally:
            db.close()

    def test_small_section_merging(self):
        """Test that small sections are merged correctly."""
        sections = [
            {
                "section_number": "1",
                "title": "Short",
                "content": "Tiny content.",  # Very small
                "page": 1,
                "line": 0,
                "is_toc": False,
                "is_key_section": False,
                "parent_number": None,
                "level": 1
            },
            {
                "section_number": "2",
                "title": "Also Short",
                "content": "Also tiny.",  # Very small
                "page": 1,
                "line": 2,
                "is_toc": False,
                "is_key_section": False,
                "parent_number": None,
                "level": 1
            }
        ]

        chunks = rag_service.chunk_sections_semantic(sections, max_tokens=1000, min_tokens=100)

        # Should be merged into 1 chunk
        assert len(chunks) == 1
        assert chunks[0]["metadata"].get("is_merged") == True
        assert "Section 1: Short" in chunks[0]["text"]
        assert "Section 2: Also Short" in chunks[0]["text"]

        print(f"✅ Small sections merged correctly: 2 sections → 1 chunk")

    def test_large_section_splitting(self):
        """Test that large sections are split correctly."""
        # Create a large section (> 1000 tokens = ~4000 chars)
        large_content = " ".join(["word"] * 5000)  # ~5000 words = ~1250 tokens

        sections = [
            {
                "section_number": "1",
                "title": "Large Section",
                "content": large_content,
                "page": 1,
                "line": 0,
                "is_toc": False,
                "is_key_section": True,
                "parent_number": None,
                "level": 1
            }
        ]

        chunks = rag_service.chunk_sections_semantic(sections, max_tokens=1000, min_tokens=100)

        # Should be split into multiple chunks
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["metadata"].get("is_split") == True
            assert chunk["metadata"]["section_number"] == "1"

        print(f"✅ Large section split correctly: 1 section → {len(chunks)} chunks")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
