"""CRUD operations for opportunities and applications."""

import uuid
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.models.application import Application
from app.schemas.opportunity import OpportunityCreate, ApplicationCreate, ApplicationUpdate


async def get_opportunities(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    source: Optional[str] = None,
    is_remote: Optional[bool] = None,
    search: Optional[str] = None,
) -> list[Opportunity]:
    query = select(Opportunity).where(Opportunity.is_active == True)
    if source:
        query = query.where(Opportunity.source == source)
    if is_remote is not None:
        query = query.where(Opportunity.is_remote == is_remote)
    if search:
        query = query.where(
            Opportunity.title.ilike(f"%{search}%") |
            Opportunity.organization.ilike(f"%{search}%")
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_opportunity_by_id(db: AsyncSession, opportunity_id: uuid.UUID) -> Optional[Opportunity]:
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    return result.scalar_one_or_none()


async def create_opportunity(db: AsyncSession, opp_in: OpportunityCreate) -> Opportunity:
    opp = Opportunity(**opp_in.model_dump())
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


async def get_applications(db: AsyncSession, user_id: uuid.UUID) -> list[Application]:
    result = await db.execute(
        select(Application).where(Application.user_id == user_id).order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


async def get_application_by_id(db: AsyncSession, application_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Application]:
    result = await db.execute(
        select(Application).where(
            and_(Application.id == application_id, Application.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def create_application(db: AsyncSession, app_in: ApplicationCreate, user_id: uuid.UUID) -> Application:
    app = Application(**app_in.model_dump(), user_id=user_id, source="manual")
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def update_application(db: AsyncSession, application: Application, update_in: ApplicationUpdate) -> Application:
    for field, value in update_in.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    await db.commit()
    await db.refresh(application)
    return application


async def delete_application(db: AsyncSession, application: Application) -> None:
    await db.delete(application)
    await db.commit()
