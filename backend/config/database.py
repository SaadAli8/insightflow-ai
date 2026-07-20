"""Database engine, session dependency, and local table bootstrap."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create local development tables.

    Production deployments should use migrations, but create_all keeps the
    educational Docker Compose stack one-command runnable.
    """
    import models  # noqa: F401  import registers models on Base

    Base.metadata.create_all(bind=engine)


__all__ = ["Base", "SessionLocal", "engine", "get_db", "init_db"]
