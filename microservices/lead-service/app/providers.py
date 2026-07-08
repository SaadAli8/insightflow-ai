import json
import re
from urllib.parse import urlparse

import httpx

from app.config import settings


SOCIAL_DOMAINS = {
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "crunchbase.com",
}


def provider_status() -> dict:
    perplexity_configured = bool(settings.perplexity_api_key.strip())
    rapidapi_configured = bool(settings.rapidapi_key.strip())
    lead_signal_configured = bool(settings.lead_signal_service_url.strip())
    return {
        "perplexity_configured": perplexity_configured,
        "rapidapi_configured": rapidapi_configured,
        "lead_signal_configured": lead_signal_configured,
        "lead_signal_url": settings.lead_signal_service_url,
        "ready": perplexity_configured and rapidapi_configured and lead_signal_configured,
    }


def require_provider_config() -> None:
    missing = []
    if not settings.perplexity_api_key.strip():
        missing.append("PERPLEXITY_API_KEY")
    if not settings.rapidapi_key.strip():
        missing.append("RAPIDAPI_KEY")
    if not settings.lead_signal_service_url.strip():
        missing.append("LEAD_SIGNAL_SERVICE_URL")
    if missing:
        raise RuntimeError(f"Lead providers are not configured: {', '.join(missing)}")


def clean_domain(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.").strip(".")
    if not host or "." not in host:
        return ""
    if host in SOCIAL_DOMAINS or any(host.endswith(f".{domain}") for domain in SOCIAL_DOMAINS):
        return ""
    return host


def website_url(domain: str) -> str:
    return f"https://{domain}" if domain else ""


def _extract_json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", flags=re.S)
    if not match:
        return {}
    return json.loads(match.group(0))


def parse_confidence(value: object) -> int:
    if isinstance(value, int | float):
        return max(0, min(100, int(value)))
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized.isdigit():
            return max(0, min(100, int(normalized)))
        labels = {
            "very high": 95,
            "high": 85,
            "medium": 70,
            "moderate": 70,
            "low": 45,
        }
        return labels.get(normalized, 70)
    return 70


async def discover_companies(query: str, count: int) -> list[dict]:
    if not settings.perplexity_api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not configured")

    prompt = (
        f'Find at least {count} real companies for this lead-generation query: "{query}". '
        "Prioritize companies that match the industry and country exactly. "
        "Return only official company websites, not LinkedIn, directory pages, marketplaces, or news articles. "
        "Respond as JSON with a companies array. Each item must include: "
        "name, website_url, industry, country, description, confidence."
    )

    payload = {
        "model": settings.perplexity_model,
        "messages": [
            {"role": "system", "content": "Return strict JSON only. Do not include markdown."},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.perplexity_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.perplexity_api_base.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    parsed = _extract_json_object(content)
    companies = parsed.get("companies", [])

    seen: set[str] = set()
    cleaned: list[dict] = []
    for item in companies:
        domain = clean_domain(item.get("website_url") or item.get("website") or item.get("url"))
        if not domain or domain in seen:
            continue
        seen.add(domain)
        cleaned.append(
            {
                "name": item.get("name") or domain,
                "website_url": website_url(domain),
                "domain": domain,
                "industry": item.get("industry") or "",
                "country": item.get("country") or "",
                "description": item.get("description") or "",
                "source": "perplexity",
                "confidence": parse_confidence(item.get("confidence")),
            }
        )
        if len(cleaned) >= count:
            break
    return cleaned


async def inspect_website(website: str, company_name: str = "") -> dict:
    if not settings.lead_signal_service_url or not website:
        return {}

    try:
        async with httpx.AsyncClient(timeout=settings.lead_signal_timeout) as client:
            response = await client.post(
                f"{settings.lead_signal_service_url.rstrip('/')}/signals/website",
                json={"website_url": website, "company_name": company_name},
            )
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _role_matches(person: dict, target_roles: list[str]) -> bool:
    if not target_roles:
        return True
    haystack = " ".join(
        str(person.get(key) or "") for key in ("title", "seniority", "role", "headline")
    ).lower()
    normalized = [role.lower() for role in target_roles]
    return any(role in haystack for role in normalized) or any(
        word in haystack for word in ("owner", "founder", "chief", "ceo", "president", "partner")
    )


async def find_people_by_domain(domain: str, target_roles: list[str], limit: int = 10) -> list[dict]:
    if not settings.rapidapi_key:
        return []

    payload = {
        "companyFilters": {"primary_domain": domain},
        "count": limit,
        "offset": 0,
    }
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": settings.rapidapi_apollo_host,
        "x-rapidapi-key": settings.rapidapi_key,
    }

    async with httpx.AsyncClient(timeout=settings.rapidapi_timeout) as client:
        response = await client.post(
            f"https://{settings.rapidapi_apollo_host}/people/findFromCompany",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    people = []
    for person in data.get("items", []):
        if not _role_matches(person, target_roles):
            continue
        people.append(
            {
                "full_name": person.get("name") or "Unknown",
                "title": person.get("title") or "",
                "role": person.get("seniority") or "",
                "email": person.get("email") or "",
                "phone": person.get("phone") or "",
                "linkedin_url": person.get("linkedin_url") or "",
                "source": "rapidapi_apollo",
                "confidence": 78,
                "raw": person,
            }
        )
    return people


async def submit_website_job(token: str, website: str) -> str | None:
    if not settings.submit_website_jobs or not website:
        return None

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.main_api_base.rstrip('/')}/api/v1/websites",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"url": website},
            )
            response.raise_for_status()
            return response.json().get("id")
    except Exception:
        return None
