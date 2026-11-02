"""AI recommendations endpoint - keyword-based scoring until embeddings are added."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.opportunity import OpportunityRead

router = APIRouter(prefix="/ai", tags=["ai"])

TECH_KEYWORDS = [
    "python", "fastapi", "django", "backend", "api", "sql", "postgresql",
    "docker", "aws", "cloud", "data", "machine learning", "ai", "software",
    "engineer", "developer", "intern", "fellowship", "open source", "remote",
    "startup", "typescript", "javascript", "react", "node", "devops",
]


@router.get("/recommendations", response_model=list[OpportunityRead])
async def get_recommendations(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Opportunity]:
    """Return top opportunities scored by relevance to a student tech profile.
    Uses keyword frequency scoring until embeddings are integrated in Phase 11."""
    result = await db.execute(select(Opportunity).where(Opportunity.is_active == True))
    all_opps = result.scalars().all()

    def score(opp: Opportunity) -> int:
        text = " ".join(filter(None, [opp.title, opp.organization, opp.description, opp.tags])).lower()
        base = sum(1 for kw in TECH_KEYWORDS if kw in text)
        bonus = 3 if opp.stipend else 0
        bonus += 2 if opp.is_remote else 0
        bonus += 3 if opp.tags and "intern" in opp.tags.lower() else 0
        bonus += 2 if opp.source == "curated" else 0
        return base + bonus

    scored = sorted(all_opps, key=score, reverse=True)
    return scored[:limit]
