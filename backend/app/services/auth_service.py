from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import UserRepository
from app.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)

    def register(self, body: RegisterRequest):
        if self.users.find_by_email(body.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        return self.users.create_user(body.email, hash_password(body.password))

    def login(self, body: LoginRequest) -> TokenResponse:
        user = self.users.find_by_email(body.email)
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

        token = create_access_token(user.id, extra_claims={"role": user.role})
        return TokenResponse(access_token=token)
