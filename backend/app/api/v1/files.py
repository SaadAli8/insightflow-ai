"""File upload + analysis.

Two upload paths are provided:

  POST /files/upload   -> simple multipart upload. The API stores bytes in the
                          shared local storage directory, creates the job, and
                          returns immediately.

  POST /files/presign  -> not available in local filesystem mode. Direct
                          browser-to-storage uploads require object storage.

Either way, the API only records metadata and enqueues a job — extraction/OCR/AI
all happen in the file worker."""

import uuid

from fastapi import APIRouter, Depends, File as UploadFileMarker, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import File, Job, JobStatus, JobType, User
from app.db.session import get_db
from app.schemas import JobResponse
from app.services import storage, tasks
from app.services.events import Event, publish

router = APIRouter(prefix="/files", tags=["files"])


def _new_key(user_id: str, filename: str) -> str:
    return f"uploads/{user_id}/{uuid.uuid4()}/{filename}"


def _create_file_and_job(db: Session, user: User, filename: str, content_type: str,
                         size: int, key: str) -> Job:
    f = File(user_id=user.id, filename=filename, content_type=content_type,
             size_bytes=size, s3_key=key, status="uploaded")
    job = Job(user_id=user.id, type=JobType.FILE, status=JobStatus.QUEUED)
    db.add(f)
    db.flush()
    job.file_id = f.id
    db.add(job)
    db.commit()
    db.refresh(job)
    tasks.enqueue_file(job.id)
    publish(Event.FILE_UPLOADED, {"job_id": job.id, "filename": filename}, key=job.id)
    return job


# ---- Path 1: simple multipart upload (great for local testing) --------------
@router.post("/upload", response_model=JobResponse, status_code=202)
def upload_file(
    upload: UploadFile = UploadFileMarker(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = upload.file.read()
    key = _new_key(user.id, upload.filename or "file")
    storage.upload_bytes(key, data, upload.content_type or "application/octet-stream")
    return _create_file_and_job(
        db, user, upload.filename or "file", upload.content_type or "", len(data), key
    )


# ---- Path 2: direct-to-object-storage upload (disabled locally) -------------
class PresignRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"


class PresignResponse(BaseModel):
    file_id: str
    upload_url: str
    storage_key: str


@router.post("/presign", response_model=PresignResponse)
def presign_upload(
    body: PresignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raise HTTPException(
        status_code=501,
        detail="Direct browser-to-storage uploads are disabled in local filesystem mode. Use /files/upload.",
    )


@router.post("/{file_id}/complete", response_model=JobResponse, status_code=202)
def complete_upload(
    file_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    f = db.get(File, file_id)
    if not f or f.user_id != user.id:
        raise HTTPException(404, "File not found")
    f.status = "uploaded"
    job = Job(user_id=user.id, type=JobType.FILE, status=JobStatus.QUEUED, file_id=f.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    tasks.enqueue_file(job.id)
    publish(Event.FILE_UPLOADED, {"job_id": job.id, "filename": f.filename}, key=job.id)
    return job
