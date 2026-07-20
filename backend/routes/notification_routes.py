from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from middleware import get_current_user
from models import User
from schemas import NotificationResponse
from services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    scope: str = "mine",
):
    return NotificationService(db).list_notifications(user, limit, scope)


@router.delete("")
def clear_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    scope: str = "mine",
):
    return NotificationService(db).clear_notifications(user, scope)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return NotificationService(db).mark_read(notification_id, user)
