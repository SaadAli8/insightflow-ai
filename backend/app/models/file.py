import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String, default="")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    s3_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["File"]
