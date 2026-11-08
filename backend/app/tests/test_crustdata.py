import pytest
from app.agents.crustdata import CrustdataClient, CreditBudgetExceeded, CREDIT_COSTS

@pytest.mark.asyncio
async def test_person_search_dry_run():
    c = CrustdataClient(dry_run=True, credit_budget=10.0)
    try:
        results = await c.person_search("Engineering Manager", company="Stripe", limit=3)
        assert len(results) == 3
        assert c.credits_used == pytest.approx(3 * CREDIT_COSTS["person_search"])
    finally:
        await c.close()

# + cache test, budget test, enrich test, job search test