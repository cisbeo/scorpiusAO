#!/usr/bin/env python3
"""
Analyse détaillée de la qualité de l'extraction de contenu sur les PDFs réels.
"""
import json
from pathlib import Path
from collections import defaultdict


def analyze_pdf_extraction(pdf_name: str, data: dict):
    """Analyze extraction quality for a single PDF."""

    print(f"\n{'='*80}")
    print(f"📄 ANALYSE DÉTAILLÉE: {pdf_name}")
    print(f"{'='*80}\n")

    sections = data['sections']
    stats = data['stats']

    # 1. Content statistics
    print("📊 STATISTIQUES DE CONTENU")
    print("-" * 80)

    content_lengths = [s.get('content_length', 0) for s in sections]
    sections_with_content = [s for s in sections if s.get('content_length', 0) > 0]
    sections_substantial = [s for s in sections if s.get('content_length', 0) > 100]
    sections_truncated = [s for s in sections if s.get('content_truncated', False)]

    print(f"Total sections: {len(sections)}")
    print(f"Sections with content (>0): {len(sections_with_content)} ({len(sections_with_content)/len(sections)*100:.1f}%)")
    print(f"Sections substantial (>100): {len(sections_substantial)} ({len(sections_substantial)/len(sections)*100:.1f}%)")
    print(f"Sections truncated (>2000): {len(sections_truncated)}")

    if content_lengths:
        avg_length = sum(content_lengths) / len(content_lengths)
        max_length = max(content_lengths)
        print(f"\nContent length (chars):")
        print(f"  Average: {avg_length:.0f}")
        print(f"  Maximum: {max_length}")
        print(f"  Total: {sum(content_lengths):,}")

    # 2. Content by page
    print(f"\n📑 RÉPARTITION PAR PAGE")
    print("-" * 80)

    by_page = defaultdict(list)
    for section in sections:
        by_page[section['page']].append(section)

    print(f"{'Page':<6} {'Sections':<10} {'With Content':<14} {'Avg Length':<12} {'Status'}")
    print("-" * 80)

    for page in sorted(by_page.keys())[:10]:  # First 10 pages
        page_sections = by_page[page]
        with_content = [s for s in page_sections if s.get('content_length', 0) > 50]
        avg_len = sum(s.get('content_length', 0) for s in page_sections) / len(page_sections)

        status = "✅ OK" if len(with_content) > 0 else "⚠️  TOC?"
        print(f"{page:<6} {len(page_sections):<10} {len(with_content):<14} {avg_len:<12.0f} {status}")

    if len(by_page) > 10:
        print(f"... and {len(by_page) - 10} more pages")

    # 3. Best examples
    print(f"\n🏆 MEILLEURS EXEMPLES D'EXTRACTION")
    print("-" * 80)

    # Sort by content length
    best_sections = sorted(
        [s for s in sections if s.get('content_length', 0) > 200],
        key=lambda s: s.get('content_length', 0),
        reverse=True
    )[:3]

    for i, section in enumerate(best_sections, 1):
        print(f"\n{i}. Section {section['number']}: {section['title'][:70]}")
        print(f"   Page {section['page']} | {section['content_length']} chars")
        print(f"   Content:")
        content = section['content'].replace('\n', ' ')[:300]
        print(f"   \"{content}...\"")

    # 4. Sections by type
    print(f"\n🏷️  TYPES DE SECTIONS")
    print("-" * 80)

    by_type = defaultdict(list)
    for section in sections:
        by_type[section['type']].append(section)

    for section_type, sections_of_type in sorted(by_type.items()):
        with_content = [s for s in sections_of_type if s.get('content_length', 0) > 50]
        avg_content = sum(s.get('content_length', 0) for s in sections_of_type) / len(sections_of_type)
        print(f"{section_type:<15}: {len(sections_of_type):3} sections, "
              f"{len(with_content):3} with content, avg {avg_content:.0f} chars")

    # 5. Key sections with content
    print(f"\n🎯 SECTIONS CLÉS AVEC CONTENU")
    print("-" * 80)

    key_sections = data.get('key_sections', {})

    for key_type, key_sections_list in key_sections.items():
        if not key_sections_list:
            continue

        print(f"\n{key_type.upper()} ({len(key_sections_list)}):")
        for ks in key_sections_list[:3]:
            # Find full section
            full_section = next(
                (s for s in sections if s['number'] == ks['section_id']),
                None
            )
            if full_section:
                content_len = full_section.get('content_length', 0)
                status = "✅" if content_len > 100 else "⚠️"
                print(f"  {status} Section {ks['section_id']}: {ks['title'][:50]}")
                print(f"     Page {ks['page']}, {content_len} chars")
                if content_len > 100:
                    preview = full_section['content'][:150].replace('\n', ' ')
                    print(f"     \"{preview}...\"")

    return {
        'total_sections': len(sections),
        'with_content': len(sections_with_content),
        'substantial': len(sections_substantial),
        'truncated': len(sections_truncated),
        'avg_length': avg_length if content_lengths else 0,
        'total_chars': sum(content_lengths)
    }


def main():
    """Analyze all PDFs."""

    print("=" * 80)
    print("🔍 ANALYSE QUALITÉ DE L'EXTRACTION DE CONTENU")
    print("=" * 80)

    # Load results
    results_file = Path(__file__).parent / "real_pdfs_extraction_results.json"
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Analyze each PDF
    summary = {}
    for pdf_name in ['RC.pdf', 'CCAP.pdf', 'CCTP.pdf']:
        if pdf_name in data:
            summary[pdf_name] = analyze_pdf_extraction(pdf_name, data[pdf_name])

    # Overall summary
    print(f"\n{'='*80}")
    print("📈 RÉSUMÉ GLOBAL")
    print(f"{'='*80}\n")

    print(f"{'Document':<15} {'Sections':<10} {'With Content':<15} {'Substantial':<13} {'Avg Length':<12} {'Total Chars'}")
    print("-" * 80)

    for pdf_name, stats in summary.items():
        pct_content = stats['with_content'] / stats['total_sections'] * 100
        pct_substantial = stats['substantial'] / stats['total_sections'] * 100

        print(f"{pdf_name:<15} "
              f"{stats['total_sections']:<10} "
              f"{stats['with_content']:<6} ({pct_content:.1f}%)  "
              f"{stats['substantial']:<6} ({pct_substantial:.1f}%)  "
              f"{stats['avg_length']:<12.0f} "
              f"{stats['total_chars']:,}")

    # Total
    total_sections = sum(s['total_sections'] for s in summary.values())
    total_with_content = sum(s['with_content'] for s in summary.values())
    total_substantial = sum(s['substantial'] for s in summary.values())
    total_chars = sum(s['total_chars'] for s in summary.values())

    print("-" * 80)
    print(f"{'TOTAL':<15} "
          f"{total_sections:<10} "
          f"{total_with_content:<6} ({total_with_content/total_sections*100:.1f}%)  "
          f"{total_substantial:<6} ({total_substantial/total_sections*100:.1f}%)  "
          f"{total_chars/total_sections:<12.0f} "
          f"{total_chars:,}")

    print(f"\n{'='*80}")
    print("✅ Analyse terminée")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
