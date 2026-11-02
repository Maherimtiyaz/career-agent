"""Analytics endpoints - application stats and opportunity breakdowns."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.application import Application
from app.models.opportunity import Opportunity
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Full analytics summary for the current user."""

    # Applications by status
    status_rows = (await db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    )).all()
    by_status = [{"status": r[0], "count": r[1]} for r in status_rows]

    # Total applications
    total_apps = sum(r["count"] for r in by_status)

    # Applications over time (by month)
    timeline_rows = (await db.execute(
        select(
            func.to_char(Application.created_at, "YYYY-MM").label("month"),
            func.count(Application.id).label("count")
        )
        .where(Application.user_id == current_user.id)
        .group_by("month")
        .order_by("month")
    )).all()
    timeline = [{"month": r[0], "count": r[1]} for r in timeline_rows]

    # Opportunities by source
    source_rows = (await db.execute(
        select(Opportunity.source, func.count(Opportunity.id))
        .group_by(Opportunity.source)
        .order_by(func.count(Opportunity.id).desc())
    )).all()
    by_source = [{"source": r[0], "count": r[1]} for r in source_rows]

    # Total opportunities
    total_opps = sum(r["count"] for r in by_source)

    # Remote vs on-site
    remote_rows = (await db.execute(
        select(Opportunity.is_remote, func.count(Opportunity.id))
        .group_by(Opportunity.is_remote)
    )).all()
    remote_split = [{"remote": r[0], "count": r[1]} for r in remote_rows]

    # Response rate (interviewing + offer / total applied)
    applied = next((r["count"] for r in by_status if r["status"] == "applied"), 0)
    interviewing = next((r["count"] for r in by_status if r["status"] == "interviewing"), 0)
    offers = next((r["count"] for r in by_status if r["status"] == "offer"), 0)
    response_rate = round((interviewing + offers) / total_apps * 100, 1) if total_apps > 0 else 0

    return {
        "total_applications": total_apps,
        "total_opportunities": total_opps,
        "response_rate": response_rate,
        "by_status": by_status,
        "timeline": timeline,
        "by_source": by_source,
        "remote_split": remote_split,
    }
