from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Notification, User
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def __init__(self, db: Session):
        super().__init__(db)

    def list_visible(self, user: User, limit: int, scope: str) -> list[Notification]:
        stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
        if scope != "all" or user.role != "admin":
            stmt = stmt.where(Notification.user_id == user.id)
        return list(self.db.scalars(stmt))

    def clear_visible(self, user: User, scope: str) -> int:
        stmt = delete(Notification)
        if scope != "all" or user.role != "admin":
            stmt = stmt.where(Notification.user_id == user.id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or 0

    def mark_read(self, notification_id: str, user: User) -> Notification | None:
        notification = self.get(notification_id)
        if not notification or (notification.user_id != user.id and user.role != "admin"):
            return None
        notification.read_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(notification)
        return notification
