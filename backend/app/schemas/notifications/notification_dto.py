from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    read_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
