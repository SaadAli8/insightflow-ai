"""Synchronous SQLAlchemy engine + session.

We use sync (not async) on purpose: it keeps the code simple and is shared by
both the API and the Celery workers. The API does almost no DB work per request
(create a row, return) so sync is plenty fast; all heavy work lives in workers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # drop dead connections instead of erroring
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
