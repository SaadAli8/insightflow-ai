"""Bridge so the API can enqueue Celery tasks WITHOUT importing the heavy task
code (OpenAI SDK, OCR libs, etc.). We send tasks by name through the broker.

This is the key separation: the API only CREATES jobs and hands them off; the
workers do the heavy lifting."""

from workers.celery_app import celery

# Task names (must match the @celery.task(name=...) in workers/tasks/*).
ANALYZE_WEBSITE = "workers.tasks.website.analyze_website"
PROCESS_FILE = "workers.tasks.files.process_file"


def enqueue_website(job_id: str) -> None:
    celery.send_task(ANALYZE_WEBSITE, args=[job_id], queue="website")


def enqueue_file(job_id: str) -> None:
    celery.send_task(PROCESS_FILE, args=[job_id], queue="file")
