"""Email outreach - AI-generated cold emails for tracked applications."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_client import LLMProviderError, chat
from app.agents.tools import DRAFT_RULES, _parse_draft, applicant_profile_block
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.application import Application
from app.models.user import User

router = APIRouter(prefix="/outreach", tags=["outreach"])


class DraftRequest(BaseModel):
    application_id: str


class DraftResponse(BaseModel):
    subject: str
    body: str
    to: str | None
    generated: bool = True  # False = template fallback, no LLM reachable


async def generate_email(user: User, app: Application) -> dict:
    """Draft a cold email with the same LLM chain and prompt rules as the agent."""
    prompt = f"""Write a cold outreach email from a job seeker.

APPLICANT:
{applicant_profile_block(user)}

JOB:
- Role: {app.role}
- Company: {app.company}
- Job link: {app.job_link or "not provided"}
- Notes: {app.notes or "none"}

{DRAFT_RULES}"""
    fallback_subject = f"Application for {app.role} at {app.company}"
    try:
        response = await chat(
            messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=600
        )
        subject, body = _parse_draft(response.content or "", fallback_subject)
        if body:
            return {"subject": subject, "body": body, "generated": True}
    except LLMProviderError:
        pass

    # Clearly-labelled template fallback when no LLM provider is reachable.
    name = user.full_name or user.email.split("@")[0]
    skills = getattr(user, "skills", "") or "software development"
    body = (
        f"Hi,\n\nI'm {name}, and I'm interested in the {app.role} role at {app.company}. "
        f"My background in {skills.split(',')[0].strip()} lines up well with it.\n\n"
        f"Would you have 15 minutes for a quick call?\n\nBest regards,\n{name}"
    )
    return {"subject": fallback_subject, "body": body, "generated": False}


@router.post("/draft", response_model=DraftResponse)
async def draft_email(
    body: DraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftResponse:
    result = await db.execute(
        select(Application).where(
            Application.id == body.application_id,
            Application.user_id == current_user.id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    draft = await generate_email(current_user, app)

    return DraftResponse(
        subject=draft["subject"],
        body=draft["body"],
        to=app.hr_contact or None,
        generated=draft["generated"],
    )