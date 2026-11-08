"""Tests for the Crustdata adapter.

All tests use dry_run=True — no credits spent, no network calls.
Verifies: mock data shape, credit accounting, Redis cache dedup,
budget enforcement, and normalization contract (orchestrator sees
only the normalized dict/list shape).
"""
import pytest

from app.agents.crustdata import (
    CREDIT_COSTS,
    CreditBudgetExceeded,
    CrustdataClient,
)


@pytest.mark.asyncio
async def test_person_search_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        results = await c.person_search(
            "Engineering Manager", company="Stripe", limit=3
        )
        assert len(results) == 3
        assert c.credits_used == pytest.approx(
            3 * CREDIT_COSTS["person_search"]
        )
        for contact in results:
            assert contact["name"]
            assert contact["title"] == "Engineering Manager"
            assert contact["company"] == "Stripe"
            assert "linkedin_url" in contact
            assert contact["has_business_email"] is True
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_cache_hit_does_not_double_charge():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        await c.person_search("Data Engineer", limit=2)
        after_first = c.credits_used
        await c.person_search("Data Engineer", limit=2)
        after_second = c.credits_used
        assert after_first == after_second, (
            "second identical search must hit cache and charge 0"
        )
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_budget_enforcement_raises_before_spending():
    c = CrustdataClient(dry_run=True, credit_budget=1.5)
    try:
        # Cheap search succeeds (0.06 credits)
        await c.person_search("Manager", limit=2)
        # Enrich costs 2.0 credits — would exceed 1.5 budget
        with pytest.raises(CreditBudgetExceeded):
            await c.person_enrich("https://linkedin.com/in/x")
        # Budget must not have been spent on the refused call
        assert c.credits_used == pytest.approx(
            2 * CREDIT_COSTS["person_search"]
        )
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_person_enrich_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        result = await c.person_enrich("https://linkedin.com/in/test-person")
        assert result["email"] == "mock.contact@example.com"
        assert result["linkedin_url"] == "https://linkedin.com/in/test-person"
        assert result["title"] == "Engineering Manager"
        assert c.credits_used == pytest.approx(CREDIT_COSTS["person_enrich"])
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_job_search_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        jobs = await c.job_search("ML internship", limit=4)
        assert len(jobs) == 4
        assert c.credits_used == pytest.approx(
            4 * CREDIT_COSTS["job_search"]
        )
        for job in jobs:
            assert "ML internship" in job["title"]
            assert "url" in job
    finally:
        await c.close()
