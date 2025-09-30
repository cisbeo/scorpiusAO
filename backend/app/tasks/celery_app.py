"""
Celery application configuration.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "scorpius",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.tender_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
