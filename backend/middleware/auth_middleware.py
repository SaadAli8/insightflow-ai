from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from config.database import get_db
from models import User
from repositories import UserRepository
from security import decode_token

_bearer = HTTPBearer(auto_error=True)


class AuthMiddleware:
    def __init__(self, db: Session):
        self.users = UserRepository(db)

    def get_current_user(self, token: str) -> User:
        try:
            payload = decode_token(token)
        except JWTError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

        user = self.users.get(payload.get("sub"))
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        return user


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    return AuthMiddleware(db).get_current_user(creds.credentials)
