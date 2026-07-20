"""OpenAI client wrapper.

Website analysis uses OpenAI's WEB SEARCH tool (the "search API of ChatGPT") so
the model can research the live site instead of us building a full crawler.
File analysis uses a plain completion over the extracted text.

Both ask the model to return strict JSON so we can store structured results."""

import json
from urllib.parse import urlparse

from openai import OpenAI

from app.config.settings import settings
from app.utils.logger import get_logger

log = get_logger("openai")

_client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_request_timeout)


_ANALYSIS_SCHEMA_HINT = """
Respond with ONLY valid JSON (no markdown, no prose) in exactly this shape:
{
  "summary": "<2-4 sentence overview>",
  "category": "<one short category>",
  "key_points": ["...", "..."],
  "topics": ["...", "..."],
  "sentiment": "positive | neutral | negative",
  "entities": ["...", "..."],
  "risks_or_notes": ["..."]
}
""".strip()


def _extract_json(text: str) -> dict:
    """Models sometimes wrap JSON in ```json fences — strip and parse safely."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except Exception:
        return {"summary": text[:1000], "parse_error": True}


def _usage(resp) -> dict:
    u = getattr(resp, "usage", None)
    return {
        "prompt_tokens": getattr(u, "input_tokens", 0) if u else 0,
        "completion_tokens": getattr(u, "output_tokens", 0) if u else 0,
    }


def _mock_result(source: str, content: str, kind: str) -> tuple[dict, dict]:
    """Deterministic local-demo result when OPENAI_MOCK=true."""
    label = urlparse(source).netloc if kind == "website" else source
    preview = " ".join(content.split())[:220] if content else "No extracted text was available."
    result = {
        "summary": f"Mock analysis for {label}. The pipeline successfully accepted, queued, processed, and stored this {kind} job locally.",
        "category": "local-demo",
        "key_points": [
            "FastAPI returned quickly after creating the job.",
            "Celery workers processed the background work.",
            "The result was saved in Postgres and can be viewed in the UI.",
        ],
        "topics": ["kong", "celery", "background-processing", "local-demo"],
        "sentiment": "neutral",
        "entities": [label],
        "risks_or_notes": [
            "OPENAI_MOCK=true is enabled, so this result did not call OpenAI.",
            preview,
        ],
    }
    return result, {"prompt_tokens": 0, "completion_tokens": 0}


def research_website(url: str, page_content: str) -> tuple[dict, dict]:
    """Use the web search tool to research the website, then analyze it."""
    if settings.openai_mock:
        log.info("mock web-search analysis done for %s", url)
        return _mock_result(url, page_content, "website")

    prompt = (
        f"Research and analyze the website: {url}\n\n"
        "Use web search to understand what this site/company does, its products, "
        "reputation, and audience. Combine that with the page excerpt below.\n\n"
        f"--- PAGE EXCERPT ---\n{page_content[:8000]}\n--- END EXCERPT ---\n\n"
        f"{_ANALYSIS_SCHEMA_HINT}"
    )
    resp = _client.responses.create(
        model=settings.openai_model,
        tools=[{"type": settings.openai_search_tool}],
        input=prompt,
    )
    log.info("web-search analysis done for %s", url)
    return _extract_json(resp.output_text), _usage(resp)


def analyze_text(content: str, source_hint: str = "document") -> tuple[dict, dict]:
    """Analyze already-extracted text (file path). No web search needed."""
    if settings.openai_mock:
        log.info("mock text analysis done (%s chars)", len(content))
        return _mock_result(source_hint, content, "file")

    prompt = (
        f"Analyze the following {source_hint} content.\n\n"
        f"--- CONTENT ---\n{content[:12000]}\n--- END CONTENT ---\n\n"
        f"{_ANALYSIS_SCHEMA_HINT}"
    )
    resp = _client.responses.create(model=settings.openai_model, input=prompt)
    log.info("text analysis done (%s chars)", len(content))
    return _extract_json(resp.output_text), _usage(resp)
