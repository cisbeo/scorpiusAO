"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Import all models to ensure SQLAlchemy metadata is populated
# This must happen before any Celery tasks execute
from app.models.tender import Tender, TenderCriterion
from app.models.tender_document import TenderDocument
from app.models.tender_analysis import TenderAnalysis
from app.models.proposal import Proposal
from app.models.document import DocumentEmbedding
from app.models.similar_tender import SimilarTender
from app.models.criterion_suggestion import CriterionSuggestion
from app.models.boamp_publication import BOAMPPublication

# Create Celery app
celery_app = Celery(
    "scorpius",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.tender_tasks",
        "app.tasks.boamp_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routes - Using default queue for now
# celery_app.conf.task_routes = {
#     "app.tasks.tender_tasks.*": {"queue": "tenders"},
# }

# Celery Beat schedule - Periodic tasks
celery_app.conf.beat_schedule = {
    # Fetch BOAMP publications every hour
    "fetch-boamp-hourly": {
        "task": "app.tasks.boamp_tasks.fetch_boamp_publications_task",
        "schedule": crontab(minute=0),  # Every hour at :00
        "kwargs": {"days_back": 1, "limit": 100},
    },
    # Cleanup old BOAMP publications weekly (Sunday at 3 AM)
    "cleanup-boamp-weekly": {
        "task": "app.tasks.boamp_tasks.cleanup_old_boamp_publications_task",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        "kwargs": {"days_to_keep": 90},
    },
}
