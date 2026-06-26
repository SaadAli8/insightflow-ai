"""Celery application + queue routing.

Queues are SEGMENTED by workload class because they have different bottlenecks:

  website  -> network I/O (gevent, high concurrency)
  file     -> CPU (OCR/parsing) (prefork, concurrency = cores)
  ai       -> OpenAI calls, RATE-LIMITED (gevent + Redis token bucket)

Each queue gets its own worker container in docker-compose.yml so they scale
independently. A burst of CPU-heavy file jobs can't starve quick website jobs."""

from celery import Celery

from app.core.config import settings

celery = Celery(
    "insightflow_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "workers.tasks.website",
        "workers.tasks.files",
        "workers.tasks.ai",
    ],
)

celery.conf.update(
    # Reliability: if a worker dies mid-task, re-deliver it to another worker.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Don't let one worker hoard tasks — critical for long-running jobs.
    worker_prefetch_multiplier=1,
    # Route each task to its dedicated queue.
    task_routes={
        "workers.tasks.website.*": {"queue": "website"},
        "workers.tasks.files.*": {"queue": "file"},
        "workers.tasks.ai.*": {"queue": "ai"},
    },
    task_default_queue="default",
    # Redelivery window for unacked tasks (Redis broker).
    broker_transport_options={"visibility_timeout": 3600},
    task_track_started=True,
    result_expires=3600,
)
