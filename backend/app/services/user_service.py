from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import UserRepository
from app.utils.validator import clamp


class UserService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)

    def list_users(self, user: User, limit: int = 100):
        if user.role != "admin":
            raise HTTPException(403, "Admin access required")
        return self.users.list_users(clamp(limit, 1, 500))
