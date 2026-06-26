"""Notification endpoints. Notifications are CREATED by the Kafka consumer when
it sees an ANALYSIS_COMPLETED event — the API only reads them here."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Notification, User
from app.db.session import get_db
from app.schemas import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    scope: str = "mine",
):
    if scope not in {"mine", "all"}:
        raise HTTPException(400, "scope must be 'mine' or 'all'")

    limit = min(max(limit, 1), 100)
    stmt = (
        select(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if scope != "all" or user.role != "admin":
        stmt = stmt.where(Notification.user_id == user.id)
    return list(db.scalars(stmt))


@router.delete("")
def clear_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    scope: str = "mine",
):
    if scope not in {"mine", "all"}:
        raise HTTPException(400, "scope must be 'mine' or 'all'")

    stmt = delete(Notification)
    if scope != "all" or user.role != "admin":
        stmt = stmt.where(Notification.user_id == user.id)

    result = db.execute(stmt)
    db.commit()
    return {"deleted": result.rowcount or 0}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    n = db.get(Notification, notification_id)
    if not n or (n.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Notification not found")
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(n)
    return n
