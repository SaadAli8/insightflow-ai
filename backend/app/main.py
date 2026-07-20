"""FastAPI application entrypoint.

The API's whole job: authenticate, validate, create a job, hand it to a worker,
return immediately. Heavy work (scraping, OCR, LLM) never runs in a request."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.config.constants import API_V1_PREFIX
from app.routes import auth_routes, file_routes, job_routes, notification_routes, user_routes, website_routes
from app.config.database import init_db
from app.services.storage import ensure_storage_root
from app.utils import get_logger, setup_logging

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
app.include_router(auth_routes.router, prefix=API_V1_PREFIX)
app.include_router(website_routes.router, prefix=API_V1_PREFIX)
app.include_router(file_routes.router, prefix=API_V1_PREFIX)
app.include_router(job_routes.router, prefix=API_V1_PREFIX)
app.include_router(notification_routes.router, prefix=API_V1_PREFIX)
app.include_router(user_routes.router, prefix=API_V1_PREFIX)
