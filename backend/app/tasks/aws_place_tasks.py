"""
Celery tasks for AWS PLACE integration.
"""
from celery import Task
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
import logging

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.models.aws_place_publication import AWSPlacePublication
from app.models.tender import Tender
from app.services.aws_place_service import aws_place_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def fetch_aws_place_consultations_task(
    self: Task,
    days_back: int = 30,
    limit: int = 100,
    min_amount: int = 50000  # 50K€ minimum for relevant IT contracts
) -> dict:
    """
    Fetch latest consultations from AWS PLACE (via DECP API).

    Args:
        days_back: Number of days to look back
        limit: Maximum number of consultations to fetch
        min_amount: Minimum contract amount in euros

    Returns:
        Dict with statistics about fetched consultations
    """
    logger.info(f"Starting AWS PLACE fetch task (days_back={days_back}, limit={limit}, min_amount={min_amount})")

    try:
        # Fetch from DECP API (async)
        import asyncio
        consultations = asyncio.run(
            aws_place_service.fetch_latest_consultations(
                limit=limit,
                days_back=days_back,
                min_amount=min_amount
            )
        )

        logger.info(f"Fetched {len(consultations)} consultations from DECP API")

        # Filter for IT infrastructure relevance
        relevant_consultations = aws_place_service.filter_relevant_consultations(
            consultations,
            check_keywords=True,
            check_cpv=True
        )

        logger.info(f"Filtered {len(relevant_consultations)} relevant IT consultations")

        # Save to database
        db: Session = next(get_db())
        saved_count = 0
        updated_count = 0
        skipped_count = 0

        try:
            for consultation in relevant_consultations:
                place_id = consultation.get("place_id")

                if not place_id:
                    logger.warning(f"Consultation missing place_id: {consultation.get('title', 'N/A')}")
                    skipped_count += 1
                    continue

                # Check if already exists
                existing = db.execute(
                    select(AWSPlacePublication).where(AWSPlacePublication.place_id == place_id)
                ).scalar_one_or_none()

                if existing:
                    # Update if status is still 'new'
                    if existing.status == 'new':
                        for key, value in consultation.items():
                            if key not in ['place_id', 'raw_data']:  # Don't update ID and raw_data
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        updated_count += 1
                        logger.debug(f"Updated existing consultation: {place_id}")
                    else:
                        skipped_count += 1
                        logger.debug(f"Skipped consultation (status={existing.status}): {place_id}")
                else:
                    # Create new publication
                    publication = AWSPlacePublication(
                        place_id=place_id,
                        title=consultation.get("title", ""),
                        reference=consultation.get("reference"),
                        organization=consultation.get("organization"),
                        publication_date=self._parse_date(consultation.get("publication_date")),
                        deadline=self._parse_datetime(consultation.get("deadline")),
                        description=consultation.get("description"),
                        cpv_codes=consultation.get("cpv_codes", []),
                        consultation_type=consultation.get("consultation_type"),
                        procedure_type=consultation.get("procedure_type"),
                        estimated_amount=consultation.get("estimated_amount"),
                        currency=consultation.get("currency", "EUR"),
                        execution_location=consultation.get("execution_location"),
                        nuts_codes=consultation.get("nuts_codes", []),
                        duration_months=consultation.get("duration_months"),
                        renewal_possible=consultation.get("renewal_possible", False),
                        status="new",
                        raw_data=consultation.get("raw_data", {}),
                        url=consultation.get("url"),
                        documents_url=consultation.get("documents_url"),
                    )
                    db.add(publication)
                    saved_count += 1
                    logger.debug(f"Created new consultation: {place_id}")

            db.commit()
            logger.info(f"AWS PLACE task completed: {saved_count} new, {updated_count} updated, {skipped_count} skipped")

            return {
                "status": "success",
                "total_fetched": len(consultations),
                "relevant": len(relevant_consultations),
                "saved": saved_count,
                "updated": updated_count,
                "skipped": skipped_count,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Database error in AWS PLACE task: {e}")
            raise

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in AWS PLACE fetch task: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string to date object"""
        if not date_str:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except:
            try:
                # Try common French format
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                logger.warning(f"Could not parse date: {date_str}")
                return None

    def _parse_datetime(self, datetime_str: str) -> datetime | None:
        """Parse datetime string to datetime object"""
        if not datetime_str:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except:
            try:
                # Try common French format
                return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except:
                logger.warning(f"Could not parse datetime: {datetime_str}")
                return None


@celery_app.task(bind=True)
def import_aws_place_as_tender_task(self: Task, publication_id: str) -> dict:
    """
    Import an AWS PLACE consultation as a Tender.

    Args:
        publication_id: UUID of the AWSPlacePublication

    Returns:
        Dict with import status
    """
    logger.info(f"Importing AWS PLACE consultation {publication_id} as Tender")

    db: Session = next(get_db())

    try:
        # Load publication
        publication = db.execute(
            select(AWSPlacePublication).where(AWSPlacePublication.id == publication_id)
        ).scalar_one_or_none()

        if not publication:
            raise ValueError(f"Publication not found: {publication_id}")

        if publication.status == "imported":
            logger.warning(f"Publication already imported: {publication_id}")
            return {"status": "skipped", "reason": "already_imported"}

        # Create Tender from publication
        tender = Tender(
            title=publication.title,
            organization=publication.organization,
            reference_number=publication.reference,
            deadline=publication.deadline,
            raw_content=publication.description or "",
            parsed_content={
                "description": publication.description,
                "cpv_codes": publication.cpv_codes,
                "estimated_amount": float(publication.estimated_amount) if publication.estimated_amount else None,
                "execution_location": publication.execution_location,
                "duration_months": publication.duration_months,
                "consultation_type": publication.consultation_type,
                "procedure_type": publication.procedure_type,
            },
            status="new",
            source="AWS_PLACE",
        )

        db.add(tender)
        db.flush()

        # Update publication status
        publication.status = "imported"
        publication.matched_tender_id = tender.id
        publication.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Successfully imported AWS PLACE consultation as Tender {tender.id}")

        return {
            "status": "success",
            "tender_id": str(tender.id),
            "publication_id": publication_id,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error importing AWS PLACE consultation: {e}")
        raise

    finally:
        db.close()


@celery_app.task
def cleanup_old_aws_place_publications_task(days_to_keep: int = 180) -> dict:
    """
    Clean up old AWS PLACE publications.

    Args:
        days_to_keep: Keep publications from last N days (default 180)

    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"Cleaning up AWS PLACE publications older than {days_to_keep} days")

    db: Session = next(get_db())
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    try:
        # Delete old publications that were not imported
        result = db.execute(
            select(AWSPlacePublication).where(
                and_(
                    AWSPlacePublication.created_at < cutoff_date,
                    AWSPlacePublication.status.in_(["new", "ignored", "error"])
                )
            )
        )
        old_publications = result.scalars().all()

        deleted_count = len(old_publications)

        for pub in old_publications:
            db.delete(pub)

        db.commit()

        logger.info(f"Deleted {deleted_count} old AWS PLACE publications")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up AWS PLACE publications: {e}")
        raise

    finally:
        db.close()
