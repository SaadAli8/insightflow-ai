import asyncio
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import current_user_id
from app.config import settings
from app.db import SessionLocal, get_db, init_db
from app.models import CampaignStatus, CompanyStatus, LeadCampaign, LeadCompany, LeadEvent, LeadPerson
from app.providers import (
    discover_companies,
    find_people_by_domain,
    inspect_website,
    provider_status,
    require_provider_config,
    submit_website_job,
)
from app.schemas import (
    CampaignCreate,
    CampaignResponse,
    CampaignRunStartResponse,
    CompanyResponse,
    PersonResponse,
    ProviderStatusResponse,
)

_bearer = HTTPBearer(auto_error=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.service_name, version="1.0.0", lifespan=lifespan)


def _campaign_query(campaign: LeadCampaign) -> str:
    return " ".join(
        part
        for part in [
            campaign.query,
            f"industry: {campaign.industry}" if campaign.industry else "",
            f"country: {campaign.country}" if campaign.country else "",
            f"target roles: {', '.join(campaign.target_roles)}" if campaign.target_roles else "",
        ]
        if part
    )


async def execute_campaign_run(campaign_id: str, user_id: str, token: str) -> None:
    db = SessionLocal()
    try:
        campaign = db.get(LeadCampaign, campaign_id)
        if not campaign or campaign.user_id != user_id:
            return

        discovered = await discover_companies(_campaign_query(campaign), campaign.company_count)
        companies_count = 0
        leads_count = 0
        failed_companies = 0

        for item in discovered:
            website_job_id = await submit_website_job(token, item["website_url"])
            signals = await inspect_website(item["website_url"], item["name"])
            company = LeadCompany(
                user_id=user_id,
                campaign_id=campaign.id,
                name=item["name"],
                website_url=item["website_url"],
                domain=item["domain"],
                industry=item["industry"],
                country=item["country"] or campaign.country,
                description=item["description"],
                source=item["source"],
                confidence=item["confidence"],
                website_reachable=bool(signals.get("reachable")),
                website_title=signals.get("title") or "",
                website_summary=signals.get("summary") or signals.get("description") or "",
                website_final_url=signals.get("final_url") or "",
                website_verification_status=signals.get("verification_status") or "not_verified",
                website_confidence=int(signals.get("confidence") or 0),
                company_logo_url=signals.get("logo_url") or "",
                website_signals=signals,
                website_job_id=website_job_id,
            )
            db.add(company)
            db.flush()

            try:
                people = await find_people_by_domain(
                    company.domain,
                    campaign.target_roles,
                    limit=settings.lead_people_per_company,
                )
            except Exception as exc:
                failed_companies += 1
                company.status = CompanyStatus.FAILED
                company.website_signals = {**(signals or {}), "people_error": str(exc)}
                companies_count += 1
                db.add(
                    LeadEvent(
                        user_id=user_id,
                        campaign_id=campaign.id,
                        event_type="COMPANY_ENRICHMENT_FAILED",
                        payload={"domain": company.domain, "error": str(exc)},
                    )
                )
                db.commit()
                if settings.lead_enrichment_delay_seconds:
                    await asyncio.sleep(settings.lead_enrichment_delay_seconds)
                continue

            for person in people:
                db.add(
                    LeadPerson(
                        user_id=user_id,
                        campaign_id=campaign.id,
                        company_id=company.id,
                        full_name=person["full_name"],
                        title=person["title"],
                        role=person["role"],
                        email=person["email"],
                        phone=person["phone"],
                        linkedin_url=person["linkedin_url"],
                        source=person["source"],
                        confidence=person["confidence"],
                        raw=person["raw"],
                    )
                )
                leads_count += 1

            company.status = CompanyStatus.ENRICHED
            companies_count += 1
            db.add(
                LeadEvent(
                    user_id=user_id,
                    campaign_id=campaign.id,
                    event_type="COMPANY_ENRICHED",
                    payload={"domain": company.domain, "leads": len(people), "website_reachable": company.website_reachable},
                )
            )
            db.commit()
            if settings.lead_enrichment_delay_seconds:
                await asyncio.sleep(settings.lead_enrichment_delay_seconds)

        campaign.status = CampaignStatus.COMPLETED
        campaign.error = f"{failed_companies} company enrichment request(s) failed." if failed_companies else None
        db.add(
            LeadEvent(
                user_id=user_id,
                campaign_id=campaign.id,
                event_type="CAMPAIGN_COMPLETED",
                payload={"companies": companies_count, "leads": leads_count, "failed_companies": failed_companies},
            )
        )
        db.commit()
    except Exception as exc:
        campaign = db.get(LeadCampaign, campaign_id)
        if campaign:
            campaign.status = CampaignStatus.FAILED
            campaign.error = str(exc)
            db.add(
                LeadEvent(
                    user_id=user_id,
                    campaign_id=campaign.id,
                    event_type="CAMPAIGN_FAILED",
                    payload={"error": str(exc)},
                )
            )
            db.commit()
    finally:
        db.close()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/lead/v1/provider-status", response_model=ProviderStatusResponse)
def get_provider_status(user_id: str = Depends(current_user_id)):
    return provider_status()


@app.post("/lead/v1/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(
    body: CampaignCreate,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    campaign = LeadCampaign(
        user_id=user_id,
        name=body.name,
        query=body.query,
        industry=body.industry,
        country=body.country,
        target_roles=body.target_roles,
        company_count=body.company_count,
    )
    db.add(campaign)
    db.flush()
    db.add(LeadEvent(user_id=user_id, campaign_id=campaign.id, event_type="CAMPAIGN_CREATED", payload=body.model_dump()))
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/lead/v1/campaigns", response_model=list[CampaignResponse])
def list_campaigns(user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    return db.scalars(
        select(LeadCampaign).where(LeadCampaign.user_id == user_id).order_by(LeadCampaign.created_at.desc())
    ).all()


@app.get("/lead/v1/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    campaign = db.get(LeadCampaign, campaign_id)
    if not campaign or campaign.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return campaign


@app.get("/lead/v1/campaigns/{campaign_id}/companies", response_model=list[CompanyResponse])
def list_companies(campaign_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    return db.scalars(
        select(LeadCompany)
        .where(LeadCompany.user_id == user_id, LeadCompany.campaign_id == campaign_id)
        .order_by(LeadCompany.created_at.desc())
    ).all()


@app.get("/lead/v1/campaigns/{campaign_id}/leads", response_model=list[PersonResponse])
def list_campaign_leads(campaign_id: str, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)):
    return db.scalars(
        select(LeadPerson)
        .where(LeadPerson.user_id == user_id, LeadPerson.campaign_id == campaign_id)
        .order_by(LeadPerson.created_at.desc())
    ).all()


@app.get("/lead/v1/leads", response_model=list[PersonResponse])
def list_leads(user_id: str = Depends(current_user_id), db: Session = Depends(get_db), limit: int = 200):
    safe_limit = min(max(limit, 1), 500)
    return db.scalars(
        select(LeadPerson)
        .where(LeadPerson.user_id == user_id)
        .order_by(LeadPerson.created_at.desc())
        .limit(safe_limit)
    ).all()


@app.post("/lead/v1/campaigns/{campaign_id}/run", response_model=CampaignRunStartResponse, status_code=202)
async def run_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
):
    campaign = db.get(LeadCampaign, campaign_id)
    if not campaign or campaign.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Campaign is already running")

    try:
        require_provider_config()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    db.execute(delete(LeadPerson).where(LeadPerson.campaign_id == campaign.id))
    db.execute(delete(LeadCompany).where(LeadCompany.campaign_id == campaign.id))
    campaign.status = CampaignStatus.RUNNING
    campaign.error = None
    db.add(LeadEvent(user_id=user_id, campaign_id=campaign.id, event_type="CAMPAIGN_STARTED", payload={}))
    db.commit()
    db.refresh(campaign)

    background_tasks.add_task(execute_campaign_run, campaign.id, user_id, creds.credentials)
    return CampaignRunStartResponse(campaign=campaign, message="Campaign run started. Companies and leads will update as enrichment completes.")
