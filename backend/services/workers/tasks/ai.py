"""AI task: the rate-limited stage.

Before calling OpenAI we take a token from the global LLM bucket. If the budget
is spent, the task re-queues itself with the bucket's wait time — so we never
exceed the provider's RPM no matter how many jobs pile up. Excess work simply
waits in the queue. THIS is "bounded by external rate limits, not your CPU"."""

import math

from celery import Task
from celery.exceptions import MaxRetriesExceededError, Retry
from openai import APIConnectionError, APITimeoutError, RateLimitError

from config.settings import settings
from utils.logger import get_logger
from models import AnalysisResult, File, Job, JobStatus, JobType, Website
from config.database import SessionLocal
from services import storage
from services.events import Event, publish
from services.workers.celery_app import celery
from services.workers.clients import openai_client
from services.workers.ratelimit import llm_gate

log = get_logger("task.ai")


@celery.task(bind=True, name="services.workers.tasks.ai.run_ai_analysis",
             max_retries=10, acks_late=True)
def run_ai_analysis(self: Task, job_id: str):
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        if job.status == JobStatus.COMPLETED:   # idempotent
            return

        # --- LLM backpressure: wait for a token rather than overrun the budget ---
        allowed, wait = llm_gate()
        if not allowed:
            log.info("LLM budget spent, re-queuing job %s in %.1fs", job_id, wait)
            raise self.retry(countdown=math.ceil(wait) + 1)

        job.status = JobStatus.ANALYZING
        db.commit()

        content = ""
        if job.extracted_s3_key:
            content = storage.download_bytes(job.extracted_s3_key).decode("utf-8", "ignore")

        # Website -> use web search; File -> analyze extracted text.
        if job.type == JobType.WEBSITE:
            website = db.get(Website, job.website_id)
            result, usage = openai_client.research_website(website.url, content)
        else:
            f = db.get(File, job.file_id)
            hint = f.filename if f else "document"
            result, usage = openai_client.analyze_text(content, source_hint=hint)

        # Persist the structured result.
        analysis = AnalysisResult(
            job_id=job.id,
            provider="openai",
            model=settings.openai_model,
            summary=result.get("summary", "")[:4000],
            result=result,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )
        db.add(analysis)
        job.status = JobStatus.COMPLETED
        job.error = None
        db.commit()

        # Announce completion. The notification consumer reacts to this.
        publish(Event.ANALYSIS_COMPLETED,
                {"job_id": job.id, "user_id": job.user_id, "type": job.type,
                 "summary": analysis.summary},
                key=job.id)
        publish(Event.REPORT_GENERATED, {"job_id": job.id}, key=job.id)
        log.info("AI analysis completed for job %s", job.id)

    except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
        # Transient provider errors -> exponential backoff retry.
        log.warning("transient OpenAI error on job %s: %s", job_id, exc)
        raise self.retry(exc=exc, countdown=min(60, 2 ** job_retry_count(self)))
    except Retry:
        raise
    except MaxRetriesExceededError:
        _fail(db, job_id, "AI analysis: max retries exceeded")
    except Exception as exc:
        log.exception("AI job %s failed", job_id)
        _fail(db, job_id, str(exc))
        raise
    finally:
        db.close()


def job_retry_count(task: Task) -> int:
    return (task.request.retries or 0) + 1


def _fail(db, job_id: str, message: str):
    job = db.get(Job, job_id)
    if job:
        job.status = JobStatus.FAILED
        job.error = message[:1000]
        db.commit()
        publish(Event.ANALYSIS_FAILED, {"job_id": job_id, "error": message}, key=job_id)
