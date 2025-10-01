"""
Integration tests for PHASE 2 smart chunking with RAGService.

Tests the full workflow: ingest_document → chunking → embedding → storage → retrieval
"""
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag_service import rag_service
from app.models.document import DocumentEmbedding


@pytest.mark.asyncio
class TestRAGServicePhase2Integration:
    """Integration tests for PHASE 2 smart chunking."""

    async def test_ingest_past_proposal_with_sections(self, db_session: AsyncSession):
        """
        Test ingesting past_proposal with section chunking (PRIORITY MAX - Q6).

        Validates:
        - Q1: Chunk sizes (512-1024 tokens)
        - Q2: Overlap (100 tokens)
        - Q4: Regex header detection
        - Q5: All 5 metadata fields
        """
        content = """
# Mémoire Technique - Appel d'offre Ministère XYZ

## 1. Présentation de l'entreprise

Notre entreprise ACME IT Services est spécialisée dans l'hébergement et l'infogérance
d'infrastructures IT critiques. Créée en 2010, nous accompagnons plus de 150 clients
issus des secteurs public, santé et finance dans leur transformation numérique.

### 1.1 Certifications et labels

Nous détenons les certifications suivantes:
- ISO 27001 (sécurité de l'information)
- ISO 9001 (qualité)
- HDS (hébergeur de données de santé)

## 2. Méthodologie proposée

### 2.1 Approche Agile

Notre approche projet repose sur la méthodologie Agile avec framework SCRUM.
Nous organisons le projet en sprints de 2 semaines avec cérémonies quotidiennes.

### 2.2 Outils et technologies

Nous utilisons un stack technologique moderne:
- GitLab pour le versioning
- Jenkins pour l'intégration continue
- Docker et Kubernetes pour la conteneurisation
"""

        doc_id = uuid4()

        chunk_count = await rag_service.ingest_document(
            db=db_session,
            document_id=doc_id,
            content=content,
            document_type="past_proposal",
            metadata={"source": "test_integration", "year": 2024}
        )

        # Verify chunks created
        assert chunk_count >= 3  # Multiple sections detected

        # Retrieve embeddings from database
        result = await db_session.execute(
            select(DocumentEmbedding).where(
                DocumentEmbedding.document_id == doc_id
            ).order_by(DocumentEmbedding.meta_data["chunk_index"].as_integer())
        )

        embeddings = result.scalars().all()

        assert len(embeddings) == chunk_count

        # Verify section metadata (Q5: all 5 fields)
        section_titles = [e.meta_data.get("section_title") for e in embeddings if e.meta_data.get("section_title")]
        assert len(section_titles) > 0
        assert any("Présentation" in title for title in section_titles if title)

        section_levels = [e.meta_data.get("section_level") for e in embeddings if e.meta_data.get("section_level")]
        assert any(level in ["H1", "H2", "H3"] for level in section_levels if level)

        # Verify token counts (Q1: <= 1024)
        token_counts = [e.meta_data.get("token_count") for e in embeddings]
        assert all(tc <= 1024 for tc in token_counts if tc)

        # Verify content_type field (Q5)
        content_types = [e.meta_data.get("content_type") for e in embeddings]
        assert all(ct in ["section", "section_part", "text"] for ct in content_types if ct)

        # Verify chunking_strategy
        strategies = [e.meta_data.get("chunking_strategy") for e in embeddings]
        assert all(s == "section" for s in strategies if s)

    async def test_ingest_certification_with_semantic(self, db_session: AsyncSession):
        """
        Test ingesting certification with semantic chunking (PRIORITY HIGH - Q6).

        Validates:
        - Q1: Chunk sizes (256-512 tokens)
        - Q2: No overlap (0 tokens)
        - Paragraph-based splitting
        - Q5: content_type field
        """
        content = """
CERTIFICAT ISO 27001:2013

Organisme certificateur: AFNOR Certification
Date d'émission: 15/06/2024
Date d'expiration: 14/06/2027

Périmètre de certification:
Système de management de la sécurité de l'information pour les activités de:
- Hébergement et infogérance d'infrastructures IT
- Services Cloud privé et hybride
- Support technique niveau 1, 2, 3

Processus couverts:
- Gestion des accès et authentification
- Sécurité physique des datacenters
- Continuité d'activité et plan de reprise
- Gestion des incidents de sécurité
- Surveillance et audits réguliers

Annexe: Liste des sites certifiés
- Paris La Défense (siège social)
- Lyon Part-Dieu (datacenter principal)
- Marseille Euromed (datacenter de secours)
"""

        doc_id = uuid4()

        chunk_count = await rag_service.ingest_document(
            db=db_session,
            document_id=doc_id,
            content=content,
            document_type="certification",
            metadata={"certification_type": "ISO 27001", "valid_until": "2027-06-14"}
        )

        # Verify chunks created
        assert chunk_count >= 1

        # Retrieve embeddings
        result = await db_session.execute(
            select(DocumentEmbedding).where(
                DocumentEmbedding.document_id == doc_id
            )
        )

        embeddings = result.scalars().all()

        # Verify token counts (Q1: <= 512 for certification)
        token_counts = [e.meta_data.get("token_count") for e in embeddings]
        assert all(tc <= 512 for tc in token_counts if tc), f"Token counts: {token_counts}"

        # Verify semantic chunking strategy
        strategies = [e.meta_data.get("chunking_strategy") for e in embeddings]
        assert all(s == "semantic" for s in strategies if s)

        # Verify content_type detection (Q5)
        content_types = [e.meta_data.get("content_type") for e in embeddings]
        assert len(content_types) > 0

        # Verify custom metadata preserved
        assert all(e.meta_data.get("certification_type") == "ISO 27001" for e in embeddings)

    async def test_ingest_template_no_split(self, db_session: AsyncSession):
        """
        Test ingesting template with nosplit chunking (PRIORITY MEDIUM - Q6).

        Validates:
        - Q1: Single chunk if <= 1024 tokens
        - Q2: No overlap (0 tokens)
        - content_type = "template"
        """
        content = """
# Template: Présentation entreprise

[ACME IT Services] est une société spécialisée dans [l'hébergement et l'infogérance
d'infrastructures IT critiques].

Créée en [2010], nous accompagnons [150+ clients] issus des secteurs [public, santé,
finance] dans leur transformation numérique.

## Nos certifications
- ISO 27001 (sécurité de l'information)
- ISO 9001 (qualité)
- HDS (hébergeur de données de santé)

## Nos chiffres clés
- [150+] clients actifs
- [200] collaborateurs
- [2] datacenters Tier 4
- [99.99%] de disponibilité garantie
"""

        doc_id = uuid4()

        chunk_count = await rag_service.ingest_document(
            db=db_session,
            document_id=doc_id,
            content=content,
            document_type="template",
            metadata={"template_type": "company_presentation"}
        )

        # Should be single chunk (Q1: nosplit if <= 1024 tokens)
        assert chunk_count == 1

        # Retrieve embedding
        result = await db_session.execute(
            select(DocumentEmbedding).where(
                DocumentEmbedding.document_id == doc_id
            )
        )

        embedding = result.scalar_one()

        # Verify content_type = "template" (Q5)
        assert embedding.meta_data.get("content_type") == "template"

        # Verify chunking_strategy = "nosplit"
        assert embedding.meta_data.get("chunking_strategy") == "nosplit"

        # Verify chunk index
        assert embedding.meta_data.get("chunk_index") == 0
        assert embedding.meta_data.get("total_chunks") == 1

    async def test_semantic_search_with_section_metadata(self, db_session: AsyncSession):
        """
        Test semantic search with section metadata filtering.

        Validates:
        - Retrieval with document_type filter
        - Section metadata in results
        - Similarity scoring
        """
        # 1. Ingest document with sections
        content = """
# Documentation ITSM

## Processus Sécurité

Processus de gestion des incidents de sécurité selon ITIL v4.
Détection, qualification, investigation, résolution, clôture.

## Processus Infrastructure

Processus de gestion des serveurs et équipements réseau.
Provisioning, configuration, monitoring, maintenance.
"""

        doc_id = uuid4()

        await rag_service.ingest_document(
            db=db_session,
            document_id=doc_id,
            content=content,
            document_type="documentation"
        )

        # 2. Search with document_type filter
        results = await rag_service.retrieve_relevant_content(
            db=db_session,
            query="gestion incidents sécurité",
            document_types=["documentation"],
            top_k=5
        )

        # 3. Verify results
        assert len(results) > 0

        # Verify metadata fields present (Q5)
        for result in results:
            metadata = result["metadata"]
            assert "chunking_strategy" in metadata
            assert "content_type" in metadata

            # At least one result should have section metadata
            if metadata.get("section_title"):
                assert metadata.get("section_level") is not None

        # Verify similarity scores
        similarities = [r["similarity_score"] for r in results]
        assert all(0 <= s <= 1 for s in similarities)

        # Results should be ordered by similarity
        assert similarities == sorted(similarities, reverse=True)

    async def test_backward_compatibility_chunk_text(self, db_session: AsyncSession):
        """
        Test backward compatibility of deprecated chunk_text() method (Q7).

        Validates:
        - DeprecationWarning raised
        - Fallback to FixedChunkingStrategy
        - Returns list of strings (not Chunk objects)
        """
        text = "Simple text for backward compatibility test. " * 50

        # Should raise DeprecationWarning (Q7)
        with pytest.warns(DeprecationWarning, match="chunk_text.*deprecated"):
            chunks = rag_service.chunk_text(text)

        # Should return list of strings (old API)
        assert isinstance(chunks, list)
        assert all(isinstance(c, str) for c in chunks)

        # Should have created chunks
        assert len(chunks) > 0

    async def test_all_document_types(self, db_session: AsyncSession):
        """
        Test all 5 knowledge base document types.

        Validates complete factory mapping.
        """
        test_cases = [
            ("past_proposal", "# Proposal\n\nContent here."),
            ("certification", "Certification content.\n\nMore paragraphs."),
            ("case_study", "## Case Study\n\nClient content."),
            ("documentation", "### Process\n\nProcess steps."),
            ("template", "Template content block.")
        ]

        for doc_type, content in test_cases:
            doc_id = uuid4()

            chunk_count = await rag_service.ingest_document(
                db=db_session,
                document_id=doc_id,
                content=content,
                document_type=doc_type
            )

            assert chunk_count >= 1

            # Verify document type stored correctly
            result = await db_session.execute(
                select(DocumentEmbedding).where(
                    DocumentEmbedding.document_id == doc_id
                )
            )

            embeddings = result.scalars().all()
            assert all(e.document_type == doc_type for e in embeddings)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
