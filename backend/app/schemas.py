"""Pydantic request/response models (the API contract)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Websites ---
class WebsiteSubmitRequest(BaseModel):
    url: str


# --- Jobs ---
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


# --- Notifications ---
class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    read_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
