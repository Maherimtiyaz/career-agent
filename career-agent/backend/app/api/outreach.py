"""Email outreach - AI-generated cold emails for job applications."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def generate_email(user: User, app: Application) -> dict:
    """Call Anthropic API to generate a personalized cold email."""
    skills = getattr(user, "skills", "") or "software development"
    target_roles = getattr(user, "target_roles", "") or "internship"
    bio = getattr(user, "bio", "") or ""
    college = getattr(user, "college", "") or "university"
    grad_year = getattr(user, "graduation_year", "") or ""
    name = user.full_name or user.email.split("@")[0]
    github = getattr(user, "github_url", "") or ""
    linkedin = getattr(user, "linkedin_url", "") or ""

    links = []
    if github:
        links.append(f"GitHub: {github}")
    if linkedin:
        links.append(f"LinkedIn: {linkedin}")
    links_str = " | ".join(links) if links else ""

    prompt = f"""Write a professional, concise cold email from a student applying for a job/internship.

Applicant details:
- Name: {name}
- College: {college}{" (" + grad_year + ")" if grad_year else ""}
- Skills: {skills}
- Target roles: {target_roles}
- Bio: {bio}
{f"- Links: {links_str}" if links_str else ""}

Job details:
- Role: {app.role}
- Company: {app.company}
- Job link: {app.job_link or "not provided"}
- Notes: {app.notes or "none"}

Write a cold email with:
1. Subject line (prefix with SUBJECT:)
2. Email body starting on the next line

Rules:
- Keep it under 150 words
- Sound human, not like a template
- Mention one specific thing about the company or role
- End with a clear ask (15-minute call or to review application)
- Do not use generic phrases like "I hope this email finds you well"
- Sign off with the applicant name and links if available

Return ONLY the subject line prefixed with SUBJECT: and then the email body. Nothing else."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code != 200:
                raise ValueError(f"API error: {resp.status_code}")

            data = resp.json()
            text = data["content"][0]["text"].strip()

            lines = text.split("\n")
            subject = ""
            body_lines = []
            for i, line in enumerate(lines):
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                else:
                    body_lines.extend(lines[i:])
                    break

            body = "\n".join(body_lines).strip()
            if not subject:
                subject = f"Application for {app.role} at {app.company}"

            return {"subject": subject, "body": body}

    except Exception as e:
        subject = f"Application for {app.role} at {app.company}"
        body = f"""Hi,

I am {name}, a {college} student{" graduating in " + grad_year if grad_year else ""} with skills in {skills}.

I came across the {app.role} opportunity at {app.company} and I am very interested. My background in {skills.split(",")[0].strip() if skills else "software development"} aligns well with this role.

Would you have 15 minutes for a quick call to discuss further?

Best regards,
{name}
{links_str}"""
        return {"subject": subject, "body": body}


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
    )