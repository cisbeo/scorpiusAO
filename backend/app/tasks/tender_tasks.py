"""
Celery tasks for tender processing.
"""
from uuid import UUID

from app.core.celery_app import celery_app
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.parser_service import parser_service
from app.models.base import get_celery_session


@celery_app.task(bind=True, max_retries=3)
def process_new_tender(self, tender_id: str):
    """
    Complete tender processing pipeline - PLACEHOLDER.

    TODO: Implement full pipeline when needed.
    """
    print(f"✅ Placeholder: Tender {tender_id} queued for processing")
    return {
        "status": "success",
        "tender_id": tender_id,
        "message": "Tender queued (placeholder)"
    }


@celery_app.task
def generate_proposal_section(proposal_id: str, section_type: str):
    """
    Generate a proposal section using AI.

    Args:
        proposal_id: Proposal UUID
        section_type: Type of section to generate
    """
    # TODO: Implement section generation
    print(f"Generating {section_type} section for proposal {proposal_id}")
    return {"status": "success", "section_type": section_type}


@celery_app.task
def check_proposal_compliance(proposal_id: str):
    """
    Check proposal compliance against tender requirements.

    Args:
        proposal_id: Proposal UUID
    """
    # TODO: Implement compliance checking
    print(f"Checking compliance for proposal {proposal_id}")
    return {"status": "success", "compliance_score": 0.0}


@celery_app.task
def ingest_knowledge_base_document(document_id: str, document_type: str):
    """
    Ingest a document into the knowledge base.

    Args:
        document_id: Document UUID
        document_type: Type of document (certification, reference, case_study, etc.)
    """
    # TODO: Implement knowledge base ingestion
    print(f"Ingesting {document_type} document {document_id}")
    return {"status": "success", "document_id": document_id}


@celery_app.task(bind=True, max_retries=3)
def process_tender_document(self, document_id: str):
    """
    Process a single tender document (extract text, OCR if needed).
    SYNCHRONOUS version for Celery tasks.

    Args:
        document_id: TenderDocument UUID
    """
    from datetime import datetime
    from sqlalchemy import select
    from app.models.tender_document import TenderDocument
    from app.services.storage_service import storage_service

    try:
        print(f"📄 Processing document {document_id}")

        db = get_celery_session()
        try:
            # 1. Load document from database
            stmt = select(TenderDocument).where(TenderDocument.id == document_id)
            result = db.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            document.extraction_status = "processing"
            db.commit()

            # 2. Download file from MinIO
            file_content = storage_service.download_file(document.file_path)

            # 3. Extract text using parser_service (sync version)
            extraction_result = parser_service.extract_from_pdf_sync(
                file_content=file_content,
                use_ocr=False  # Try without OCR first
            )

            # If no text extracted, try with OCR
            if not extraction_result["text"].strip():
                print(f"⚠️  No text found, trying OCR for {document.filename}")
                extraction_result = parser_service.extract_from_pdf_sync(
                    file_content=file_content,
                    use_ocr=True
                )

            # 4. Update document with extracted text
            document.extracted_text = extraction_result["text"]
            document.page_count = extraction_result["page_count"]
            document.extraction_method = extraction_result["extraction_method"]
            document.extraction_meta_data = extraction_result["metadata"]
            document.extraction_status = "completed"
            document.processed_at = datetime.utcnow()

            db.commit()

            print(f"✅ Document {document_id} processed: {len(extraction_result['text'])} chars extracted")

            return {
                "status": "success",
                "document_id": document_id,
                "text_length": len(extraction_result["text"]),
                "page_count": extraction_result["page_count"]
            }
        finally:
            db.close()

    except Exception as exc:
        print(f"❌ Error processing document {document_id}: {exc}")

        # Update status to failed
        try:
            db = get_celery_session()
            try:
                stmt = select(TenderDocument).where(TenderDocument.id == document_id)
                result = db.execute(stmt)
                document = result.scalar_one_or_none()

                if document:
                    document.extraction_status = "failed"
                    document.extraction_error = str(exc)
                    db.commit()
            finally:
                db.close()
        except:
            pass

        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def process_tender_documents(self, tender_id: str):
    """
    Complete tender documents processing pipeline.
    SYNCHRONOUS version for Celery tasks.

    Steps:
    1. Extract content from all documents
    2. Create embeddings for all documents
    3. Run AI analysis
    4. Extract criteria
    5. Find similar tenders
    6. Generate content suggestions
    7. Save results and notify user

    Args:
        tender_id: Tender UUID
    """
    import time
    from datetime import datetime
    from sqlalchemy import select
    from app.models.tender import Tender
    from app.models.tender_document import TenderDocument
    from app.models.tender_analysis import TenderAnalysis

    start_time = time.time()

    try:
        db = get_celery_session()
        try:
            # Load tender
            stmt = select(Tender).where(Tender.id == tender_id)
            result = db.execute(stmt)
            tender = result.scalar_one_or_none()

            if not tender:
                raise ValueError(f"Tender {tender_id} not found")

            # Load documents
            stmt = select(TenderDocument).where(TenderDocument.tender_id == tender_id)
            result = db.execute(stmt)
            documents = result.scalars().all()

            if not documents:
                raise ValueError(f"No documents found for tender {tender_id}")

            print(f"🚀 Starting analysis of tender {tender_id} with {len(documents)} documents")

            # Create analysis record
            analysis = TenderAnalysis(
                tender_id=tender_id,
                analysis_status="processing"
            )
            db.add(analysis)
            db.commit()

            # STEP 1: Extract content from all documents (if not already done)
            print(f"📄 Step 1/6: Extracting content from {len(documents)} documents")
            all_content = []
            for doc in documents:
                if doc.extraction_status != "completed":
                    # Trigger extraction for this document
                    print(f"  - Extracting {doc.filename}...")
                    process_tender_document(str(doc.id))
                    # Reload document to get extracted text
                    db.refresh(doc)

                if doc.extracted_text:
                    all_content.append(f"=== {doc.document_type}: {doc.filename} ===\n\n{doc.extracted_text}")
                else:
                    print(f"⚠️  Warning: No text extracted from {doc.filename}")

            full_content = "\n\n".join(all_content)
            print(f"  ✓ Total content: {len(full_content)} characters")

            # STEP 2: Create embeddings
            print(f"🔍 Step 2/6: Creating embeddings")
            # TODO: Implement embedding creation
            # rag_service.ingest_document_sync(...)

            # STEP 3: AI Analysis
            print(f"🤖 Step 3/6: Running AI analysis")
            analysis_result = llm_service.analyze_tender_sync(full_content)

            # Save analysis results
            analysis.summary = analysis_result.get("summary", "")
            analysis.key_requirements = analysis_result.get("key_requirements", [])
            analysis.deadlines = analysis_result.get("deadlines", [])
            analysis.risks = analysis_result.get("risks", [])
            analysis.mandatory_documents = analysis_result.get("mandatory_documents", [])
            analysis.complexity_level = analysis_result.get("complexity_level", "moyenne")
            analysis.recommendations = analysis_result.get("recommendations", [])

            # Combine technical requirements, budget info, evaluation method, and contact info
            analysis.structured_data = {
                "technical_requirements": analysis_result.get("technical_requirements", {}),
                "budget_info": analysis_result.get("budget_info", {}),
                "evaluation_method": analysis_result.get("evaluation_method", ""),
                "contact_info": analysis_result.get("contact_info", {})
            }

            # STEP 4: Extract criteria
            print(f"📋 Step 4/6: Extracting evaluation criteria")
            criteria = llm_service.extract_criteria_sync(full_content)

            # DEBUG: Print what Claude returned
            import json
            print(f"🔍 DEBUG - Claude returned {len(criteria)} criteria:")
            print(json.dumps(criteria, indent=2, ensure_ascii=False))

            # Save criteria to database
            from app.models.tender import TenderCriterion
            for criterion_data in criteria:
                # Store extra fields in meta_data
                meta_data = {
                    "evaluation_method": criterion_data.get("evaluation_method"),
                    "sub_criteria": criterion_data.get("sub_criteria", [])
                }

                criterion = TenderCriterion(
                    tender_id=tender_id,
                    criterion_type=criterion_data.get("criterion_type", "autre"),
                    description=criterion_data.get("description", ""),
                    weight=str(criterion_data.get("weight", "")),
                    is_mandatory=str(criterion_data.get("is_mandatory", False)),
                    meta_data=meta_data
                )
                db.add(criterion)

            db.commit()
            print(f"  ✓ Saved {len(criteria)} criteria to database")

            # STEP 5: Find similar tenders
            print(f"🔎 Step 5/6: Finding similar past tenders")
            # TODO: Implement similarity search
            # similar = rag_service.find_similar_tenders_sync(db, tender_id)

            # STEP 6: Generate content suggestions
            print(f"💡 Step 6/6: Generating content suggestions")
            # TODO: Implement suggestion generation

            # Finalize analysis
            analysis.analysis_status = "completed"
            analysis.analyzed_at = datetime.utcnow()
            analysis.processing_time_seconds = int(time.time() - start_time)

            tender.status = "analyzed"

            db.commit()

            print(f"✅ Tender {tender_id} analysis completed in {analysis.processing_time_seconds}s")

            # TODO: Send WebSocket notification

            return {
                "status": "success",
                "tender_id": tender_id,
                "processing_time": analysis.processing_time_seconds
            }
        finally:
            db.close()

    except Exception as exc:
        print(f"❌ Error analyzing tender {tender_id}: {exc}")

        # Update analysis status to failed
        try:
            db = get_celery_session()
            try:
                stmt = select(TenderAnalysis).where(TenderAnalysis.tender_id == tender_id)
                result = db.execute(stmt)
                analysis = result.scalar_one_or_none()

                if analysis:
                    analysis.analysis_status = "failed"
                    analysis.error_message = str(exc)
                    db.commit()
            finally:
                db.close()
        except:
            pass

        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
