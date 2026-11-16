"""Tests for the Crustdata adapter.

All tests use dry_run=True — no credits spent, no network calls.
Each test uses a *unique* query string so the Redis cache never causes
test cross-contamination (the cache TTL is 24h, so re-runs of the same
test would otherwise see cached data and skip the charge path).
"""
import uuid

import pytest

from app.agents.crustdata import (
    CREDIT_COSTS,
    CreditBudgetExceeded,
    CrustdataClient,
)


def _unique(prefix: str) -> str:
    """Return a query string that cannot collide with a previous test run."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@pytest.mark.asyncio
async def test_person_search_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        results = await c.person_search(
            _unique("Engineering Manager"), company="Stripe", limit=3
        )
        assert len(results) == 3
        assert c.credits_used == pytest.approx(
            3 * CREDIT_COSTS["person_search"]
        )
        for contact in results:
            assert contact["name"]
            assert contact["company"] == "Stripe"
            assert "linkedin_url" in contact
            assert contact["has_business_email"] is True
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_cache_hit_does_not_double_charge():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        query = _unique("Data Engineer")
        await c.person_search(query, limit=2)
        after_first = c.credits_used
        assert after_first > 0, (
            "first call must charge (cache was empty for unique query)"
        )
        await c.person_search(query, limit=2)
        after_second = c.credits_used
        assert after_second == after_first, (
            "second identical search must hit cache and charge 0"
        )
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_budget_enforcement_raises_before_spending():
    c = CrustdataClient(dry_run=True, credit_budget=1.5)
    try:
        await c.person_search(_unique("Manager"), limit=2)
        assert c.credits_used == pytest.approx(
            2 * CREDIT_COSTS["person_search"]
        )
        with pytest.raises(CreditBudgetExceeded):
            # Enrich costs 2.0, would exceed remaining 1.5 - 0.06
            await c.person_enrich(
                f"https://linkedin.com/in/test-{uuid.uuid4().hex[:8]}"
            )
        # Refused call must not have charged
        assert c.credits_used == pytest.approx(
            2 * CREDIT_COSTS["person_search"]
        )
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_person_enrich_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        url = f"https://linkedin.com/in/test-{uuid.uuid4().hex[:8]}"
        result = await c.person_enrich(url)
        assert result["email"].endswith("@example.com")  # reserved domain: never a real person
        assert result["linkedin_url"] == url
        assert c.credits_used == pytest.approx(CREDIT_COSTS["person_enrich"])
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_job_search_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        jobs = await c.job_search(_unique("ML internship"), limit=4)
        assert len(jobs) == 4
        assert c.credits_used == pytest.approx(
            4 * CREDIT_COSTS["job_search"]
        )
    finally:
        await c.close()


def test_dry_run_and_live_cache_keys_never_collide():
    args = {"title": "Recruiter", "company": "Acme", "location": None, "limit": 3}
    dry = CrustdataClient(dry_run=True)._cache_key("person_search", args)
    live = CrustdataClient(dry_run=False)._cache_key("person_search", args)
    assert dry != live


@pytest.mark.asyncio
async def test_dry_run_enrich_returns_same_person_as_search():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        people = await c.person_search(_unique("Recruiter"), company="Pinterest", limit=1)
        profile = await c.person_enrich(people[0]["linkedin_url"])
        assert profile["name"] == people[0]["name"]
        assert profile["company"] == "Pinterest"
        assert profile["email"].endswith("@example.com")
    finally:
        await c.close()
