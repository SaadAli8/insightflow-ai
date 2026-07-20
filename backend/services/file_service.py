from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from helpers import FileHelper
from models import User
from repositories import FileRepository
from services import storage, tasks
from services.events import Event, publish


class FileService:
    def __init__(self, db: Session):
        self.files = FileRepository(db)

    def upload(self, upload: UploadFile, user: User):
        data = upload.file.read()
        filename = upload.filename or "file"
        content_type = upload.content_type or "application/octet-stream"
        key = FileHelper.new_storage_key(user.id, filename)
        storage.upload_bytes(key, data, content_type)
        job = self.files.create_upload_job(user.id, filename, upload.content_type or "", len(data), key)
        tasks.enqueue_file(job.id)
        publish(Event.FILE_UPLOADED, {"job_id": job.id, "filename": filename}, key=job.id)
        return job

    def complete_upload(self, file_id: str, user: User):
        file_record = self.files.get_user_file(file_id, user.id, user.role == "admin")
        if not file_record:
            raise HTTPException(404, "File not found")
        job = self.files.create_job_for_file(file_record, user.id)
        tasks.enqueue_file(job.id)
        publish(Event.FILE_UPLOADED, {"job_id": job.id, "filename": file_record.filename}, key=job.id)
        return job

    @staticmethod
    def presign_upload_disabled():
        raise HTTPException(
            status_code=501,
            detail="Direct browser-to-storage uploads are disabled in local filesystem mode. Use /files/upload.",
        )
