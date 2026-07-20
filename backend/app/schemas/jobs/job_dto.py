from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    website_id: str | None = None
    file_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
