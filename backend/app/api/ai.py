"""Semantic AI recommendations personalized to the current user's profile."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.services.recommendations import RecommendationModelUnavailable, rank_opportunities
from app.schemas.opportunity import OpportunityRead

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/recommendations", response_model=list[OpportunityRead])
async def get_recommendations(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Opportunity]:
    """Return opportunities ranked by local semantic similarity to the user's profile."""
    result = await db.execute(select(Opportunity).where(Opportunity.is_active == True))
    opportunities = list(result.scalars().all())
    if not opportunities:
        return []

    try:
        return await rank_opportunities(current_user, opportunities, limit)
    except RecommendationModelUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The local recommendation model could not be loaded. "
                "Check backend access to Hugging Face and retry."
            ),
        ) from error
