#!/usr/bin/env python3
"""
Batch ingest all past proposals for RAG Knowledge Base.

Usage:
    python scripts/ingest_past_proposals.py --status won
    python scripts/ingest_past_proposals.py --status all
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.rag_service import rag_service


def main():
    parser = argparse.ArgumentParser(description="Batch ingest past proposals for RAG Knowledge Base")
    parser.add_argument(
        "--status",
        choices=["won", "lost", "all"],
        default="won",
        help="Filter proposals by status (default: won)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing (default: 10)"
    )

    args = parser.parse_args()

    # Create database session
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("=" * 80)
        print("🚀 BATCH INGESTION - PAST PROPOSALS FOR RAG KNOWLEDGE BASE")
        print("=" * 80)
        print(f"Status filter: {args.status}")
        print(f"Batch size: {args.batch_size}")
        print()

        # Run batch ingestion
        result = rag_service.ingest_all_past_proposals_sync(
            db=db,
            batch_size=args.batch_size,
            status_filter=args.status
        )

        print("\n" + "=" * 80)
        print("✅ BATCH INGESTION COMPLETE")
        print("=" * 80)
        print(f"Total proposals: {result['total_proposals']}")
        print(f"Total embeddings: {result['total_embeddings']}")
        print(f"Errors: {len(result['errors'])}")

        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
