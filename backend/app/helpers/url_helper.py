from urllib.parse import ParseResult, urlparse

from fastapi import HTTPException


class UrlHelper:
    @staticmethod
    def parse_http_url(value: str) -> ParseResult:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(400, "Provide a valid http(s) URL")
        return parsed
