"""Crustdata API adapter with Redis caching and credit budget enforcement.

Endpoints covered: person search, person enrich, job search. Everything else
in Crustdata's catalog (company enrichment, monitoring, etc.) is intentionally
omitted — the agent does not use it and adding unused endpoints would burn
credits, complicate the code, and slow reviews.

Safety features:
  - dry_run=True (default) returns realistic mock data. No credits spent.
  - Redis cache (24h TTL) deduplicates identical queries.
  - Credit budget pre-check; refusal rather than post-failure.
  - Every successful charge is exposed via credits_used for the ledger.

Uncertainty acknowledged: exact Crustdata response field names may differ
from what _normalize_* expects. Those functions are the only place to fix
it — the orchestrator only ever sees the normalized shape below.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.core.config import get_settings


logger = logging.getLogger(__name__)


CRUSTDATA_BASE_URL = "https://api.crustdata.com"

# Per-result costs as of the hackathon docs. If these drift, adjust one dict.
CREDIT_COSTS = {
    "person_search": 0.03,
    "person_enrich": 2.0,
    "job_search": 0.03,
}


class CrustdataError(RuntimeError):
    """Base class for Crustdata adapter failures."""


class CreditBudgetExceeded(CrustdataError):
    """Call would exceed the configured credit budget."""


class CrustdataRateLimitError(CrustdataError):
    """Upstream returned 429."""


# --- Normalized internal shapes (the orchestrator only sees these) ---

def _normalize_person_search(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract contacts from a raw Crustdata person search response.

    Adjust this function alone if upstream field names change.
    """
    profiles = raw.get("profiles") or raw.get("data") or []
    contacts: list[dict[str, Any]] = []
    for profile in profiles:
        basic = profile.get("basic_profile") or profile.get("basic") or {}
        contact = profile.get("contact") or {}
        contacts.append(
            {
                "name": basic.get("name") or basic.get("full_name"),
                "title": basic.get("current_title") or basic.get("headline"),
                "company": basic.get("current_company"),
                "location": basic.get("location"),
                "linkedin_url": basic.get("linkedin_url") or basic.get("url"),
                "has_business_email": bool(contact.get("has_business_email")),
                "has_personal_email": bool(contact.get("has_personal_email")),
            }
        )
    return contacts


def _normalize_person_enrich(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract contact details from a raw Crustdata person enrich response."""
    data = raw.get("data") or raw.get("profile") or raw
    basic = data.get("basic_profile") or data.get("basic") or {}
    contact = data.get("contact") or {}
    return {
        "name": basic.get("name") or basic.get("full_name"),
        "title": basic.get("current_title") or basic.get("headline"),
        "company": basic.get("current_company"),
        "location": basic.get("location"),
        "linkedin_url": basic.get("linkedin_url") or basic.get("url"),
        "email": contact.get("business_email")
        or contact.get("email")
        or contact.get("personal_email"),
        "phone": contact.get("phone"),
        "headline": basic.get("headline"),
    }


def _normalize_job_search(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract job entries from a raw Crustdata job search response."""
    jobs = raw.get("jobs") or raw.get("data") or raw.get("results") or []
    out: list[dict[str, Any]] = []
    for job in jobs:
        out.append(
            {
                "title": job.get("title"),
                "company": job.get("company") or job.get("company_name"),
                "location": job.get("location"),
                "url": job.get("url") or job.get("job_url"),
                "posted_at": job.get("posted_at") or job.get("date_posted"),
            }
        )
    return out


# --- Deterministic mock data for dry_run ---

def _mock_person_search(title: str, company: str | None, limit: int) -> list[dict[str, Any]]:
    n = max(1, min(limit, 5))
    return [
        {
            "name": f"Mock Contact {i + 1}",
            "title": title,
            "company": company or "Mock Company",
            "location": "Remote",
            "linkedin_url": f"https://linkedin.com/in/mock-{title.lower().replace(' ', '-')}-{i + 1}",
            "has_business_email": True,
            "has_personal_email": False,
        }
        for i in range(n)
    ]


def _mock_person_enrich(linkedin_url: str) -> dict[str, Any]:
    return {
        "name": "Mock Contact",
        "title": "Engineering Manager",
        "company": "Mock Company",
        "location": "Remote",
        "linkedin_url": linkedin_url,
        "email": "mock.contact@example.com",
        "phone": None,
        "headline": "Engineering leader at a fast-growing startup",
    }


def _mock_job_search(query: str, limit: int) -> list[dict[str, Any]]:
    n = max(1, min(limit, 5))
    return [
        {
            "title": f"{query} Role {i + 1}",
            "company": "Mock Company",
            "location": "Remote",
            "url": f"https://example.com/jobs/mock-{i + 1}",
            "posted_at": None,
        }
        for i in range(n)
    ]


# --- Client ---

class CrustdataClient:
    """Async Crustdata adapter. One instance per agent run."""

    def __init__(
        self,
        api_key: str | None = None,
        redis_client: aioredis.Redis | None = None,
        credit_budget: float | None = None,
        dry_run: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.crustdata_api_key
        self._redis = redis_client  # may be None; created lazily
        self._budget = (
            credit_budget if credit_budget is not None else settings.agent_credit_budget
        )
        self._dry_run = (
            dry_run if dry_run is not None else settings.crustdata_dry_run
        )
        self._cache_ttl = settings.crustdata_cache_ttl_seconds
        self._credits_used: float = 0.0
        self._timeout = timeout

    # --- public state ---

    @property
    def credits_used(self) -> float:
        return self._credits_used

    @property
    def credits_remaining(self) -> float:
        return max(0.0, self._budget - self._credits_used)

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    # --- lifecycle ---

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                get_settings().redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    # --- budget + caching helpers ---

    def _reserve_credits(self, estimated: float) -> None:
        if self._credits_used + estimated > self._budget:
            raise CreditBudgetExceeded(
                f"Estimated cost {estimated:.2f} would exceed budget "
                f"({self._credits_used:.2f}/{self._budget:.2f} used)"
            )
        self._credits_used += estimated

    @staticmethod
    def _cache_key(method: str, args: dict[str, Any]) -> str:
        payload = json.dumps(args, sort_keys=True, default=str).encode()
        digest = hashlib.sha256(payload).hexdigest()
        return f"crustdata:{method}:{digest}"

    async def _cache_get(self, key: str) -> Any | None:
        try:
            r = await self._get_redis()
            raw = await r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("crustdata_cache_get_failed", extra={"error": str(exc)})
            return None

    async def _cache_set(self, key: str, value: Any) -> None:
        try:
            r = await self._get_redis()
            await r.setex(key, self._cache_ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.warning("crustdata_cache_set_failed", extra={"error": str(exc)})

    # --- HTTP ---

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise CrustdataError(
                "CRUSTDATA_API_KEY is not configured and dry_run is False"
            )
        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{CRUSTDATA_BASE_URL}{path}", json=body, headers=headers
            )
        if response.status_code == 429:
            raise CrustdataRateLimitError(
                f"Crustdata rate limit hit: {response.text[:200]}"
            )
        if response.status_code >= 400:
            raise CrustdataError(
                f"Crustdata {path} failed ({response.status_code}): {response.text[:300]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise CrustdataError(
                f"Crustdata {path} returned non-JSON: {response.text[:200]}"
            ) from exc

    # --- public methods ---

    async def person_search(
        self,
        title: str,
        company: str | None = None,
        location: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        args = {
            "title": title,
            "company": company,
            "location": location,
            "limit": limit,
        }
        cache_key = self._cache_key("person_search", args)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.info("crustdata_cache_hit", extra={"method": "person_search"})
            return cached

        estimated = CREDIT_COSTS["person_search"] * limit
        self._reserve_credits(estimated)

        if self._dry_run:
            result = _mock_person_search(title, company, limit)
        else:
            body = {
                "filters": [
                    {"field": "current_title", "type": "(.)", "value": title},
                ],
                "limit": limit,
            }
            if company:
                body["filters"].append(
                    {"field": "current_company_name", "type": "(.)", "value": company}
                )
            if location:
                body["filters"].append(
                    {"field": "location", "type": "(.)", "value": location}
                )
            raw = await self._post("/screener/person/search", body)
            result = _normalize_person_search(raw)

        await self._cache_set(cache_key, result)
        return result

    async def person_enrich(self, linkedin_url: str) -> dict[str, Any]:
        args = {"linkedin_url": linkedin_url}
        cache_key = self._cache_key("person_enrich", args)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.info("crustdata_cache_hit", extra={"method": "person_enrich"})
            return cached

        self._reserve_credits(CREDIT_COSTS["person_enrich"])

        if self._dry_run:
            result = _mock_person_enrich(linkedin_url)
        else:
            body = {"professional_network_profile_url": linkedin_url}
            raw = await self._post("/screener/person/enrich", body)
            result = _normalize_person_enrich(raw)

        await self._cache_set(cache_key, result)
        return result

    async def job_search(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        args = {"query": query, "limit": limit}
        cache_key = self._cache_key("job_search", args)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            logger.info("crustdata_cache_hit", extra={"method": "job_search"})
            return cached

        estimated = CREDIT_COSTS["job_search"] * limit
        self._reserve_credits(estimated)

        if self._dry_run:
            result = _mock_job_search(query, limit)
        else:
            body = {"query": query, "limit": limit}
            raw = await self._post("/screener/job/search", body)
            result = _normalize_job_search(raw)

        await self._cache_set(cache_key, result)
        return result
