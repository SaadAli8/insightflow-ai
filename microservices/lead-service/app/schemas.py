from datetime import datetime

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    query: str = Field(min_length=5)
    industry: str = ""
    country: str = "US"
    target_roles: list[str] = Field(default_factory=lambda: ["CEO", "Founder", "Owner"])
    company_count: int = Field(default=10, ge=1, le=50)


class CampaignResponse(BaseModel):
    id: str
    name: str
    query: str
    industry: str
    country: str
    target_roles: list[str]
    company_count: int
    status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    id: str
    campaign_id: str
    name: str
    website_url: str
    domain: str
    industry: str
    country: str
    description: str
    source: str
    confidence: int
    status: str
    website_reachable: bool = False
    website_title: str = ""
    website_summary: str = ""
    website_final_url: str = ""
    website_verification_status: str = "not_verified"
    website_confidence: int = 0
    company_logo_url: str = ""
    website_signals: dict = Field(default_factory=dict)
    website_job_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PersonResponse(BaseModel):
    id: str
    campaign_id: str
    company_id: str
    full_name: str
    title: str
    role: str
    email: str
    phone: str
    linkedin_url: str
    source: str
    confidence: int
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignRunResponse(BaseModel):
    campaign: CampaignResponse
    companies: list[CompanyResponse]
    leads: list[PersonResponse]
    message: str


class CampaignRunStartResponse(BaseModel):
    campaign: CampaignResponse
    message: str


class ProviderStatusResponse(BaseModel):
    perplexity_configured: bool
    rapidapi_configured: bool
    lead_signal_configured: bool
    lead_signal_url: str
    ready: bool
