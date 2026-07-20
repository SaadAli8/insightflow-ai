from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.helpers.response_helper import ResponseHelper
from app.models import User
from app.repositories import NotificationRepository
from app.utils.validator import clamp


class NotificationService:
    def __init__(self, db: Session):
        self.notifications = NotificationRepository(db)

    @staticmethod
    def _validate_scope(scope: str) -> None:
        if scope not in {"mine", "all"}:
            raise HTTPException(400, "scope must be 'mine' or 'all'")

    def list_notifications(self, user: User, limit: int = 10, scope: str = "mine"):
        self._validate_scope(scope)
        return self.notifications.list_visible(user, clamp(limit, 1, 100), scope)

    def clear_notifications(self, user: User, scope: str = "mine") -> dict:
        self._validate_scope(scope)
        return ResponseHelper.deleted(self.notifications.clear_visible(user, scope))

    def mark_read(self, notification_id: str, user: User):
        notification = self.notifications.mark_read(notification_id, user)
        if not notification:
            raise HTTPException(404, "Notification not found")
        return notification
