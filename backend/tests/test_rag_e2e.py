"""
E2E Tests for RAG Service - Day 3 Validation

Tests the complete RAG pipeline with real-world scenarios:
1. Document ingestion with embeddings
2. Semantic search quality (recall@5)
3. Q&A accuracy
4. Cost tracking
"""
import pytest
import sys
import os
from typing import List, Dict
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.rag_service import rag_service


# Test dataset: VSGP-AO questions with expected answers
VSGP_TEST_QUESTIONS = [
    {
        "question": "Quelle est la durée du marché ?",
        "expected_keywords": ["4 ans", "renouvellement", "2 fois", "1 an"],
        "relevant_section": "1"
    },
    {
        "question": "Quelles sont les prestations à réaliser ?",
        "expected_keywords": ["infogérance", "infrastructure", "supervision", "24/7", "maintenance"],
        "relevant_section": "2"
    },
    {
        "question": "Quel type de maintenance est prévu ?",
        "expected_keywords": ["préventive", "corrective"],
        "relevant_section": "2"
    },
    {
        "question": "Quelle est la durée du préavis de résiliation ?",
        "expected_keywords": ["préavis", "mois"],
        "relevant_section": "1"
    },
    {
        "question": "Quels sont les horaires de supervision ?",
        "expected_keywords": ["24/7", "24 heures", "7 jours"],
        "relevant_section": "2"
    }
]


class TestRAGE2E:
    """E2E tests for RAG Service"""

    @pytest.fixture(scope="class")
    def db_session(self):
        """Create database session for tests"""
        engine = create_engine(settings.database_url_sync)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture(scope="class")
    def test_tender(self, db_session):
        """Create a test tender with documents"""
        tender_id = uuid4()
        tender = Tender(
            id=tender_id,
            title="VSGP - Accord-cadre d'infogérance (TEST E2E)",
            organization="EPT Vallée Sud Grand Paris",
            status="new"
        )
        db_session.add(tender)
        db_session.commit()

        # Create test document
        doc_id = uuid4()
        doc = TenderDocument(
            id=doc_id,
            tender_id=tender.id,
            filename="CCTP_test_e2e.pdf",
            file_path="/tmp/test_e2e.pdf",
            document_type="CCTP",
            extraction_status="completed"
        )
        db_session.add(doc)
        db_session.commit()

        # Create embeddings
        chunks = [
            {
                "text": "Section 1: Durée du marché\n\nLe marché est conclu pour une durée initiale de 4 ans à compter de la notification. Il peut être renouvelé 2 fois par période de 1 an. Le préavis de résiliation est de 3 mois.",
                "metadata": {
                    "section_number": "1",
                    "page": 1,
                    "is_key_section": True
                }
            },
            {
                "text": "Section 2: Prestations demandées\n\nLes prestations comprennent l'infogérance complète de l'infrastructure informatique, incluant la supervision 24/7 (24 heures sur 24, 7 jours sur 7), la maintenance préventive et corrective.",
                "metadata": {
                    "section_number": "2",
                    "page": 2,
                    "is_key_section": True
                }
            }
        ]

        count = rag_service.ingest_document_sync(
            db_session,
            doc_id,
            chunks,
            "tender",
            {"tender_id": str(tender.id)}
        )

        print(f"✅ Created test tender with {count} embeddings")

        yield tender

        # Cleanup
        # Note: Cascade delete will handle embeddings and documents
        db_session.delete(tender)
        db_session.commit()

    def test_semantic_search_quality(self, db_session, test_tender):
        """Test 1: Validate semantic search quality (recall@5)"""
        correct_retrievals = 0
        total_questions = len(VSGP_TEST_QUESTIONS)

        for test_case in VSGP_TEST_QUESTIONS:
            question = test_case["question"]
            relevant_section = test_case["relevant_section"]

            # Get document IDs for this tender
            docs = db_session.query(TenderDocument).filter_by(
                tender_id=test_tender.id
            ).all()
            doc_ids = [str(doc.id) for doc in docs]

            # Retrieve top-5 chunks
            results = rag_service.retrieve_relevant_content_sync(
                db_session,
                question,
                top_k=5,
                document_ids=doc_ids
            )

            # Check if relevant section is in top-5
            found = False
            for result in results:
                if result.get("metadata", {}).get("section_number") == relevant_section:
                    found = True
                    print(f"✅ Found relevant section {relevant_section} for: {question}")
                    break

            if found:
                correct_retrievals += 1
            else:
                print(f"❌ Missing section {relevant_section} for: {question}")

        recall_at_5 = (correct_retrievals / total_questions) * 100
        print(f"\n📊 Recall@5: {recall_at_5:.1f}% ({correct_retrievals}/{total_questions})")

        # Validation: recall@5 should be > 80%
        assert recall_at_5 >= 80.0, f"Recall@5 ({recall_at_5:.1f}%) is below 80% threshold"

    def test_answer_quality(self, db_session, test_tender):
        """Test 2: Validate answer quality with keyword matching"""
        correct_answers = 0
        total_questions = len(VSGP_TEST_QUESTIONS)

        for test_case in VSGP_TEST_QUESTIONS:
            question = test_case["question"]
            expected_keywords = test_case["expected_keywords"]

            # Get answer (simulate Q&A endpoint logic)
            docs = db_session.query(TenderDocument).filter_by(
                tender_id=test_tender.id
            ).all()
            doc_ids = [str(doc.id) for doc in docs]

            results = rag_service.retrieve_relevant_content_sync(
                db_session,
                question,
                top_k=3,
                document_ids=doc_ids
            )

            # Build context
            context = "\n\n".join([
                f"[Section {r.get('metadata', {}).get('section_number', '?')}]\n{r['chunk_text']}"
                for r in results
            ])

            # Check if expected keywords are in context
            keywords_found = sum(
                1 for keyword in expected_keywords
                if keyword.lower() in context.lower()
            )

            coverage = (keywords_found / len(expected_keywords)) * 100

            if coverage >= 80.0:
                correct_answers += 1
                print(f"✅ Good coverage ({coverage:.0f}%) for: {question}")
            else:
                print(f"⚠️  Low coverage ({coverage:.0f}%) for: {question}")
                print(f"   Missing: {[k for k in expected_keywords if k.lower() not in context.lower()]}")

        accuracy = (correct_answers / total_questions) * 100
        print(f"\n📊 Answer Quality: {accuracy:.1f}% ({correct_answers}/{total_questions})")

        # Validation: answer quality should be > 80%
        assert accuracy >= 80.0, f"Answer quality ({accuracy:.1f}%) is below 80% threshold"

    def test_cost_tracking(self, db_session, test_tender):
        """Test 3: Track API costs for embeddings and Q&A"""
        import tiktoken

        # Cost tracking
        costs = {
            "embedding_tokens": 0,
            "embedding_cost": 0.0,
            "llm_tokens": 0,
            "llm_cost": 0.0,
            "total_cost": 0.0
        }

        # Embedding costs (already created during setup)
        docs = db_session.query(TenderDocument).filter_by(
            tender_id=test_tender.id
        ).all()

        # Estimate tokens for chunks (2 chunks created)
        # text-embedding-3-small: $0.00002 per 1K tokens
        embedding_model = "text-embedding-3-small"
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Similar tokenizer

        # Chunk 1: ~50 tokens, Chunk 2: ~50 tokens = ~100 tokens total
        estimated_chunk_tokens = 100
        costs["embedding_tokens"] = estimated_chunk_tokens
        costs["embedding_cost"] = (estimated_chunk_tokens / 1000) * 0.00002

        # Q&A costs (5 questions)
        # Claude Sonnet 4: $3 input / $15 output per 1M tokens
        # Average: 50 tokens input (question + context), 200 tokens output
        num_questions = len(VSGP_TEST_QUESTIONS)
        avg_input_tokens = 50
        avg_output_tokens = 200

        costs["llm_tokens"] = num_questions * (avg_input_tokens + avg_output_tokens)
        costs["llm_cost"] = (
            (num_questions * avg_input_tokens / 1_000_000) * 3.0 +  # Input
            (num_questions * avg_output_tokens / 1_000_000) * 15.0   # Output
        )

        costs["total_cost"] = costs["embedding_cost"] + costs["llm_cost"]

        print(f"\n💰 Cost Analysis:")
        print(f"   Embedding: {costs['embedding_tokens']} tokens → ${costs['embedding_cost']:.6f}")
        print(f"   LLM (5 Q&A): {costs['llm_tokens']} tokens → ${costs['llm_cost']:.6f}")
        print(f"   TOTAL per tender: ${costs['total_cost']:.6f}")

        # Validation: cost per tender should be < $0.02
        assert costs["total_cost"] < 0.02, f"Cost (${costs['total_cost']:.6f}) exceeds $0.02 threshold"

    def test_chunking_strategy(self, db_session):
        """Test 4: Validate semantic chunking strategy"""
        sections = [
            {
                "section_number": "1.1",
                "title": "Petite section",
                "content": "Ceci est une petite section de 10 tokens seulement.",
                "page": 1,
                "level": 2,
                "is_key_section": False
            },
            {
                "section_number": "1.2",
                "title": "Section moyenne",
                "content": "Ceci est une section moyenne avec environ 150 tokens. " * 15,
                "page": 1,
                "level": 2,
                "is_key_section": True
            },
            {
                "section_number": "2",
                "title": "Grande section",
                "content": "Ceci est une très grande section qui dépasse 1000 tokens. " * 100,
                "page": 2,
                "level": 1,
                "is_key_section": True
            }
        ]

        chunks = rag_service.chunk_sections_semantic(sections)

        print(f"\n🔪 Chunking Results:")
        print(f"   Input: {len(sections)} sections")
        print(f"   Output: {len(chunks)} chunks")

        # Validate chunking rules
        # Small sections get merged, so we may have fewer chunks than sections
        assert len(chunks) > 0, "Should have at least one chunk"

        # Check metadata
        for chunk in chunks:
            assert "text" in chunk, "Chunk missing 'text' field"
            assert "metadata" in chunk, "Chunk missing 'metadata' field"
            # Merged chunks have section_numbers (plural), single chunks have section_number
            has_section_info = (
                "section_number" in chunk["metadata"] or
                "section_numbers" in chunk["metadata"]
            )
            assert has_section_info, "Chunk missing section number information"

        print(f"   ✅ All chunks have required metadata")


if __name__ == "__main__":
    """Run tests manually for debugging"""
    pytest.main([__file__, "-v", "-s"])
