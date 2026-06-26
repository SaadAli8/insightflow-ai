"""Website task: fetch the page politely, store the text, then hand off to the
AI queue. Politeness is enforced with a per-domain token bucket — if we'd exceed
the domain's rate, the task re-queues itself (backpressure), it does not hammer
the site."""

import math
from urllib.parse import urlparse

from celery import Task
from celery.exceptions import MaxRetriesExceededError, Retry

from app.core.logging import get_logger
from app.db.models import Job, JobStatus, Website
from app.db.session import SessionLocal
from app.services import storage
from app.services.events import Event, publish
from workers.celery_app import celery
from workers.ratelimit import domain_gate
from workers.scraper import fetch_clean_text

log = get_logger("task.website")


@celery.task(bind=True, name="workers.tasks.website.analyze_website",
             max_retries=5, acks_late=True)
def analyze_website(self: Task, job_id: str):
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            log.warning("job %s gone", job_id)
            return
        if job.status == JobStatus.COMPLETED:   # idempotent: already done
            return

        website = db.get(Website, job.website_id)
        domain = urlparse(website.url).netloc

        # --- politeness backpressure: re-queue instead of overloading the site ---
        allowed, wait = domain_gate(domain)
        if not allowed:
            raise self.retry(countdown=math.ceil(wait) + 1)

        job.status = JobStatus.PROCESSING
        job.attempts += 1
        db.commit()
        publish(Event.ANALYSIS_STARTED, {"job_id": job.id, "type": "website"}, key=job.id)

        # Best-effort page fetch (web search fills in the rest during AI step).
        text = fetch_clean_text(website.url)
        key = f"extracted/{job.id}.txt"
        storage.upload_bytes(key, text.encode("utf-8"), "text/plain")
        job.extracted_s3_key = key
        db.commit()

        # Hand off to the rate-limited AI queue.
        celery.send_task("workers.tasks.ai.run_ai_analysis", args=[job.id], queue="ai")
        log.info("website job %s queued for AI", job.id)

    except Retry:
        raise                                   # let Celery reschedule
    except MaxRetriesExceededError:
        _fail(db, job_id, "domain rate limit: max retries exceeded")
    except Exception as exc:
        log.exception("website job %s failed", job_id)
        _fail(db, job_id, str(exc))
        raise
    finally:
        db.close()


def _fail(db, job_id: str, message: str):
    job = db.get(Job, job_id)
    if job:
        job.status = JobStatus.FAILED
        job.error = message[:1000]
        db.commit()
        publish(Event.ANALYSIS_FAILED, {"job_id": job_id, "error": message}, key=job_id)
