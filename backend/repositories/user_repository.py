from sqlalchemy import select
from sqlalchemy.orm import Session

from models import User
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, db: Session):
        super().__init__(db)

    def find_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create_user(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(self, limit: int) -> list[User]:
        stmt = select(User).order_by(User.email).limit(limit)
        return list(self.db.scalars(stmt))
