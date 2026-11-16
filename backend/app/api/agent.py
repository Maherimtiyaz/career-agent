"""Agent REST API: start runs, inspect state, approve/reject, list leads.

All endpoints require auth. Runs live in Orchestrator._RUNS (in-memory dict) —
fine for a single-process hackathon demo. Persisting runs to the DB is a
post-hackathon concern; outreach_leads is already persistent, so the durable
artifacts of every run survive a restart.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import Orchestrator
from app.agents.schemas import (
    AgentGoal,
    AgentRun,
    AgentStatus,
    ApprovalDecision,
)
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.opportunity import Opportunity
from app.models.outreach_lead import OutreachLead
from app.models.user import User


router = APIRouter(prefix="/agent", tags=["agent"])


class StartRunRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=1000)
    max_steps: int = Field(default=10, ge=1, le=20)
    credit_budget: float = Field(default=50.0, ge=0.0, le=500.0)
    dry_run: bool = Field(default=True)


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    edited_subject: str | None = None
    edited_body: str | None = None
    reason: str | None = None


def _serialize_run(run: AgentRun) -> dict:
    """Run dict + the pending approval (only while the run is actually paused)."""
    payload = run.model_dump(mode="json", warnings=False)
    state = Orchestrator._STATES.get(run.id)
    approval = state.context.pending_approval if state else None
    payload["pending_approval"] = (
        approval.model_dump(mode="json")
        if approval is not None and run.status == AgentStatus.AWAITING_APPROVAL
        else None
    )
    # What was actually sent / proposed, for the final result card.
    payload["final_email"] = approval.model_dump(mode="json") if approval is not None else None
    return payload


def _find_approval_step_index(run: AgentRun) -> int | None:
    for step in reversed(run.plan):
        if step.result and step.result.ok and isinstance(step.result.data, dict):
            if "approval_request" in step.result.data:
                return step.index
    return None


@router.post("/run")
async def start_run(
    body: StartRunRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Start an agent run in the background. Poll GET /agent/run/{id} for the live trace."""
    goal = AgentGoal(
        prompt=body.prompt,
        max_steps=body.max_steps,
        credit_budget=body.credit_budget,
        dry_run=body.dry_run,
    )
    run = Orchestrator.start_in_background(goal, user.id)
    return _serialize_run(run)


@router.get("/run/{run_id}")
async def get_run(
    run_id: UUID,
    user: User = Depends(get_current_user),
) -> dict:
    run = Orchestrator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your run")
    return _serialize_run(run)


@router.post("/run/{run_id}/approve")
async def approve_run(
    run_id: UUID,
    body: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    run = Orchestrator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your run")
    if run.status != AgentStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Run is '{run.status.value}', not awaiting approval",
        )

    step_index = _find_approval_step_index(run)
    if step_index is None:
        raise HTTPException(status_code=500, detail="No pending approval in plan")

    decision = ApprovalDecision(
        run_id=run_id,
        step_index=step_index,
        approved=body.approved,
        edited_subject=body.edited_subject,
        edited_body=body.edited_body,
        reason=body.reason,
    )
    try:
        run = await Orchestrator.approve(run_id, decision, db=db)
    except ValueError as exc:  # lost a race with a concurrent decision
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_run(run)


@router.get("/leads")
async def list_leads(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    rows = (
        await db.execute(
            select(OutreachLead, Opportunity)
            .outerjoin(Opportunity, Opportunity.id == OutreachLead.opportunity_id)
            .where(OutreachLead.user_id == user.id)
            .order_by(OutreachLead.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        {
            "id": str(lead.id),
            "company": opp.organization if opp else None,
            "role": opp.title if opp else None,
            "opportunity_url": opp.url if opp else None,
            "contact_name": lead.contact_name,
            "contact_title": lead.contact_title,
            "contact_email": lead.contact_email,
            "contact_linkedin": lead.contact_linkedin,
            "contact_source": lead.contact_source,
            "status": lead.status,
            "error_message": lead.error_message,
            "email_subject": lead.email_subject,
            "email_draft": lead.email_draft,
            "credit_cost": lead.credit_cost,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "sent_at": lead.sent_at.isoformat() if lead.sent_at else None,
        }
        for lead, opp in rows
    ]
