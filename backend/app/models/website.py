import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str] = mapped_column(String)
    domain: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["Website"]
