"""
E2E Pipeline Tests - Migrated from scripts/tests/test_fresh_e2e.py

Tests the complete tender processing pipeline:
1. Tender creation
2. Document upload to MinIO
3. Document extraction and section parsing
4. Embedding creation (RAG Service integration)
5. Hierarchical structure and LLM analysis

Modernized with pytest framework:
- Fixtures for database, tender, documents
- Assertions instead of print statements
- Markers for E2E and quality tests
- Proper cleanup and error handling
"""
import pytest
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.storage_service import storage_service
from app.services.llm_service import LLMService
from app.services.rag_service import rag_service
from app.tasks.tender_tasks import process_tender_document


# Expected results from VSGP-AO tender (validation targets)
EXPECTED_RESULTS = {
    "total_sections": 377,
    "min_sections": 350,  # Allow some variance
    "max_sections": 400,
    "toc_percentage_min": 30,  # At least 30% TOC
    "key_sections_percentage_min": 25,  # At least 25% key sections
    "min_itil_processes": 18,  # ITIL process detection
    "min_hierarchy_reduction": 10,  # At least 10% reduction with hierarchy
}


@pytest.fixture(scope="module")
def pdf_files_path():
    """Check if sample PDFs exist (skip if not available)"""
    real_pdfs_dir = Path("/app/real_pdfs")

    if not real_pdfs_dir.exists():
        pytest.skip(f"Sample PDFs not found: {real_pdfs_dir}")

    pdf_files = [
        ("CCTP.pdf", "cahier_charges_technique"),
        ("CCAP.pdf", "cahier_charges_administratif"),
        ("RC.pdf", "reglement_consultation")
    ]

    # Verify files exist
    for filename, _ in pdf_files:
        pdf_path = real_pdfs_dir / filename
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")

    return real_pdfs_dir, pdf_files


@pytest.fixture(scope="module")
def e2e_tender(db_session):
    """Create a test tender for E2E pipeline"""
    tender = Tender(
        id=uuid4(),
        title="VSGP - Accord-cadre d'infogérance d'infrastructure et d'assistance utilisateur",
        organization="Établissement Public Territorial Vallée Sud Grand Paris",
        reference_number="25TIC06",
        deadline=datetime(2025, 4, 15),
        status="new",
        source="manual_upload"
    )
    db_session.add(tender)
    db_session.commit()
    db_session.refresh(tender)

    print(f"\n✅ E2E Tender created: {tender.id}")
    print(f"   Title: {tender.title}")

    yield tender

    # Cleanup (cascade delete handles documents, sections, embeddings)
    db_session.delete(tender)
    db_session.commit()


@pytest.fixture(scope="module")
def uploaded_documents(db_session, e2e_tender, pdf_files_path):
    """Upload PDFs to MinIO and create document records"""
    real_pdfs_dir, pdf_files = pdf_files_path
    document_ids = []

    for filename, doc_type in pdf_files:
        pdf_path = real_pdfs_dir / filename

        # Read file
        with open(pdf_path, 'rb') as f:
            file_content = f.read()

        print(f"\n📤 Uploading: {filename} ({len(file_content):,} bytes)")

        # Upload to MinIO
        object_name = f"tenders/{e2e_tender.id}/{filename}"
        try:
            storage_service.upload_file(file_content, object_name, "application/pdf")
            print(f"   ✅ MinIO: {object_name}")
        except Exception as e:
            pytest.fail(f"MinIO upload failed for {filename}: {e}")

        # Create document record
        doc = TenderDocument(
            id=uuid4(),
            tender_id=e2e_tender.id,
            filename=filename,
            file_path=object_name,
            file_size=len(file_content),
            mime_type="application/pdf",
            document_type=doc_type,
            extraction_status="pending"
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        document_ids.append(str(doc.id))
        print(f"   ✅ DB: {doc.id} (status: pending)")

    assert len(document_ids) == 3, f"Expected 3 documents, got {len(document_ids)}"
    print(f"\n✅ {len(document_ids)} documents uploaded")

    return document_ids


@pytest.mark.e2e
@pytest.mark.slow
def test_create_tender(e2e_tender):
    """Test 1: Tender creation with all required fields"""
    assert e2e_tender.id is not None
    assert e2e_tender.title.startswith("VSGP")
    assert e2e_tender.organization == "Établissement Public Territorial Vallée Sud Grand Paris"
    assert e2e_tender.reference_number == "25TIC06"
    assert e2e_tender.status == "new"
    assert e2e_tender.source == "manual_upload"
    print(f"✅ Tender validation passed: {e2e_tender.id}")


@pytest.mark.e2e
@pytest.mark.slow
def test_upload_documents(uploaded_documents):
    """Test 2: Document upload to MinIO and database"""
    assert len(uploaded_documents) == 3, "Expected 3 documents (CCTP, CCAP, RC)"

    for doc_id in uploaded_documents:
        # Validate UUID format
        try:
            uuid_obj = uuid4()
            # Just verify it's a valid UUID string
            assert len(doc_id) == 36, f"Invalid UUID format: {doc_id}"
        except Exception as e:
            pytest.fail(f"Invalid document ID format: {doc_id}")

    print(f"✅ Document upload validation passed: {len(uploaded_documents)} documents")


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.quality
def test_extract_sections(db_session, uploaded_documents):
    """Test 3: Extract sections from all documents using Celery pipeline"""
    processing_results = []

    for i, doc_id in enumerate(uploaded_documents, 1):
        # Get filename
        doc = db_session.execute(text("""
            SELECT filename FROM tender_documents WHERE id = :id
        """), {"id": doc_id}).first()
        filename = doc[0] if doc else "unknown"

        print(f"\n[{i}/{len(uploaded_documents)}] 🔄 Processing: {filename}")

        start_time = time.time()

        try:
            result = process_tender_document(doc_id)
            elapsed = time.time() - start_time

            print(f"    ✅ Success in {elapsed:.1f}s")
            print(f"       {result}")

            # Get detailed stats
            stats = db_session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN is_toc THEN 1 END) as toc,
                    COUNT(CASE WHEN is_key_section THEN 1 END) as key_sections,
                    COUNT(CASE WHEN content_length > 0 THEN 1 END) as with_content,
                    SUM(content_length) as total_content_length
                FROM document_sections
                WHERE document_id = :doc_id
            """), {"doc_id": doc_id}).first()

            # Validate section extraction
            assert stats[0] > 0, f"No sections extracted for {filename}"
            assert stats[3] > 0, f"No sections with content for {filename}"

            processing_results.append({
                "filename": filename,
                "doc_id": doc_id,
                "total_sections": stats[0],
                "toc_sections": stats[1],
                "key_sections": stats[2],
                "sections_with_content": stats[3],
                "total_content_length": stats[4] or 0,
                "elapsed_time": elapsed
            })

            print(f"    📊 Sections: {stats[0]} total")
            print(f"       - TOC: {stats[1]}")
            print(f"       - Key: {stats[2]}")
            print(f"       - With content: {stats[3]}")

        except Exception as e:
            pytest.fail(f"Document processing failed for {filename}: {e}")

    # Global validation
    total_sections = sum(r["total_sections"] for r in processing_results)
    total_toc = sum(r["toc_sections"] for r in processing_results)
    total_key = sum(r["key_sections"] for r in processing_results)
    total_with_content = sum(r["sections_with_content"] for r in processing_results)

    print(f"\n📊 Global Statistics:")
    print(f"   Total sections: {total_sections}")
    print(f"   TOC: {total_toc} ({total_toc*100//total_sections if total_sections > 0 else 0}%)")
    print(f"   Key: {total_key} ({total_key*100//total_sections if total_sections > 0 else 0}%)")
    print(f"   With content: {total_with_content}")

    # Assertions based on VSGP-AO expected results
    assert total_sections >= EXPECTED_RESULTS["min_sections"], \
        f"Expected at least {EXPECTED_RESULTS['min_sections']} sections, got {total_sections}"
    assert total_sections <= EXPECTED_RESULTS["max_sections"], \
        f"Expected at most {EXPECTED_RESULTS['max_sections']} sections, got {total_sections}"

    # Validate percentages
    toc_percentage = (total_toc * 100 // total_sections) if total_sections > 0 else 0
    key_percentage = (total_key * 100 // total_sections) if total_sections > 0 else 0

    assert toc_percentage >= EXPECTED_RESULTS["toc_percentage_min"], \
        f"TOC percentage ({toc_percentage}%) below {EXPECTED_RESULTS['toc_percentage_min']}%"
    assert key_percentage >= EXPECTED_RESULTS["key_sections_percentage_min"], \
        f"Key sections percentage ({key_percentage}%) below {EXPECTED_RESULTS['key_sections_percentage_min']}%"

    print(f"✅ Section extraction validation passed: {total_sections} sections")


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.rag
def test_create_embeddings(db_session, e2e_tender, uploaded_documents):
    """Test 4: Create embeddings for extracted sections (RAG Service integration)"""
    # Get all key sections from extracted documents
    sections_result = db_session.execute(text("""
        SELECT
            ds.id,
            ds.section_number,
            ds.title,
            ds.content,
            ds.page,
            ds.is_key_section,
            ds.is_toc,
            ds.level,
            td.id as doc_id
        FROM document_sections ds
        JOIN tender_documents td ON ds.document_id = td.id
        WHERE td.tender_id = :tender_id
          AND ds.is_toc = false
          AND ds.content IS NOT NULL
          AND ds.content_length > 0
        ORDER BY ds.page, ds.line
    """), {"tender_id": str(e2e_tender.id)}).fetchall()

    sections = []
    for row in sections_result:
        sections.append({
            "id": str(row[0]),
            "section_number": row[1],
            "title": row[2],
            "content": row[3],
            "page": row[4],
            "is_key_section": row[5],
            "is_toc": row[6],
            "level": row[7] or 1,
            "document_id": str(row[8])
        })

    assert len(sections) > 0, "No sections found for embedding creation"
    print(f"\n📊 Creating embeddings for {len(sections)} sections")

    # Chunk sections semantically
    chunks = rag_service.chunk_sections_semantic(
        sections,
        max_tokens=1000,
        min_tokens=100
    )

    assert len(chunks) > 0, "Chunking produced no results"
    print(f"   ✅ Chunking: {len(sections)} sections → {len(chunks)} chunks")

    # Get first document for embedding storage
    doc_id = sections[0]["document_id"]

    # Ingest chunks into RAG
    embedding_count = rag_service.ingest_document_sync(
        db=db_session,
        document_id=doc_id,
        chunks=chunks,
        document_type="tender",
        metadata={"tender_id": str(e2e_tender.id)}
    )

    assert embedding_count > 0, "No embeddings created"
    assert embedding_count == len(chunks), \
        f"Expected {len(chunks)} embeddings, got {embedding_count}"

    print(f"   ✅ Created {embedding_count} embeddings")

    # Test retrieval
    test_query = "Quelle est la durée du marché ?"
    results = rag_service.retrieve_relevant_content_sync(
        db=db_session,
        query=test_query,
        top_k=5,
        document_ids=[doc_id]
    )

    assert len(results) > 0, "Retrieval returned no results"
    assert results[0]["similarity_score"] > 0.5, \
        f"Top result similarity ({results[0]['similarity_score']}) too low"

    print(f"   ✅ Retrieval test: {len(results)} results, top similarity: {results[0]['similarity_score']:.2f}")
    print(f"✅ Embedding creation and retrieval validation passed")


@pytest.mark.e2e
@pytest.mark.quality
def test_hierarchical_structure(db_session, e2e_tender):
    """Test 5: Hierarchical structure generation and optimization"""
    # Get all sections
    sections_result = db_session.execute(text("""
        SELECT
            section_type,
            section_number,
            parent_number,
            title,
            content,
            content_length,
            is_toc,
            is_key_section,
            level,
            page
        FROM document_sections ds
        JOIN tender_documents td ON ds.document_id = td.id
        WHERE td.tender_id = :tender_id
        ORDER BY ds.page, ds.line
    """), {"tender_id": str(e2e_tender.id)})

    all_sections = []
    for row in sections_result:
        all_sections.append({
            "type": row[0],
            "section_number": row[1],
            "parent_number": row[2],
            "title": row[3],
            "content": row[4] or "",
            "content_length": row[5],
            "is_toc": row[6],
            "is_key_section": row[7],
            "level": row[8],
            "page": row[9]
        })

    assert len(all_sections) > 0, "No sections found for hierarchy test"
    print(f"\n📊 Testing hierarchical structure with {len(all_sections)} sections")

    # Build hierarchical structure
    llm_service = LLMService()
    hierarchical_text = llm_service._build_hierarchical_structure(all_sections)

    assert len(hierarchical_text) > 0, "Hierarchical structure is empty"

    # Calculate flat text for comparison
    flat_text = "\n\n".join([
        f"Section {s['section_number']}: {s['title']}\n{s['content']}"
        for s in all_sections
        if s['content'] and not s['is_toc']
    ])

    assert len(flat_text) > 0, "Flat text is empty"

    # Calculate reduction
    reduction = 100 - (len(hierarchical_text) * 100 // len(flat_text)) if len(flat_text) > 0 else 0

    print(f"   Hierarchical: {len(hierarchical_text):,} chars (~{len(hierarchical_text)//4:,} tokens)")
    print(f"   Flat: {len(flat_text):,} chars (~{len(flat_text)//4:,} tokens)")
    print(f"   Reduction: {reduction}%")

    # Validate reduction
    assert reduction >= EXPECTED_RESULTS["min_hierarchy_reduction"], \
        f"Hierarchy reduction ({reduction}%) below {EXPECTED_RESULTS['min_hierarchy_reduction']}%"

    # Cost estimation
    cost_before = (len(flat_text) // 4) * 0.003 / 1000
    cost_after = (len(hierarchical_text) // 4) * 0.003 / 1000
    savings = cost_before - cost_after

    print(f"   Cost savings: ${savings:.4f} per analysis ({reduction}% reduction)")

    # Verify parent-child relationships
    hierarchy_check = db_session.execute(text("""
        SELECT
            child.section_number,
            parent.section_number
        FROM document_sections child
        JOIN tender_documents td ON child.document_id = td.id
        LEFT JOIN document_sections parent ON child.parent_id = parent.id
        WHERE td.tender_id = :tender_id
          AND child.parent_id IS NOT NULL
        LIMIT 10
    """), {"tender_id": str(e2e_tender.id)}).fetchall()

    if hierarchy_check:
        print(f"   ✅ Parent-child relationships: {len(hierarchy_check)} examples")
        for row in hierarchy_check[:3]:
            print(f"      • {row[0]} → parent: {row[1]}")

    print(f"✅ Hierarchical structure validation passed: {reduction}% reduction")


@pytest.mark.e2e
@pytest.mark.quality
def test_itil_process_detection(db_session, e2e_tender):
    """Test 6: Validate ITIL process detection (section 4.1.5.x)"""
    # Query for ITIL sections (section 4.1.5.x in VSGP-AO)
    itil_sections = db_session.execute(text("""
        SELECT
            section_number,
            title,
            content_length
        FROM document_sections ds
        JOIN tender_documents td ON ds.document_id = td.id
        WHERE td.tender_id = :tender_id
          AND section_number LIKE '4.1.5%'
        ORDER BY section_number
    """), {"tender_id": str(e2e_tender.id)}).fetchall()

    itil_count = len(itil_sections)

    print(f"\n📊 ITIL Process Detection:")
    print(f"   Found: {itil_count} ITIL process sections")

    if itil_sections:
        for section in itil_sections[:5]:
            print(f"   • {section[0]}: {section[1][:60]}")

    # Validate ITIL detection (VSGP-AO has 18-19 ITIL processes)
    assert itil_count >= EXPECTED_RESULTS["min_itil_processes"], \
        f"Expected at least {EXPECTED_RESULTS['min_itil_processes']} ITIL processes, found {itil_count}"

    print(f"✅ ITIL process detection validation passed: {itil_count} processes")


if __name__ == "__main__":
    """Run tests manually for debugging"""
    pytest.main([__file__, "-v", "-s"])
