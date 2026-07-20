from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from middleware import get_current_user
from models import User
from schemas import AnalysisResultResponse, JobResponse
from services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    scope: str = "mine",
):
    return JobService(db).list_jobs(user, limit, scope)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return JobService(db).get_job(job_id, user)


@router.get("/{job_id}/result", response_model=AnalysisResultResponse)
def get_result(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return JobService(db).get_result(job_id, user)
