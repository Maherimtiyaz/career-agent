"""Agent tool implementations and OpenAI function-calling schemas.

Every tool:
  - Receives a ToolContext (db session, user, run id, clients).
  - Returns a ToolResult (from schemas.py) — never raises to the orchestrator.
  - Has a matching entry in TOOL_SCHEMAS so the LLM planner can select it.

The `request_approval` tool does NOT block. It returns ok=True with an
`approval_request` payload; the orchestrator sees this and pauses the run.
That separation keeps the tool layer stateless and testable.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.crustdata import CrustdataClient, CrustdataError
from app.agents.llm_client import LLMProviderError, chat
from app.agents.schemas import (
    ApprovalRequest,
    ToolName,
    ToolResult,
)
from app.models.opportunity import Opportunity
from app.models.outreach_lead import OutreachLead, OutreachStatus
from app.models.user import User


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

@dataclass
class ToolContext:
    """Mutable bag of per-run state. Created once per orchestrator run."""
    session: AsyncSession
    user: User
    run_id: UUID
    dry_run: bool = True
    crustdata: CrustdataClient | None = None
    credits_used: float = 0.0
    collected_leads: list[dict[str, Any]] = field(default_factory=list)
    pending_approval: ApprovalRequest | None = None


# ---------------------------------------------------------------------------
# OpenAI function-calling schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": ToolName.DB_SEARCH_OPPORTUNITIES.value,
            "description": (
                "Search the user's tracked opportunities database by keyword "
                "(matches title, organization, description, tags). Use this "
                "FIRST before calling Crustdata — it's free and fast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.CRUSTDATA_PERSON_SEARCH.value,
            "description": (
                "Find contacts (hiring managers, recruiters, engineers) at a "
                "specific company. Use this after DB search to identify a "
                "human to email. Costs ~0.03 credits per result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Job title to search for, e.g. 'Engineering Manager'"},
                    "company": {"type": "string", "description": "Target company name"},
                    "location": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.CRUSTDATA_PERSON_ENRICH.value,
            "description": (
                "Get full profile (email, headline) for ONE contact found via "
                "person_search. Only call this for contacts you intend to email. "
                "Costs ~2.0 credits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "linkedin_url": {"type": "string"},
                },
                "required": ["linkedin_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.DRAFT_EMAIL.value,
            "description": (
                "Write a personalized cold email to a contact about a specific "
                "opportunity. Returns subject + body. Does NOT send anything."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "contact_title": {"type": "string"},
                    "contact_email": {"type": "string"},
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "context": {"type": "string", "description": "Why this person/role was chosen"},
                },
                "required": ["contact_email", "company", "role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.REQUEST_APPROVAL.value,
            "description": (
                "ALWAYS call this before sending any email. Pauses the run and "
                "asks the user to approve the draft. The user sees the exact "
                "recipient and body."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_email": {"type": "string"},
                    "recipient_name": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["recipient_email", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.SEND_EMAIL.value,
            "description": (
                "Send the email. Only call this AFTER request_approval returned "
                "ok and the user approved. In dry-run mode, this is a no-op."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_email": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["recipient_email", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.SAVE_LEAD.value,
            "description": (
                "Persist a lead (contact + drafted email) so it appears in the "
                "outreach_leads table. Use this after draft_email succeeds, "
                "before request_approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "contact_title": {"type": "string"},
                    "contact_email": {"type": "string"},
                    "contact_linkedin": {"type": "string"},
                    "opportunity_id": {"type": "string"},
                    "email_subject": {"type": "string"},
                    "email_draft": {"type": "string"},
                },
                "required": ["contact_email"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _db_search_opportunities(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return ToolResult(
            tool=ToolName.DB_SEARCH_OPPORTUNITIES,
            ok=False,
            error="query is required",
        )
    limit = min(int(args.get("limit", 5)), 20)
    pattern = f"%{query}%"
    stmt = (
        select(Opportunity)
        .where(
            Opportunity.is_active.is_(True),
            or_(
                Opportunity.title.ilike(pattern),
                Opportunity.organization.ilike(pattern),
                Opportunity.description.ilike(pattern),
                Opportunity.tags.ilike(pattern),
            ),
        )
        .limit(limit)
    )
    rows = (await ctx.session.execute(stmt)).scalars().all()
    return ToolResult(
        tool=ToolName.DB_SEARCH_OPPORTUNITIES,
        ok=True,
        data=[
            {
                "id": str(o.id),
                "title": o.title,
                "company": o.organization,
                "url": o.url,
                "location": o.location,
                "is_remote": o.is_remote,
                "source": o.source,
            }
            for o in rows
        ],
    )


async def _crustdata_person_search(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult:
    if ctx.crustdata is None:
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_SEARCH,
            ok=False,
            error="Crustdata client not initialized for this run",
        )
    before = ctx.crustdata.credits_used
    try:
        contacts = await ctx.crustdata.person_search(
            title=args["title"],
            company=args.get("company"),
            location=args.get("location"),
            limit=int(args.get("limit", 3)),
        )
        spent = ctx.crustdata.credits_used - before
        ctx.credits_used += spent
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_SEARCH,
            ok=True,
            data=contacts,
            credits_spent=spent,
        )
    except CrustdataError as exc:
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_SEARCH, ok=False, error=str(exc)
        )


async def _crustdata_person_enrich(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult:
    if ctx.crustdata is None:
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_ENRICH,
            ok=False,
            error="Crustdata client not initialized",
        )
    before = ctx.crustdata.credits_used
    try:
        profile = await ctx.crustdata.person_enrich(args["linkedin_url"])
        spent = ctx.crustdata.credits_used - before
        ctx.credits_used += spent
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_ENRICH,
            ok=True,
            data=profile,
            credits_spent=spent,
        )
    except CrustdataError as exc:
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_ENRICH, ok=False, error=str(exc)
        )


async def _draft_email(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    user = ctx.user
    skills = getattr(user, "skills", None) or "software development"
    target_roles = getattr(user, "target_roles", None) or "internship"
    bio = getattr(user, "bio", None) or ""
    college = getattr(user, "college", None) or "university"
    grad_year = getattr(user, "graduation_year", None) or ""
    name = user.full_name or user.email.split("@")[0]
    github = getattr(user, "github_url", None) or ""
    linkedin = getattr(user, "linkedin_url", None) or ""

    links = []
    if github:
        links.append(f"GitHub: {github}")
    if linkedin:
        links.append(f"LinkedIn: {linkedin}")
    links_str = " | ".join(links)

    prompt = f"""Write a professional, concise cold email.

APPLICANT:
- Name: {name}
- College: {college}{f' ({grad_year})' if grad_year else ''}
- Skills: {skills}
- Target roles: {target_roles}
- Bio: {bio}
{f'- Links: {links_str}' if links_str else ''}

RECIPIENT:
- Name: {args.get('contact_name', 'there')}
- Title: {args.get('contact_title', 'unknown')}
- Company: {args['company']}

OPPORTUNITY: {args['role']}
CONTEXT: {args.get('context', 'No additional context')}

Rules:
- Under 150 words
- Sound human, no generic phrases ("I hope this email finds you well")
- Mention ONE specific thing about the company or role
- Clear ask: 15-minute call or application review
- Sign off with the applicant name

Output format — EXACTLY:
SUBJECT: <subject line>
<body, no prefix>"""

    try:
        response = await chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
    except LLMProviderError as exc:
        return ToolResult(
            tool=ToolName.DRAFT_EMAIL,
            ok=False,
            error=f"Draft generation failed: {exc}",
        )

    text = (response.content or "").strip()
    subject = f"Re: {args['role']} at {args['company']}"
    body = text
    for i, line in enumerate(text.splitlines()):
        if line.upper().startswith("SUBJECT:"):
            subject = line.split(":", 1)[1].strip()
            body = "\n".join(text.splitlines()[i + 1:]).strip()
            break

    return ToolResult(
        tool=ToolName.DRAFT_EMAIL,
        ok=True,
        data={
            "subject": subject,
            "body": body,
            "recipient_email": args["contact_email"],
            "recipient_name": args.get("contact_name"),
            "provider": response.provider,
            "model": response.model,
        },
    )


async def _request_approval(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    approval = ApprovalRequest(
        run_id=ctx.run_id,
        step_index=int(args.get("_step_index", 0)),
        recipient_email=args["recipient_email"],
        recipient_name=args.get("recipient_name"),
        subject=args["subject"],
        body=args["body"],
    )
    ctx.pending_approval = approval
    return ToolResult(
        tool=ToolName.REQUEST_APPROVAL,
        ok=True,
        data={"approval_request": approval.model_dump(mode="json")},
    )


async def _send_email(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    if ctx.dry_run:
        # Advance the corresponding lead to 'sent' so the UI reflects reality.
        # In dry-run, we simulate the email but still mark the DB truthfully.
        from datetime import datetime, timezone
        from sqlalchemy import update as sa_update

        stmt = (
            sa_update(OutreachLead)
            .where(
                OutreachLead.run_id == ctx.run_id,
                OutreachLead.contact_email == args["recipient_email"],
                OutreachLead.status == OutreachStatus.PENDING_APPROVAL.value,
            )
            .values(
                status=OutreachStatus.SENT.value,
                sent_at=datetime.now(timezone.utc),
            )
        )
        await ctx.session.execute(stmt)
        await ctx.session.commit()

        return ToolResult(
            tool=ToolName.SEND_EMAIL,
            ok=True,
            data={
                "sent": True,
                "dry_run": True,
                "recipient": args["recipient_email"],
                "note": "Simulated — Gmail integration runs only in live mode; "
                        "lead status advanced to 'sent'",
            },
        )
    return ToolResult(
        tool=ToolName.SEND_EMAIL,
        ok=False,
        error="Live email sending not configured (Gmail OAuth not yet wired)",
    )


async def _save_lead(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    lead = OutreachLead(
        user_id=ctx.user.id,
        run_id=ctx.run_id,
        contact_name=args.get("contact_name"),
        contact_title=args.get("contact_title"),
        contact_email=args.get("contact_email"),
        contact_linkedin=args.get("contact_linkedin"),
        contact_source=args.get("contact_source", "agent"),
        status=OutreachStatus.PENDING_APPROVAL.value,
        email_subject=args.get("email_subject"),
        email_draft=args.get("email_draft"),
        credit_cost=ctx.credits_used,
    )
    if args.get("opportunity_id"):
        try:
            lead.opportunity_id = UUID(args["opportunity_id"])
        except (ValueError, TypeError):
            pass
    ctx.session.add(lead)
    await ctx.session.commit()
    ctx.collected_leads.append({"id": str(lead.id), **args})
    return ToolResult(
        tool=ToolName.SAVE_LEAD,
        ok=True,
        data={"lead_id": str(lead.id)},
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_DISPATCH = {
    ToolName.DB_SEARCH_OPPORTUNITIES: _db_search_opportunities,
    ToolName.CRUSTDATA_PERSON_SEARCH: _crustdata_person_search,
    ToolName.CRUSTDATA_PERSON_ENRICH: _crustdata_person_enrich,
    ToolName.DRAFT_EMAIL: _draft_email,
    ToolName.REQUEST_APPROVAL: _request_approval,
    ToolName.SEND_EMAIL: _send_email,
    ToolName.SAVE_LEAD: _save_lead,
}


async def execute_tool(
    name: str | ToolName, args: dict[str, Any], ctx: ToolContext
) -> ToolResult:
    """Execute a tool by name. Never raises — always returns a ToolResult.

    Accepts a raw string (what an LLM might hallucinate) and normalizes
    to ToolName. Invalid names produce an ok=False result rather than a
    validation error, so callers can log the bad input verbatim.
    """
    try:
        tool_name = name if isinstance(name, ToolName) else ToolName(name)
    except (ValueError, TypeError):
        return ToolResult(
            tool=str(name),
            ok=False,
            error=f"Unknown tool: {name!r}",
        )

    handler = _DISPATCH.get(tool_name)
    if handler is None:
        # Enum value exists but no handler registered — a code bug we must surface
        return ToolResult(
            tool=tool_name.value,
            ok=False,
            error=f"Tool not registered in dispatch table: {tool_name.value}",
        )

    start = time.monotonic()
    try:
        result = await handler(args, ctx)
    except Exception as exc:
        logger.exception("tool_crashed", extra={"tool": tool_name.value})
        result = ToolResult(
            tool=tool_name.value, ok=False, error=f"Tool crashed: {exc}"
        )
    result.duration_ms = int((time.monotonic() - start) * 1000)
    return result


def tool_schemas_for_llm() -> list[dict[str, Any]]:
    """Return tool schemas in the format llm_client.chat() expects."""
    return TOOL_SCHEMAS
