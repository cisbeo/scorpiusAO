"""
Run real LLM analysis with Claude API using hierarchical structure.
"""
import sys
import asyncio
import json
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.llm_service import LLMService


async def main():
    print("=" * 80)
    print("🤖 ANALYSE LLM AVEC CLAUDE API - STRUCTURE HIÉRARCHIQUE")
    print("=" * 80)
    print()

    # Verify API key
    if not settings.anthropic_api_key or settings.anthropic_api_key == "your_anthropic_key_here":
        print("❌ Clé API Anthropic non configurée")
        return

    print(f"✅ Clé API Anthropic configurée : {settings.anthropic_api_key[:20]}...")
    print()

    # Connect to database
    engine = create_engine(settings.database_url_sync)

    # Get all sections and metadata
    print("📊 Chargement des données...")
    with engine.connect() as conn:
        # Get sections
        result = conn.execute(text("""
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

        sections = []
        for row in result:
            sections.append({
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

        # Get tender metadata
        tender_result = conn.execute(text("""
            SELECT
                t.title,
                t.organization,
                t.reference_number,
                t.deadline,
                COUNT(td.id) as doc_count,
                SUM(td.page_count) as total_pages
            FROM tenders t
            LEFT JOIN tender_documents td ON t.id = td.tender_id
            GROUP BY t.id, t.title, t.organization, t.reference_number, t.deadline
            LIMIT 1
        """)).first()

        metadata = {
            "tender_title": tender_result[0],
            "organization": tender_result[1],
            "reference_number": tender_result[2],
            "deadline": str(tender_result[3]) if tender_result[3] else None,
            "document_count": tender_result[4],
            "total_pages": tender_result[5]
        }

    print(f"✅ {len(sections)} sections chargées")
    print(f"✅ Tender : {metadata['tender_title']}")
    print(f"✅ Organisation : {metadata['organization']}")
    print(f"✅ Référence : {metadata['reference_number']}")
    print()

    # Analyze with LLM
    print("🤖 Appel de Claude API pour analyse structurée...")
    print("-" * 80)

    llm_service = LLMService()

    try:
        # Use async analysis
        analysis = await llm_service.analyze_tender_structured(sections, metadata)

        print("✅ Analyse terminée avec succès !")
        print()
        print("=" * 80)
        print("📋 RÉSULTATS DE L'ANALYSE")
        print("=" * 80)
        print()

        # Display formatted results
        print("📌 RÉSUMÉ :")
        print("-" * 80)
        print(analysis.get("summary", "N/A"))
        print()

        print("🎯 EXIGENCES PRINCIPALES :")
        print("-" * 80)
        for i, req in enumerate(analysis.get("key_requirements", []), 1):
            print(f"  {i}. {req}")
        print()

        print("📅 DÉLAIS :")
        print("-" * 80)
        for deadline in analysis.get("deadlines", []):
            print(f"  • {deadline.get('type', 'N/A')} : {deadline.get('date', 'N/A')}")
            if deadline.get('description'):
                print(f"    → {deadline['description']}")
        print()

        print("⚠️  RISQUES IDENTIFIÉS :")
        print("-" * 80)
        for i, risk in enumerate(analysis.get("risks", []), 1):
            print(f"  {i}. {risk}")
        print()

        print("📄 DOCUMENTS OBLIGATOIRES :")
        print("-" * 80)
        for doc in analysis.get("mandatory_documents", []):
            print(f"  • {doc}")
        print()

        print("📊 ÉVALUATION :")
        print("-" * 80)
        print(f"  • Complexité : {analysis.get('complexity_level', 'N/A').upper()}")
        print(f"  • Méthode : {analysis.get('evaluation_method', 'N/A')}")
        print()

        print("💡 RECOMMANDATIONS :")
        print("-" * 80)
        for i, rec in enumerate(analysis.get("recommendations", []), 1):
            print(f"  {i}. {rec}")
        print()

        if "key_sections_summary" in analysis:
            print("🔑 RÉSUMÉ DES SECTIONS CLÉS :")
            print("-" * 80)
            key_sum = analysis["key_sections_summary"]
            if key_sum.get("exclusions"):
                print(f"  Exclusions : {key_sum['exclusions']}")
            if key_sum.get("obligations"):
                print(f"  Obligations : {key_sum['obligations']}")
            if key_sum.get("criteria"):
                print(f"  Critères : {key_sum['criteria']}")
            if key_sum.get("penalties"):
                print(f"  Pénalités : {key_sum['penalties']}")
            print()

        # Save full JSON
        print("💾 Sauvegarde du résultat complet...")
        with open('/app/analysis_result.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print("✅ Résultat sauvegardé dans /app/analysis_result.json")
        print()

        print("=" * 80)
        print("✅ ANALYSE LLM TERMINÉE AVEC SUCCÈS")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
