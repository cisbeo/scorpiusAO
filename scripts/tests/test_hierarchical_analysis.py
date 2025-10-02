"""
Test hierarchical structure generation and calculate real LLM savings.
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.llm_service import LLMService


def main():
    print("=" * 80)
    print("🌳 ANALYSE DE LA STRUCTURE HIÉRARCHIQUE - ÉCONOMIES LLM")
    print("=" * 80)
    print()

    # Connect to database
    engine = create_engine(settings.database_url_sync)

    # Get all sections
    print("📊 Chargement des sections depuis la base de données...")
    with engine.connect() as conn:
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
                page,
                td.filename
            FROM document_sections ds
            JOIN tender_documents td ON ds.document_id = td.id
            ORDER BY td.filename, ds.page, ds.line
        """))

        sections = []
        sections_by_doc = {}

        for row in result:
            section = {
                "type": row[0],
                "section_number": row[1],
                "parent_number": row[2],
                "title": row[3],
                "content": row[4] or "",
                "content_length": row[5],
                "is_toc": row[6],
                "is_key_section": row[7],
                "level": row[8],
                "page": row[9],
                "filename": row[10]
            }
            sections.append(section)

            # Group by document
            if row[10] not in sections_by_doc:
                sections_by_doc[row[10]] = []
            sections_by_doc[row[10]].append(section)

    print(f"✅ {len(sections)} sections chargées depuis {len(sections_by_doc)} documents")
    print()

    # Statistics by document
    print("📋 Statistiques par document :")
    print("-" * 80)
    for filename, doc_sections in sections_by_doc.items():
        toc_count = sum(1 for s in doc_sections if s['is_toc'])
        key_count = sum(1 for s in doc_sections if s['is_key_section'])
        with_content = sum(1 for s in doc_sections if s['content_length'] > 0)

        print(f"  {filename}:")
        print(f"    - Total: {len(doc_sections)} sections")
        print(f"    - TOC: {toc_count} ({toc_count*100//len(doc_sections)}%)")
        print(f"    - Clés: {key_count} ({key_count*100//len(doc_sections)}%)")
        print(f"    - Avec contenu: {with_content} ({with_content*100//len(doc_sections)}%)")

    # Build hierarchical structure
    print(f"\n🌳 Construction de la structure hiérarchique...")
    print("-" * 80)

    llm_service = LLMService()
    hierarchical_text = llm_service._build_hierarchical_structure(sections)

    # Calculate flat text for comparison
    flat_text = "\n\n".join([
        f"Section {s['section_number']}: {s['title']}\n{s['content']}"
        for s in sections
        if s['content'] and not s['is_toc']
    ])

    # Display results
    print(f"Structure hiérarchique générée :")
    print(f"  - Caractères : {len(hierarchical_text):,}")
    print(f"  - Tokens estimés : ~{len(hierarchical_text) // 4:,}")
    print(f"  - Lignes : {len(hierarchical_text.splitlines()):,}")

    print(f"\n📊 Comparaison FLAT vs HIÉRARCHIQUE :")
    print("-" * 80)
    print(f"{'Méthode':<20} {'Caractères':>15} {'Tokens':>15} {'Coût (input)':>15}")
    print("-" * 80)

    flat_tokens = len(flat_text) // 4
    hier_tokens = len(hierarchical_text) // 4
    flat_cost = flat_tokens * 0.003 / 1000
    hier_cost = hier_tokens * 0.003 / 1000

    print(f"{'Flat (avant)':<20} {len(flat_text):>15,} {flat_tokens:>15,} ${flat_cost:>14.4f}")
    print(f"{'Hiérarchique':<20} {len(hierarchical_text):>15,} {hier_tokens:>15,} ${hier_cost:>14.4f}")
    print("-" * 80)

    reduction_chars = len(flat_text) - len(hierarchical_text)
    reduction_pct = (reduction_chars * 100) // len(flat_text) if len(flat_text) > 0 else 0
    savings = flat_cost - hier_cost

    print(f"{'RÉDUCTION':<20} {reduction_chars:>15,} {flat_tokens - hier_tokens:>15,} ${savings:>14.4f}")
    print(f"{'POURCENTAGE':<20} {reduction_pct:>14}% {reduction_pct:>14}% {int(savings*100/flat_cost) if flat_cost > 0 else 0:>14}%")
    print("-" * 80)

    # Monthly savings
    print(f"\n💰 ÉCONOMIES MENSUELLES (estimations) :")
    print("-" * 80)
    scenarios = [
        (10, "10 tenders/mois"),
        (50, "50 tenders/mois"),
        (100, "100 tenders/mois"),
        (200, "200 tenders/mois")
    ]

    for count, label in scenarios:
        monthly_savings = savings * count
        yearly_savings = monthly_savings * 12
        print(f"  {label:<20} : ${monthly_savings:>6.2f}/mois  (${yearly_savings:>7.2f}/an)")

    # Show sample of hierarchical structure
    print(f"\n📄 APERÇU DE LA STRUCTURE HIÉRARCHIQUE (1000 premiers caractères) :")
    print("=" * 80)
    print(hierarchical_text[:1000])
    print("\n[... suite tronquée ...]")
    print("=" * 80)

    # Breakdown by section type
    print(f"\n🔍 DÉTAIL PAR TYPE DE SECTION :")
    print("-" * 80)

    toc_sections = [s for s in sections if s['is_toc']]
    key_sections = [s for s in sections if s['is_key_section'] and not s['is_toc']]
    regular_long = [s for s in sections if not s['is_toc'] and not s['is_key_section'] and s['content_length'] > 200]
    regular_short = [s for s in sections if not s['is_toc'] and not s['is_key_section'] and 0 < s['content_length'] <= 200]
    empty_sections = [s for s in sections if not s['is_toc'] and s['content_length'] == 0]

    total_toc_content = sum(s['content_length'] for s in toc_sections)
    total_key_content = sum(s['content_length'] for s in key_sections)
    total_regular_long = sum(s['content_length'] for s in regular_long)
    total_regular_short = sum(s['content_length'] for s in regular_short)

    print(f"{'Type':<25} {'Count':>8} {'Chars (avant)':>15} {'Chars (après)':>15} {'Économie':>12}")
    print("-" * 80)
    print(f"{'TOC (exclues)':<25} {len(toc_sections):>8} {total_toc_content:>15,} {0:>15,} {total_toc_content:>11,}")
    print(f"{'Clés (complètes)':<25} {len(key_sections):>8} {total_key_content:>15,} {total_key_content:>15,} {0:>11,}")

    # Regular long: résumées à 200 chars
    regular_long_after = len(regular_long) * 200
    regular_long_savings = total_regular_long - regular_long_after
    print(f"{'Longues (>200, résumé)':<25} {len(regular_long):>8} {total_regular_long:>15,} {regular_long_after:>15,} {regular_long_savings:>11,}")

    # Regular short: gardées complètes
    print(f"{'Courtes (≤200, garde)':<25} {len(regular_short):>8} {total_regular_short:>15,} {total_regular_short:>15,} {0:>11,}")

    # Empty: headers only
    print(f"{'Vides (titre seul)':<25} {len(empty_sections):>8} {0:>15,} {0:>15,} {0:>11,}")
    print("-" * 80)

    total_before = total_toc_content + total_key_content + total_regular_long + total_regular_short
    total_after = total_key_content + regular_long_after + total_regular_short
    total_savings = total_before - total_after

    print(f"{'TOTAL':<25} {len(sections):>8} {total_before:>15,} {total_after:>15,} {total_savings:>11,}")
    print("-" * 80)

    # Verify hierarchy
    print(f"\n🔗 VÉRIFICATION DE LA HIÉRARCHIE :")
    print("-" * 80)

    with engine.connect() as conn:
        hierarchy_examples = conn.execute(text("""
            SELECT
                child.section_number,
                LEFT(child.title, 40) as child_title,
                parent.section_number,
                LEFT(parent.title, 40) as parent_title,
                td.filename
            FROM document_sections child
            JOIN document_sections parent ON child.parent_id = parent.id
            JOIN tender_documents td ON child.document_id = td.id
            LIMIT 10
        """)).fetchall()

        if hierarchy_examples:
            print(f"✅ {len(hierarchy_examples)} exemples de relations parent-enfant :")
            for row in hierarchy_examples:
                print(f"  [{row[4]}] {row[0]} → parent: {row[2]}")
                print(f"    '{row[1]}' → '{row[3]}'")
        else:
            print("⚠️  Aucune relation hiérarchique trouvée")

    # Final summary
    print(f"\n" + "=" * 80)
    print("✅ ANALYSE TERMINÉE")
    print("=" * 80)
    print(f"\n🎯 RÉSUMÉ FINAL :")
    print(f"  ✓ Documents analysés : {len(sections_by_doc)}")
    print(f"  ✓ Sections totales : {len(sections)}")
    print(f"  ✓ Réduction tokens : -{reduction_pct}%")
    print(f"  ✓ Économie par analyse : ${savings:.4f}")
    print(f"  ✓ Économie 100 tenders/mois : ${savings * 100:.2f}/mois (${savings * 1200:.2f}/an)")
    print()


if __name__ == "__main__":
    main()
