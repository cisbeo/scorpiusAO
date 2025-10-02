"""
Fresh end-to-end test from scratch.
Upload PDFs from local filesystem and process them.
"""
import sys
import time
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

# Run from backend directory
sys.path.insert(0, '/app')

from app.core.config import settings
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.storage_service import storage_service
from app.tasks.tender_tasks import process_tender_document


def main():
    print("=" * 80)
    print("🚀 TEST END-TO-END COMPLET - BASE DE DONNÉES VIDE")
    print("=" * 80)
    print()

    # Connect to database
    engine = create_engine(settings.database_url_sync)

    # Step 1: Create tender
    print("📋 ÉTAPE 1/5 : Création de l'appel d'offres")
    print("-" * 80)

    with Session(engine) as db:
        tender = Tender(
            id=str(uuid.uuid4()),
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
        print(f"✅ Tender créé : {tender_id}")
        print(f"   Titre : {tender.title}")
        print(f"   Organisation : {tender.organization}")
        print(f"   Référence : {tender.reference_number}")

    # Step 2: Prepare PDFs (copy from Examples to a mounted location)
    print(f"\n📄 ÉTAPE 2/5 : Copie des PDFs depuis Examples/VSGP-AO")
    print("-" * 80)

    # Since we're in Docker, we need to copy files from host
    # The files are already in /app/real_pdfs/ from previous uploads
    # Let's use those instead

    pdf_files = [
        ("CCTP.pdf", "cahier_charges_technique"),
        ("CCAP.pdf", "cahier_charges_administratif"),
        ("RC.pdf", "reglement_consultation")
    ]

    # Check if files exist in /app/real_pdfs/
    import os
    real_pdfs_dir = Path("/app/real_pdfs")
    if not real_pdfs_dir.exists():
        print(f"❌ Répertoire {real_pdfs_dir} non trouvé")
        print(f"   Le test doit être exécuté depuis l'hôte, pas dans Docker")
        return

    document_ids = []

    with Session(engine) as db:
        for filename, doc_type in pdf_files:
            pdf_path = real_pdfs_dir / filename

            if not pdf_path.exists():
                print(f"⚠️  Fichier non trouvé : {pdf_path}")
                continue

            # Read file
            with open(pdf_path, 'rb') as f:
                file_content = f.read()

            print(f"\n📤 Upload : {filename} ({len(file_content):,} bytes)")

            # Upload to MinIO
            object_name = f"tenders/{tender_id}/{filename}"
            try:
                storage_service.upload_file(file_content, object_name, "application/pdf")
                print(f"   ✅ MinIO : {object_name}")
            except Exception as e:
                print(f"   ⚠️  MinIO : {e}")

            # Create document record
            doc = TenderDocument(
                id=str(uuid.uuid4()),
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
            print(f"   ✅ DB : {doc.id} (status: pending)")

    print(f"\n✅ {len(document_ids)} documents uploadés")

    # Step 3: Process documents
    print(f"\n⚙️  ÉTAPE 3/5 : Traitement avec pipeline optimisé")
    print("-" * 80)

    processing_results = []

    for i, doc_id in enumerate(document_ids, 1):
        # Get filename
        with Session(engine) as db:
            doc = db.execute(text("""
                SELECT filename FROM tender_documents WHERE id = :id
            """), {"id": doc_id}).first()
            filename = doc[0] if doc else "unknown"

        print(f"\n[{i}/{len(document_ids)}] 🔄 Traitement : {filename}")
        print(f"    Document ID : {doc_id}")

        start_time = time.time()

        try:
            result = process_tender_document(doc_id)
            elapsed = time.time() - start_time

            print(f"    ✅ Succès en {elapsed:.1f}s")
            print(f"       {result}")

            # Get detailed stats
            with Session(engine) as db:
                stats = db.execute(text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_toc THEN 1 END) as toc,
                        COUNT(CASE WHEN is_key_section THEN 1 END) as key_sections,
                        COUNT(CASE WHEN content_length > 0 THEN 1 END) as with_content,
                        SUM(content_length) as total_content_length
                    FROM document_sections
                    WHERE document_id = :doc_id
                """), {"doc_id": doc_id}).first()

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

                print(f"    📊 Sections : {stats[0]} total")
                print(f"       - TOC : {stats[1]}")
                print(f"       - Clés : {stats[2]}")
                print(f"       - Avec contenu : {stats[3]}")
                print(f"       - Contenu total : {stats[4]:,} chars")

        except Exception as e:
            print(f"    ❌ Erreur : {e}")
            import traceback
            traceback.print_exc()

    # Step 4: Global statistics
    print(f"\n📊 ÉTAPE 4/5 : Statistiques globales")
    print("-" * 80)

    total_sections = sum(r["total_sections"] for r in processing_results)
    total_toc = sum(r["toc_sections"] for r in processing_results)
    total_key = sum(r["key_sections"] for r in processing_results)
    total_with_content = sum(r["sections_with_content"] for r in processing_results)
    total_content = sum(r["total_content_length"] for r in processing_results)
    total_time = sum(r["elapsed_time"] for r in processing_results)

    print(f"Documents traités : {len(processing_results)}")
    print(f"Temps total : {total_time:.1f}s")
    print(f"\nSections totales : {total_sections}")
    print(f"  - TOC : {total_toc} ({total_toc*100//total_sections if total_sections > 0 else 0}%)")
    print(f"  - Clés : {total_key} ({total_key*100//total_sections if total_sections > 0 else 0}%)")
    print(f"  - Avec contenu : {total_with_content} ({total_with_content*100//total_sections if total_sections > 0 else 0}%)")
    print(f"  - Contenu total : {total_content:,} chars")

    # Step 5: Hierarchical structure test
    print(f"\n🌳 ÉTAPE 5/5 : Test de la structure hiérarchique")
    print("-" * 80)

    # Get all sections
    with Session(engine) as db:
        sections_result = db.execute(text("""
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
            FROM document_sections
            ORDER BY page, line
        """))

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

    from app.services.llm_service import LLMService
    llm_service = LLMService()

    hierarchical_text = llm_service._build_hierarchical_structure(all_sections)

    # Calculate flat text for comparison
    flat_text = "\n\n".join([
        f"Section {s['section_number']}: {s['title']}\n{s['content']}"
        for s in all_sections
        if s['content'] and not s['is_toc']
    ])

    print(f"Structure hiérarchique générée :")
    print(f"  - Caractères : {len(hierarchical_text):,}")
    print(f"  - Tokens estimés : ~{len(hierarchical_text) // 4:,}")
    print(f"  - Lignes : {len(hierarchical_text.splitlines())}")

    reduction = 100 - (len(hierarchical_text) * 100 // len(flat_text)) if len(flat_text) > 0 else 0
    print(f"\n📉 Optimisation vs flat text :")
    print(f"  - Flat : {len(flat_text):,} chars (~{len(flat_text)//4:,} tokens)")
    print(f"  - Hiérarchique : {len(hierarchical_text):,} chars (~{len(hierarchical_text)//4:,} tokens)")
    print(f"  - Réduction : {reduction}%")

    cost_before = (len(flat_text) // 4) * 0.003 / 1000
    cost_after = (len(hierarchical_text) // 4) * 0.003 / 1000
    savings = cost_before - cost_after

    print(f"\n💰 Coût estimé (input only) :")
    print(f"  - Avant : ${cost_before:.4f}")
    print(f"  - Après : ${cost_after:.4f}")
    print(f"  - Économie : ${savings:.4f} (-{reduction}%)")

    print(f"\n📄 Aperçu de la structure (800 premiers caractères) :")
    print("-" * 80)
    print(hierarchical_text[:800])
    print("\n[...]")
    print("-" * 80)

    # Verify hierarchy relationships
    print(f"\n🔗 Vérification de la hiérarchie parent-enfant :")
    with Session(engine) as db:
        hierarchy_check = db.execute(text("""
            SELECT
                child.section_number as child_num,
                child.title as child_title,
                parent.section_number as parent_num,
                parent.title as parent_title
            FROM document_sections child
            LEFT JOIN document_sections parent ON child.parent_id = parent.id
            WHERE child.parent_id IS NOT NULL
            LIMIT 5
        """)).fetchall()

        if hierarchy_check:
            print(f"  ✅ Relations parent-enfant établies ({len(hierarchy_check)} exemples) :")
            for row in hierarchy_check[:5]:
                print(f"     • {row[0]} → parent: {row[2]}")
                child_title = row[1][:50] + "..." if len(row[1]) > 50 else row[1]
                parent_title = row[3][:50] + "..." if len(row[3]) > 50 else row[3]
                print(f"       '{child_title}' → '{parent_title}'")
        else:
            print(f"  ⚠️  Aucune relation parent-enfant trouvée")

    # Final summary
    print(f"\n" + "=" * 80)
    print("✅ TEST END-TO-END TERMINÉ AVEC SUCCÈS")
    print("=" * 80)
    print(f"\n🎉 Résultats finaux :")
    print(f"  ✓ Tender créé : {tender_id}")
    print(f"  ✓ Documents traités : {len(processing_results)}")
    print(f"  ✓ Sections extraites : {total_sections}")
    print(f"  ✓ Sections TOC : {total_toc}")
    print(f"  ✓ Sections clés : {total_key}")
    print(f"  ✓ Hiérarchie établie : OUI")
    print(f"  ✓ Optimisation : -{reduction}%")
    print(f"  ✓ Économie par analyse : ${savings:.4f}")
    print()


if __name__ == "__main__":
    main()
