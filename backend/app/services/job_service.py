from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import AnalysisResultRepository, JobRepository
from app.utils.validator import clamp


class JobService:
    def __init__(self, db: Session):
        self.jobs = JobRepository(db)
        self.results = AnalysisResultRepository(db)

    def list_jobs(self, user: User, limit: int = 100, scope: str = "mine"):
        return self.jobs.list_visible(user, clamp(limit, 1, 500), scope)

    def get_job(self, job_id: str, user: User):
        job = self.jobs.get_visible(job_id, user)
        if not job:
            raise HTTPException(404, "Job not found")
        return job

    def get_result(self, job_id: str, user: User):
        self.get_job(job_id, user)
        result = self.results.find_by_job_id(job_id)
        if not result:
            raise HTTPException(404, "Result not ready")
        return result
