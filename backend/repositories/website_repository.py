from sqlalchemy.orm import Session

from models import Job, JobStatus, JobType, Website
from repositories.base_repository import BaseRepository


class WebsiteRepository(BaseRepository[Website]):
    model = Website

    def __init__(self, db: Session):
        super().__init__(db)

    def create_submission(self, user_id: str, url: str, domain: str) -> Job:
        website = Website(user_id=user_id, url=url, domain=domain)
        job = Job(user_id=user_id, type=JobType.WEBSITE, status=JobStatus.QUEUED)
        self.db.add(website)
        self.db.flush()
        job.website_id = website.id
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
