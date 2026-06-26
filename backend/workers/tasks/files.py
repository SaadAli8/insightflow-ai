"""File task: download the upload, extract text (OCR if needed), store the text,
then hand off to the AI queue. This is the CPU-bound stage (prefork pool)."""

from celery import Task
from celery.exceptions import Retry

from app.core.logging import get_logger
from app.db.models import File, Job, JobStatus
from app.db.session import SessionLocal
from app.services import storage
from app.services.events import Event, publish
from workers.celery_app import celery
from workers.extractors import extract_text

log = get_logger("task.file")


@celery.task(bind=True, name="workers.tasks.files.process_file",
             max_retries=3, acks_late=True)
def process_file(self: Task, job_id: str):
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        if job.status == JobStatus.COMPLETED:   # idempotent
            return

        f = db.get(File, job.file_id)
        job.status = JobStatus.EXTRACTING
        job.attempts += 1
        db.commit()
        publish(Event.ANALYSIS_STARTED, {"job_id": job.id, "type": "file"}, key=job.id)

        # Download -> extract -> store extracted text.
        data = storage.download_bytes(f.s3_key)
        text = extract_text(f.filename, f.content_type, data)

        key = f"extracted/{job.id}.txt"
        storage.upload_bytes(key, text.encode("utf-8"), "text/plain")
        job.extracted_s3_key = key
        db.commit()
        log.info("extracted %d chars from %s", len(text), f.filename)

        celery.send_task("workers.tasks.ai.run_ai_analysis", args=[job.id], queue="ai")

    except Retry:
        raise
    except Exception as exc:
        log.exception("file job %s failed", job_id)
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error = str(exc)[:1000]
            db.commit()
            publish(Event.ANALYSIS_FAILED, {"job_id": job_id, "error": str(exc)}, key=job_id)
        raise
    finally:
        db.close()
