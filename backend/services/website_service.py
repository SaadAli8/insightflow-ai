from sqlalchemy.orm import Session

from helpers import UrlHelper
from models import User
from repositories import WebsiteRepository
from schemas import WebsiteSubmitRequest
from services import tasks
from services.events import Event, publish


class WebsiteService:
    def __init__(self, db: Session):
        self.websites = WebsiteRepository(db)

    def submit(self, body: WebsiteSubmitRequest, user: User):
        parsed = UrlHelper.parse_http_url(body.url)
        job = self.websites.create_submission(user.id, body.url, parsed.netloc)
        tasks.enqueue_website(job.id)
        publish(Event.WEBSITE_SUBMITTED, {"job_id": job.id, "url": body.url}, key=job.id)
        return job
