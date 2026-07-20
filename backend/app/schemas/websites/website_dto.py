from pydantic import BaseModel


class WebsiteSubmitRequest(BaseModel):
    url: str
