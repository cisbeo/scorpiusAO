"""Test script for hierarchical structure optimization."""
import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.llm_service import LLMService

async def test_hierarchy():
    """Test hierarchical structure building."""

    # Connect to database
    engine = create_engine(settings.database_url_sync)

    # Fetch sections from CCTP.pdf (document with key sections)
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
                page
            FROM document_sections
            WHERE document_id = 'a0154e42-a610-4888-80b6-7b14f7510058'
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

    print(f"📊 Loaded {len(sections)} sections from CCTP.pdf")
    print(f"   - TOC sections: {sum(1 for s in sections if s['is_toc'])}")
    print(f"   - Key sections: {sum(1 for s in sections if s['is_key_section'])}")
    print(f"   - Regular sections: {sum(1 for s in sections if not s['is_toc'] and not s['is_key_section'])}")

    # Test hierarchical structure
    llm_service = LLMService()
    hierarchical_text = llm_service._build_hierarchical_structure(sections)

    print(f"\n📝 Hierarchical structure generated:")
    print(f"   - Characters: {len(hierarchical_text)}")
    print(f"   - Estimated tokens: ~{len(hierarchical_text) // 4}")
    print(f"   - Lines: {len(hierarchical_text.splitlines())}")

    # Compare with flat text (old method)
    flat_text = "\n\n".join([
        f"Section {s['section_number']}: {s['title']}\n{s['content']}"
        for s in sections
        if s['content'] and not s['is_toc']
    ])

    print(f"\n📊 Comparison (Flat vs Hierarchical):")
    print(f"   - Flat text: {len(flat_text)} chars (~{len(flat_text) // 4} tokens)")
    print(f"   - Hierarchical: {len(hierarchical_text)} chars (~{len(hierarchical_text) // 4} tokens)")
    print(f"   - Reduction: {100 - (len(hierarchical_text) * 100 // len(flat_text))}%")

    # Show sample of hierarchical text
    print(f"\n📄 Sample of hierarchical structure (first 1500 chars):")
    print("=" * 80)
    print(hierarchical_text[:1500])
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_hierarchy())
