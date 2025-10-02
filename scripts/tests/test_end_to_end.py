"""
End-to-end test of the complete tender analysis pipeline.

Tests:
1. Upload PDFs from VSGP-AO
2. Extract with optimized parser (TOC detection, key sections, hierarchy)
3. Analyze with structured LLM prompt
4. Display results and metrics
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.core.config import settings
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.tasks.tender_tasks import process_tender_document
from app.services.llm_service import LLMService


async def main():
    print("=" * 80)
    print("🚀 TEST END-TO-END : Pipeline complet d'analyse d'appel d'offres")
    print("=" * 80)
    print()

    # Connect to database
    engine = create_engine(settings.database_url_sync)

    # Step 1: Create tender
    print("📋 ÉTAPE 1 : Création de l'appel d'offres")
    print("-" * 80)

    with Session(engine) as db:
        # Check if tender already exists
        existing = db.execute(text("""
            SELECT id FROM tenders WHERE title LIKE '%VSGP%Infogérance%'
        """)).first()

        if existing:
            tender_id = str(existing[0])
            print(f"✅ Appel d'offres existant trouvé : {tender_id}")
        else:
            tender = Tender(
                title="VSGP - Accord-cadre d'infogérance d'infrastructure et d'assistance utilisateur",
                organization="Établissement Public Territorial Vallée Sud Grand Paris",
                reference_number="25TIC06",
                deadline=datetime(2025, 4, 15),
                status="new",
                source="manual_upload"
            )
            db.add(tender)
            db.commit()
            db.refresh(tender)
            tender_id = str(tender.id)
            print(f"✅ Nouveau tender créé : {tender_id}")

    # Step 2: Upload PDFs
    print("\n📄 ÉTAPE 2 : Upload des documents PDF")
    print("-" * 80)

    pdf_dir = Path("/Users/cedric/Dev/projects/ScorpiusAO/Examples/VSGP-AO")
    pdf_files = {
        "CCTP.pdf": "cahier_charges_technique",
        "CCAP.pdf": "cahier_charges_administratif",
        "RC.pdf": "reglement_consultation"
    }

    document_ids = []

    with Session(engine) as db:
        for filename, doc_type in pdf_files.items():
            pdf_path = pdf_dir / filename

            if not pdf_path.exists():
                print(f"⚠️  Fichier non trouvé : {pdf_path}")
                continue

            # Check if document already uploaded
            existing_doc = db.execute(text("""
                SELECT id FROM tender_documents
                WHERE tender_id = :tender_id AND filename = :filename
            """), {"tender_id": tender_id, "filename": filename}).first()

            if existing_doc:
                doc_id = str(existing_doc[0])
                print(f"✅ Document existant : {filename} ({doc_id})")
                document_ids.append(doc_id)
                continue

            # Read file
            with open(pdf_path, 'rb') as f:
                file_content = f.read()

            # Upload to MinIO
            from app.services.storage_service import storage_service
            object_name = f"tenders/{tender_id}/{filename}"
            storage_service.upload_file(file_content, object_name, "application/pdf")

            # Create document record
            doc = TenderDocument(
                tender_id=tender_id,
                filename=filename,
                file_path=object_name,
                file_size=len(file_content),
                mime_type="application/pdf",
                document_type=doc_type,
                extraction_status="pending"
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            document_ids.append(str(doc.id))
            print(f"✅ Uploaded : {filename} ({len(file_content)} bytes) → {doc.id}")

    # Step 3: Process documents
    print(f"\n⚙️  ÉTAPE 3 : Traitement des documents ({len(document_ids)} PDFs)")
    print("-" * 80)

    all_sections = []
    processing_stats = []

    for doc_id in document_ids:
        print(f"\n🔄 Traitement du document {doc_id}...")

        try:
            result = process_tender_document(doc_id)
            print(f"   ✅ Succès : {result}")

            # Get sections from DB
            with Session(engine) as db:
                sections_result = db.execute(text("""
                    SELECT
                        ds.section_number,
                        ds.title,
                        ds.content,
                        ds.content_length,
                        ds.is_toc,
                        ds.is_key_section,
                        ds.parent_number,
                        ds.level,
                        ds.page,
                        td.filename
                    FROM document_sections ds
                    JOIN tender_documents td ON ds.document_id = td.id
                    WHERE ds.document_id = :doc_id
                    ORDER BY ds.page, ds.line
                """), {"doc_id": doc_id})

                doc_sections = []
                toc_count = 0
                key_count = 0

                for row in sections_result:
                    section = {
                        "section_number": row[0],
                        "title": row[1],
                        "content": row[2] or "",
                        "content_length": row[3],
                        "is_toc": row[4],
                        "is_key_section": row[5],
                        "parent_number": row[6],
                        "level": row[7],
                        "page": row[8],
                        "filename": row[9]
                    }
                    doc_sections.append(section)
                    all_sections.append(section)

                    if row[4]:  # is_toc
                        toc_count += 1
                    if row[5]:  # is_key_section
                        key_count += 1

                processing_stats.append({
                    "doc_id": doc_id,
                    "total_sections": len(doc_sections),
                    "toc_sections": toc_count,
                    "key_sections": key_count,
                    "regular_sections": len(doc_sections) - toc_count - key_count
                })

                print(f"   📊 Sections : {len(doc_sections)} total")
                print(f"      - TOC : {toc_count}")
                print(f"      - Clés : {key_count}")
                print(f"      - Régulières : {len(doc_sections) - toc_count - key_count}")

        except Exception as e:
            print(f"   ❌ Erreur : {e}")

    # Step 4: Display processing summary
    print(f"\n📊 ÉTAPE 4 : Résumé du traitement")
    print("-" * 80)

    total_sections = sum(s["total_sections"] for s in processing_stats)
    total_toc = sum(s["toc_sections"] for s in processing_stats)
    total_key = sum(s["key_sections"] for s in processing_stats)
    total_regular = sum(s["regular_sections"] for s in processing_stats)

    print(f"Total sections : {total_sections}")
    print(f"  - TOC : {total_toc} ({total_toc*100//total_sections}%)")
    print(f"  - Clés : {total_key} ({total_key*100//total_sections}%)")
    print(f"  - Régulières : {total_regular} ({total_regular*100//total_sections}%)")

    # Step 5: Build hierarchical structure and analyze
    print(f"\n🤖 ÉTAPE 5 : Analyse LLM avec structure hiérarchique")
    print("-" * 80)

    llm_service = LLMService()

    # Build hierarchical structure
    hierarchical_text = llm_service._build_hierarchical_structure(all_sections)

    print(f"Structure hiérarchique générée :")
    print(f"  - Caractères : {len(hierarchical_text):,}")
    print(f"  - Tokens estimés : ~{len(hierarchical_text) // 4:,}")
    print(f"  - Lignes : {len(hierarchical_text.splitlines())}")

    # Compare with flat
    flat_text = "\n\n".join([
        f"Section {s['section_number']}: {s['title']}\n{s['content']}"
        for s in all_sections
        if s['content'] and not s['is_toc']
    ])

    reduction = 100 - (len(hierarchical_text) * 100 // len(flat_text))
    print(f"\n📉 Optimisation :")
    print(f"  - Flat : {len(flat_text):,} chars (~{len(flat_text)//4:,} tokens)")
    print(f"  - Hiérarchique : {len(hierarchical_text):,} chars (~{len(hierarchical_text)//4:,} tokens)")
    print(f"  - Réduction : {reduction}%")

    cost_before = (len(flat_text) // 4) * 0.003 / 1000
    cost_after = (len(hierarchical_text) // 4) * 0.003 / 1000
    print(f"\n💰 Coût estimé (input only) :")
    print(f"  - Avant : ${cost_before:.4f}")
    print(f"  - Après : ${cost_after:.4f}")
    print(f"  - Économie : ${cost_before - cost_after:.4f} ({reduction}%)")

    # Show sample
    print(f"\n📄 Aperçu de la structure (500 premiers caractères) :")
    print("-" * 80)
    print(hierarchical_text[:500])
    print("...")
    print("-" * 80)

    # Step 6: Analyze with LLM (if API key configured)
    if settings.anthropic_api_key and settings.anthropic_api_key != "your_anthropic_key_here":
        print(f"\n🧠 ÉTAPE 6 : Analyse avec Claude API")
        print("-" * 80)

        metadata = {
            "tender_reference": "25TIC06",
            "organization": "Vallée Sud Grand Paris",
            "document_count": len(pdf_files),
            "total_pages": sum(s.get("page", 0) for s in all_sections if s.get("page"))
        }

        try:
            analysis = await llm_service.analyze_tender_structured(all_sections, metadata)

            print("✅ Analyse terminée !")
            print("\n📋 Résultats :")
            print(json.dumps(analysis, indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"❌ Erreur lors de l'analyse LLM : {e}")
    else:
        print(f"\n⚠️  ÉTAPE 6 : Analyse LLM ignorée (API key non configurée)")

    # Final summary
    print(f"\n" + "=" * 80)
    print("✅ TEST END-TO-END TERMINÉ")
    print("=" * 80)
    print(f"\n📊 Résumé final :")
    print(f"  - Tender ID : {tender_id}")
    print(f"  - Documents traités : {len(document_ids)}")
    print(f"  - Sections totales : {total_sections}")
    print(f"  - Optimisation tokens : -{reduction}%")
    print(f"  - Économie par analyse : ${cost_before - cost_after:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
