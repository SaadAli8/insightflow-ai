from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from middleware import get_current_user
from models import User
from schemas import JobResponse, WebsiteSubmitRequest
from services.website_service import WebsiteService

router = APIRouter(prefix="/websites", tags=["websites"])


@router.post("", response_model=JobResponse, status_code=202)
def submit_website(
    body: WebsiteSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return WebsiteService(db).submit(body, user)
