"""Website submission. The endpoint is a DISPATCHER: it creates the job and
returns immediately. No scraping, no LLM calls happen here."""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Job, JobStatus, JobType, User, Website
from app.db.session import get_db
from app.schemas import JobResponse, WebsiteSubmitRequest
from app.services import tasks
from app.services.events import Event, publish

router = APIRouter(prefix="/websites", tags=["websites"])


@router.post("", response_model=JobResponse, status_code=202)
def submit_website(
    body: WebsiteSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(400, "Provide a valid http(s) URL")

    website = Website(user_id=user.id, url=body.url, domain=parsed.netloc)
    job = Job(user_id=user.id, type=JobType.WEBSITE, status=JobStatus.QUEUED)
    db.add(website)
    db.flush()                  # get website.id without a second round trip
    job.website_id = website.id
    db.add(job)
    db.commit()
    db.refresh(job)

    # Hand off to the background worker, then announce the fact.
    tasks.enqueue_website(job.id)
    publish(Event.WEBSITE_SUBMITTED, {"job_id": job.id, "url": body.url}, key=job.id)

    return job
