from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "football_simulator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_track_started=True,
    # Windows platformunda havuz problemleri yasanmamasi icin
    worker_pool_restarts=True,
)
