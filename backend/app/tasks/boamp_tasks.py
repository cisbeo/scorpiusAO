"""
Celery tasks for BOAMP (Bulletin Officiel des Annonces des Marchés Publics) integration.
"""
from datetime import datetime, date
from uuid import UUID
from sqlalchemy import select
import asyncio
import logging

from app.core.celery_app import celery_app
from app.services.boamp_service import boamp_service
from app.models.base import get_celery_session
from app.models.boamp_publication import BOAMPPublication
from app.models.tender import Tender
from app.models.tender_document import TenderDocument

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def fetch_boamp_publications_task(self, days_back: int = 1, limit: int = 100):
    """
    Periodic task: Fetch latest BOAMP publications and save to database.

    Runs hourly via Celery Beat.
    Fetches publications from last N days and filters for relevant IT infrastructure tenders.

    Args:
        days_back: Number of days to look back (default: 1 for hourly runs)
        limit: Maximum number of publications to fetch

    Returns:
        Dict with statistics about fetched/saved publications
    """
    try:
        logger.info(f"🔄 Starting BOAMP fetch: {days_back} days back, limit {limit}")

        # Fetch publications from BOAMP API (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        publications = loop.run_until_complete(
            boamp_service.fetch_latest_publications(limit=limit, days_back=days_back)
        )
        loop.close()

        if not publications:
            logger.info("No publications fetched from BOAMP")
            return {
                "status": "success",
                "fetched": 0,
                "filtered": 0,
                "saved": 0,
                "duplicates": 0
            }

        logger.info(f"Fetched {len(publications)} publications from BOAMP")

        # Filter for relevant publications (IT infrastructure/services)
        relevant_publications = boamp_service.filter_relevant_publications(
            publications,
            min_amount=10000.0,  # Minimum 10K€ contracts
            check_keywords=True,
            check_cpv=True
        )

        logger.info(f"Filtered {len(relevant_publications)} relevant publications")

        # Save to database
        db = get_celery_session()
        saved_count = 0
        duplicate_count = 0

        try:
            for pub_raw in relevant_publications:
                # Parse publication
                pub_data = boamp_service.parse_publication(pub_raw)

                # Check if already exists (by boamp_id)
                stmt = select(BOAMPPublication).where(
                    BOAMPPublication.boamp_id == pub_data["boamp_id"]
                )
                result = db.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    duplicate_count += 1
                    logger.debug(f"Duplicate: {pub_data['boamp_id']}")
                    continue

                # Create new publication
                publication = BOAMPPublication(
                    boamp_id=pub_data["boamp_id"],
                    title=pub_data["title"],
                    organization=pub_data["organization"],
                    publication_date=pub_data["publication_date"],
                    deadline=pub_data["deadline"],
                    type_annonce=pub_data["type_annonce"],
                    objet=pub_data["objet"],
                    montant=pub_data["montant"],
                    lieu_execution=pub_data["lieu_execution"],
                    cpv_codes=pub_data["cpv_codes"],
                    descripteurs=pub_data["descripteurs"],
                    raw_data=pub_data["raw_data"],
                    status="new",
                    created_at=datetime.utcnow()
                )

                db.add(publication)
                saved_count += 1

            db.commit()

            logger.info(f"✅ BOAMP fetch completed: {saved_count} new, {duplicate_count} duplicates")

            # TODO: Send notification if critical tenders found
            # if saved_count > 0:
            #     notify_new_boamp_publications(saved_count)

            return {
                "status": "success",
                "fetched": len(publications),
                "filtered": len(relevant_publications),
                "saved": saved_count,
                "duplicates": duplicate_count
            }

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"❌ Error fetching BOAMP publications: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


@celery_app.task(bind=True, max_retries=3)
def import_boamp_as_tender_task(self, boamp_publication_id: str):
    """
    Import a BOAMP publication as a Tender in the system.

    Creates a Tender record from BOAMP publication data.
    Updates BOAMP publication status to 'imported'.

    Args:
        boamp_publication_id: UUID of BOAMPPublication to import

    Returns:
        Dict with created tender_id and status
    """
    try:
        logger.info(f"📥 Importing BOAMP publication: {boamp_publication_id}")

        db = get_celery_session()
        try:
            # Load BOAMP publication
            stmt = select(BOAMPPublication).where(
                BOAMPPublication.id == boamp_publication_id
            )
            result = db.execute(stmt)
            boamp_pub = result.scalar_one_or_none()

            if not boamp_pub:
                raise ValueError(f"BOAMP publication {boamp_publication_id} not found")

            if boamp_pub.status == "imported":
                logger.warning(f"Publication {boamp_publication_id} already imported")
                return {
                    "status": "already_imported",
                    "tender_id": str(boamp_pub.matched_tender_id)
                }

            # Create Tender from BOAMP publication
            tender = Tender(
                title=boamp_pub.title,
                organization=boamp_pub.organization,
                reference_number=boamp_pub.boamp_id,
                deadline=datetime.combine(boamp_pub.deadline, datetime.min.time()) if boamp_pub.deadline else None,
                source="BOAMP",
                status="new",
                raw_content=boamp_pub.objet,
                parsed_content={
                    "boamp_id": boamp_pub.boamp_id,
                    "type_annonce": boamp_pub.type_annonce,
                    "montant": float(boamp_pub.montant) if boamp_pub.montant else None,
                    "lieu_execution": boamp_pub.lieu_execution,
                    "cpv_codes": boamp_pub.cpv_codes,
                    "descripteurs": boamp_pub.descripteurs,
                    "publication_date": boamp_pub.publication_date.isoformat() if boamp_pub.publication_date else None,
                }
            )

            db.add(tender)
            db.flush()  # Get tender.id

            # Update BOAMP publication
            boamp_pub.status = "imported"
            boamp_pub.matched_tender_id = tender.id
            boamp_pub.imported_at = datetime.utcnow()

            db.commit()

            logger.info(f"✅ Created Tender {tender.id} from BOAMP publication {boamp_publication_id}")

            # TODO: Download documents if URLs available in raw_data
            # download_boamp_documents_task.delay(str(tender.id), boamp_pub.raw_data)

            # TODO: Trigger tender processing pipeline
            # from app.tasks.tender_tasks import process_tender_documents
            # process_tender_documents.delay(str(tender.id))

            return {
                "status": "success",
                "tender_id": str(tender.id),
                "boamp_publication_id": boamp_publication_id
            }

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"❌ Error importing BOAMP publication {boamp_publication_id}: {exc}")

        # Update status to error
        try:
            db = get_celery_session()
            try:
                stmt = select(BOAMPPublication).where(
                    BOAMPPublication.id == boamp_publication_id
                )
                result = db.execute(stmt)
                boamp_pub = result.scalar_one_or_none()

                if boamp_pub:
                    boamp_pub.status = "error"
                    db.commit()
            finally:
                db.close()
        except:
            pass

        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


@celery_app.task
def cleanup_old_boamp_publications_task(days_to_keep: int = 90):
    """
    Cleanup old BOAMP publications that were not imported.

    Deletes publications older than N days with status 'new' or 'ignored'.

    Args:
        days_to_keep: Number of days to retain publications

    Returns:
        Dict with number of deleted publications
    """
    try:
        from datetime import timedelta

        logger.info(f"🧹 Cleaning up BOAMP publications older than {days_to_keep} days")

        db = get_celery_session()
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)

            # Delete old unimported publications
            from sqlalchemy import delete
            stmt = delete(BOAMPPublication).where(
                BOAMPPublication.publication_date < cutoff_date,
                BOAMPPublication.status.in_(["new", "ignored"])
            )

            result = db.execute(stmt)
            deleted_count = result.rowcount

            db.commit()

            logger.info(f"✅ Deleted {deleted_count} old BOAMP publications")

            return {
                "status": "success",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"❌ Error cleaning up BOAMP publications: {exc}")
        return {
            "status": "error",
            "error": str(exc)
        }
