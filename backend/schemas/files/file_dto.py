from pydantic import BaseModel


class PresignRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"


class PresignResponse(BaseModel):
    file_id: str
    upload_url: str
    storage_key: str
