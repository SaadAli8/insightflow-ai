"""FastAPI application entrypoint.

The API's whole job: authenticate, validate, create a job, hand it to a worker,
return immediately. Heavy work (scraping, OCR, LLM) never runs in a request."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1 import auth, files, jobs, notifications, users, websites
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db
from app.services.storage import ensure_storage_root

setup_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Local convenience: create tables + local storage directory on boot.
    init_db()
    ensure_storage_root()
    log.info("API started in %s mode", settings.environment)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

# /metrics for Prometheus.
Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# All business routes live under /api/v1 (matches the Kong routes).
app.include_router(auth.router, prefix="/api/v1")
app.include_router(websites.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
