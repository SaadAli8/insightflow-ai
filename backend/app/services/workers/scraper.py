"""Lightweight, polite single-page fetch.

We deliberately keep scraping minimal: fetch the submitted page and extract its
main text. The heavy "research/crawl" is delegated to OpenAI's web search tool
(see openai_client.research_website). The fetch is best-effort — if it fails,
the AI step still runs using web search alone."""

import httpx
import trafilatura

from app.config.settings import settings
from app.utils.logger import get_logger

log = get_logger("scraper")


def fetch_clean_text(url: str) -> str:
    """Return cleaned main-content text for a URL, or '' on failure."""
    try:
        headers = {"User-Agent": settings.scrape_user_agent}
        with httpx.Client(timeout=settings.scrape_timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
        text = trafilatura.extract(resp.text) or ""
        log.info("fetched %s (%d chars cleaned)", url, len(text))
        return text
    except Exception as exc:
        log.warning("fetch failed for %s: %s", url, exc)
        return ""
