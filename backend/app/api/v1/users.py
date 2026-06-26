"""Admin user listing for the demo dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")

    limit = min(max(limit, 1), 500)
    stmt = select(User).order_by(User.email).limit(limit)
    return list(db.scalars(stmt))
