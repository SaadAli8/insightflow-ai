from datetime import datetime

from pydantic import BaseModel


class AnalysisResultResponse(BaseModel):
    id: str
    job_id: str
    provider: str
    model: str
    summary: str
    result: dict
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime

    class Config:
        from_attributes = True
