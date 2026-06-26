"""Create tables on startup.

For local dev we just call create_all(). In production you'd switch to Alembic
migrations — but this keeps "docker compose up" a one-command experience."""

from app.db import models  # noqa: F401  (import registers the models on Base)
from app.db.session import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
