from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_reachable BOOLEAN DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_title VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_summary TEXT DEFAULT ''"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_final_url VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_verification_status VARCHAR DEFAULT 'not_verified'"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_confidence INTEGER DEFAULT 0"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS company_logo_url VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE lead_companies ADD COLUMN IF NOT EXISTS website_signals JSON DEFAULT '{}'::json"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
