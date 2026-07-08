import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CampaignStatus:
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CompanyStatus:
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    FAILED = "failed"


class LeadCampaign(Base):
    __tablename__ = "lead_campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    query: Mapped[str] = mapped_column(Text)
    industry: Mapped[str] = mapped_column(String, default="")
    country: Mapped[str] = mapped_column(String, default="US")
    target_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    company_count: Mapped[int] = mapped_column(Integer, default=10)
    status: Mapped[str] = mapped_column(String, default=CampaignStatus.DRAFT, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LeadCompany(Base):
    __tablename__ = "lead_companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("lead_campaigns.id"), index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    website_url: Mapped[str] = mapped_column(String, default="")
    domain: Mapped[str] = mapped_column(String, index=True)
    industry: Mapped[str] = mapped_column(String, default="")
    country: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, default="perplexity")
    confidence: Mapped[int] = mapped_column(Integer, default=70)
    status: Mapped[str] = mapped_column(String, default=CompanyStatus.DISCOVERED, index=True)
    website_reachable: Mapped[bool] = mapped_column(Boolean, default=False)
    website_title: Mapped[str] = mapped_column(String, default="")
    website_summary: Mapped[str] = mapped_column(Text, default="")
    website_final_url: Mapped[str] = mapped_column(String, default="")
    website_verification_status: Mapped[str] = mapped_column(String, default="not_verified")
    website_confidence: Mapped[int] = mapped_column(Integer, default=0)
    company_logo_url: Mapped[str] = mapped_column(String, default="")
    website_signals: Mapped[dict] = mapped_column(JSON, default=dict)
    website_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadPerson(Base):
    __tablename__ = "lead_people"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("lead_campaigns.id"), index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("lead_companies.id"), index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    full_name: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    linkedin_url: Mapped[str] = mapped_column(String, default="")
    source: Mapped[str] = mapped_column(String, default="rapidapi_apollo")
    confidence: Mapped[int] = mapped_column(Integer, default=75)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("lead_campaigns.id"), index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
