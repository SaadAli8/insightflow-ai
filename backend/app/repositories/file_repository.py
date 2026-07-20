from sqlalchemy.orm import Session

from app.models import File, Job, JobStatus, JobType
from app.repositories.base_repository import BaseRepository


class FileRepository(BaseRepository[File]):
    model = File

    def __init__(self, db: Session):
        super().__init__(db)

    def create_upload_job(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        size: int,
        storage_key: str,
    ) -> Job:
        file_record = File(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size,
            s3_key=storage_key,
            status="uploaded",
        )
        job = Job(user_id=user_id, type=JobType.FILE, status=JobStatus.QUEUED)
        self.db.add(file_record)
        self.db.flush()
        job.file_id = file_record.id
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_user_file(self, file_id: str, user_id: str, is_admin: bool = False) -> File | None:
        file_record = self.get(file_id)
        if not file_record or (file_record.user_id != user_id and not is_admin):
            return None
        return file_record

    def create_job_for_file(self, file_record: File, user_id: str) -> Job:
        file_record.status = "uploaded"
        job = Job(user_id=user_id, type=JobType.FILE, status=JobStatus.QUEUED, file_id=file_record.id)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
