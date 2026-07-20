import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class JobType:
    WEBSITE = "website"
    FILE = "file"


class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default=JobStatus.QUEUED, index=True)
    website_id: Mapped[str | None] = mapped_column(ForeignKey("websites.id"), nullable=True)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    extracted_s3_key: Mapped[str | None] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


__all__ = ["Job", "JobStatus", "JobType"]
