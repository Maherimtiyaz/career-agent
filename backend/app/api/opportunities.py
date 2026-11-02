"""Opportunities and applications endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.crud.opportunity import (
    create_application,
    create_opportunity,
    delete_application,
    get_application_by_id,
    get_applications,
    get_opportunities,
    get_opportunity_by_id,
    update_application,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.opportunity import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    OpportunityCreate,
    OpportunityRead,
)

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities", response_model=list[OpportunityRead])
async def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    source: Optional[str] = Query(None),
    is_remote: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_opportunities(db, skip=skip, limit=limit, source=source, is_remote=is_remote, search=search)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(opportunity_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    opp = await get_opportunity_by_id(db, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return opp


@router.post("/opportunities", response_model=OpportunityRead, status_code=status.HTTP_201_CREATED)
async def create_opp(
    opp_in: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_opportunity(db, opp_in)


@router.get("/applications", response_model=list[ApplicationRead])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_applications(db, current_user.id)


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_app(
    app_in: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_application(db, app_in, current_user.id)


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
async def update_app(
    application_id: uuid.UUID,
    update_in: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await get_application_by_id(db, application_id, current_user.id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return await update_application(db, app, update_in)


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await get_application_by_id(db, application_id, current_user.id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    await delete_application(db, app)
