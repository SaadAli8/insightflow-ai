from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Job, User
from repositories.base_repository import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    def __init__(self, db: Session):
        super().__init__(db)

    def list_visible(self, user: User, limit: int, scope: str) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        if scope != "all" or user.role != "admin":
            stmt = stmt.where(Job.user_id == user.id)
        return list(self.db.scalars(stmt))

    def get_visible(self, job_id: str, user: User) -> Job | None:
        job = self.get(job_id)
        if not job or (job.user_id != user.id and user.role != "admin"):
            return None
        return job
