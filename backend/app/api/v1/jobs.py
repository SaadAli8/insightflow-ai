"""Job status + results. The frontend polls these to update the dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import AnalysisResult, Job, User
from app.db.session import get_db
from app.schemas import AnalysisResultResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    scope: str = "mine",
):
    limit = min(max(limit, 1), 500)
    stmt = (
        select(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    if scope != "all" or user.role != "admin":
        stmt = stmt.where(Job.user_id == user.id)
    return list(db.scalars(stmt))


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}/result", response_model=AnalysisResultResponse)
def get_result(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or (job.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Job not found")
    result = db.scalar(select(AnalysisResult).where(AnalysisResult.job_id == job_id))
    if not result:
        raise HTTPException(404, "Result not ready")
    return result
