"""Agent tool implementations and OpenAI function-calling schemas.

Every tool:
  - Receives a ToolContext (db session, user, run id, clients).
  - Returns a ToolResult (from schemas.py) — never raises to the orchestrator.

The LLM can only see TOOL_SCHEMAS (5 tools). `send_email` is deliberately NOT
exposed to the LLM: it is executed by the orchestrator, and only after a human
approves the draft. The model has no way to send anything on its own.

Contact provenance: every email address a tool returns is recorded in
`ctx.known_contacts` with its source. `draft_email` refuses any recipient that
no tool produced in this run — a hallucinated address can never reach the
approval screen.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.crustdata import CrustdataClient, CrustdataError
from app.agents.llm_client import LLMProviderError, chat
from app.agents.schemas import (
    ApprovalRequest,
    ContactSource,
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
    # email (lowercased) -> ContactSource, filled by tools that return emails
    known_contacts: dict[str, ContactSource] = field(default_factory=dict)
    # opportunity id -> url, so the approval card can link the posting
    seen_opportunities: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_draft: dict[str, Any] | None = None
    lead_id: UUID | None = None
    pending_approval: ApprovalRequest | None = None


# ---------------------------------------------------------------------------
# OpenAI function-calling schemas (what the LLM planner can choose from)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": ToolName.DB_SEARCH_OPPORTUNITIES.value,
            "description": (
                "Search the user's saved opportunities by keywords (matches "
                "title, company, description, tags; results ranked by relevance). "
                "Free. Results may include `application_email` taken from the "
                "job posting itself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords, e.g. 'machine learning intern'"},
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
                "Find people (hiring managers, recruiters, engineering leads) at "
                "a specific company. Returns names + LinkedIn URLs, no emails. "
                "~0.03 credits per result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Job title, e.g. 'Engineering Manager' or 'Recruiter'"},
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
                "Get the email and profile for ONE person found via "
                "crustdata_person_search. ~2 credits — only for the person you will email."
            ),
            "parameters": {
                "type": "object",
                "properties": {"linkedin_url": {"type": "string"}},
                "required": ["linkedin_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.DRAFT_EMAIL.value,
            "description": (
                "Write a personalized outreach email using the user's profile. "
                "contact_email MUST be an address returned by a previous tool "
                "(application_email or crustdata_person_enrich). Sends nothing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_email": {"type": "string"},
                    "contact_name": {"type": "string"},
                    "contact_title": {"type": "string"},
                    "contact_linkedin": {"type": "string"},
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "opportunity_id": {"type": "string", "description": "id from db_search_opportunities"},
                    "context": {"type": "string", "description": "Why this person and role fit the user"},
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
                "Save the lead and hand the latest draft to the user for review. "
                "Takes no arguments — the exact drafted email is shown. The run "
                "pauses here; only the user can send."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ---------------------------------------------------------------------------
# Opportunity search helpers
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "at", "of", "to", "with", "on",
    "find", "me", "my", "i", "saved", "any", "some", "one", "role", "roles",
    "job", "jobs", "position", "positions", "opportunity", "opportunities",
}
_EXPANSIONS = {
    "ml": ["machine learning"],
    "ai": ["artificial intelligence"],
    "intern": ["internship"],
    "internship": ["intern"],
    "swe": ["software engineer"],
}


def _search_terms(query: str) -> list[str]:
    """Split a free-text query into match terms (with a few synonyms)."""
    words = [w for w in re.findall(r"[a-z0-9+#.]+", query.lower()) if w not in _STOPWORDS]
    terms: list[str] = []
    for w in words:
        if (len(w) >= 2 or w in _EXPANSIONS) and w not in terms:
            terms.append(w)
        for extra in _EXPANSIONS.get(w, []):
            if extra not in terms:
                terms.append(extra)
    return terms


def _score_opportunity(terms: list[str], title: str, other: str) -> int:
    """Whole-word matches: 3 points in the title, 1 point elsewhere."""
    score = 0
    for term in terms:
        pat = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        if pat.search(title or ""):
            score += 3
        elif pat.search(other or ""):
            score += 1
    return score


def _application_email(tags: str | None) -> str | None:
    for part in (tags or "").split(","):
        part = part.strip()
        if part.lower().startswith("email:") and "@" in part:
            return part.split(":", 1)[1].strip()
    return None


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _db_search_opportunities(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = (args.get("query") or "").strip()
    terms = _search_terms(query)
    if not terms:
        return ToolResult(
            tool=ToolName.DB_SEARCH_OPPORTUNITIES, ok=False, error="query is required"
        )
    limit = max(1, min(int(args.get("limit", 5) or 5), 20))

    clauses = []
    for term in terms:
        p = f"%{term}%"
        clauses += [
            Opportunity.title.ilike(p),
            Opportunity.organization.ilike(p),
            Opportunity.description.ilike(p),
            Opportunity.tags.ilike(p),
        ]
    stmt = select(Opportunity).where(Opportunity.is_active.is_(True), or_(*clauses)).limit(400)
    rows = (await ctx.session.execute(stmt)).scalars().all()

    scored = []
    for o in rows:
        other = " ".join(filter(None, [o.organization, o.description, o.tags]))
        s = _score_opportunity(terms, o.title, other)
        if s > 0:
            scored.append((s, o))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = []
    for score, o in scored[:limit]:
        email = _application_email(o.tags)
        if email:
            ctx.known_contacts[email.lower()] = ContactSource.JOB_POSTING
        item = {
            "id": str(o.id),
            "title": o.title,
            "company": o.organization,
            "url": o.url,
            "location": o.location,
            "is_remote": o.is_remote,
            "source": o.source,
            "application_email": email,
            "relevance": score,
        }
        ctx.seen_opportunities[item["id"]] = item
        results.append(item)

    return ToolResult(tool=ToolName.DB_SEARCH_OPPORTUNITIES, ok=True, data=results)


def _crustdata_source(ctx: ToolContext) -> ContactSource:
    if ctx.crustdata is not None and ctx.crustdata.dry_run:
        return ContactSource.CRUSTDATA_SIMULATED
    return ContactSource.CRUSTDATA


async def _crustdata_person_search(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    if ctx.crustdata is None:
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_SEARCH, ok=False,
            error="Crustdata client not initialized for this run",
        )
    if not args.get("title"):
        return ToolResult(tool=ToolName.CRUSTDATA_PERSON_SEARCH, ok=False, error="title is required")
    before = ctx.crustdata.credits_used
    try:
        contacts = await ctx.crustdata.person_search(
            title=args["title"],
            company=args.get("company"),
            location=args.get("location"),
            limit=int(args.get("limit", 3) or 3),
        )
    except CrustdataError as exc:
        return ToolResult(tool=ToolName.CRUSTDATA_PERSON_SEARCH, ok=False, error=str(exc))
    spent = ctx.crustdata.credits_used - before
    ctx.credits_used += spent
    source = _crustdata_source(ctx).value
    return ToolResult(
        tool=ToolName.CRUSTDATA_PERSON_SEARCH,
        ok=True,
        data=[{**c, "source": source} for c in contacts],
        credits_spent=spent,
    )


async def _crustdata_person_enrich(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    if ctx.crustdata is None:
        return ToolResult(
            tool=ToolName.CRUSTDATA_PERSON_ENRICH, ok=False, error="Crustdata client not initialized"
        )
    if not args.get("linkedin_url"):
        return ToolResult(tool=ToolName.CRUSTDATA_PERSON_ENRICH, ok=False, error="linkedin_url is required")
    before = ctx.crustdata.credits_used
    try:
        profile = await ctx.crustdata.person_enrich(args["linkedin_url"])
    except CrustdataError as exc:
        return ToolResult(tool=ToolName.CRUSTDATA_PERSON_ENRICH, ok=False, error=str(exc))
    spent = ctx.crustdata.credits_used - before
    ctx.credits_used += spent
    source = _crustdata_source(ctx)
    if profile.get("email"):
        ctx.known_contacts[profile["email"].lower()] = source
    return ToolResult(
        tool=ToolName.CRUSTDATA_PERSON_ENRICH,
        ok=True,
        data={**profile, "source": source.value},
        credits_spent=spent,
    )


def _parse_draft(text: str, fallback_subject: str) -> tuple[str, str]:
    """Split 'SUBJECT: ...\\n<body>' model output into (subject, body)."""
    lines = (text or "").strip().splitlines()
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("SUBJECT:"):
            return line.split(":", 1)[1].strip() or fallback_subject, "\n".join(lines[i + 1:]).strip()
    return fallback_subject, "\n".join(lines).strip()


def applicant_profile_block(user: User) -> str:
    """Profile summary shared by every drafting prompt."""
    name = user.full_name or user.email.split("@")[0]
    college = getattr(user, "college", None) or ""
    grad = getattr(user, "graduation_year", None) or ""
    links = " | ".join(
        x for x in [
            f"GitHub: {user.github_url}" if getattr(user, "github_url", None) else "",
            f"LinkedIn: {user.linkedin_url}" if getattr(user, "linkedin_url", None) else "",
        ] if x
    )
    lines = [
        f"- Name: {name}",
        f"- Education: {college}{f' ({grad})' if grad else ''}" if college else "",
        f"- Skills: {getattr(user, 'skills', None) or 'software development'}",
        f"- Target roles: {getattr(user, 'target_roles', None) or 'internship'}",
        f"- Bio: {user.bio}" if getattr(user, "bio", None) else "",
        f"- Links: {links}" if links else "",
    ]
    return "\n".join(line for line in lines if line)


DRAFT_RULES = """Rules:
- Under 150 words
- Sound human; no generic openers like "I hope this email finds you well"
- Mention ONE specific, relevant thing about the company or role
- Connect ONE concrete skill of the applicant to the role
- Clear ask: a 15-minute call or a look at the application
- Sign off with the applicant's name (and links if provided)

Output format — EXACTLY:
SUBJECT: <subject line>
<body, no prefix>"""


async def _draft_email(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    email = (args.get("contact_email") or "").strip()
    company = (args.get("company") or "").strip()
    role = (args.get("role") or "").strip()
    if not (email and company and role):
        return ToolResult(
            tool=ToolName.DRAFT_EMAIL, ok=False, error="contact_email, company and role are required"
        )
    source = ctx.known_contacts.get(email.lower())
    if source is None:
        return ToolResult(
            tool=ToolName.DRAFT_EMAIL,
            ok=False,
            error=(
                f"Refused: {email} was not returned by any tool in this run. "
                "Use an application_email from db_search_opportunities or an "
                "email from crustdata_person_enrich. Never invent addresses."
            ),
        )

    prompt = f"""Write a cold outreach email from a job seeker.

APPLICANT:
{applicant_profile_block(ctx.user)}

RECIPIENT:
- Name: {args.get('contact_name') or 'unknown (address them by team, not "Dear Sir")'}
- Title: {args.get('contact_title') or 'unknown'}
- Company: {company}

OPPORTUNITY: {role}
CONTEXT: {args.get('context') or 'none'}

{DRAFT_RULES}"""

    try:
        response = await chat(
            messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=600
        )
    except LLMProviderError as exc:
        return ToolResult(tool=ToolName.DRAFT_EMAIL, ok=False, error=f"Draft generation failed: {exc}")

    subject, body = _parse_draft(response.content or "", f"{role} at {company}")
    if not body:
        return ToolResult(tool=ToolName.DRAFT_EMAIL, ok=False, error="Model returned an empty draft")

    opportunity = ctx.seen_opportunities.get(str(args.get("opportunity_id") or ""))
    ctx.last_draft = {
        "recipient_email": email,
        "recipient_name": args.get("contact_name"),
        "contact_title": args.get("contact_title"),
        "contact_linkedin": args.get("contact_linkedin"),
        "contact_source": source,
        "company": company,
        "role": role,
        "opportunity_id": opportunity["id"] if opportunity else None,
        "opportunity_url": opportunity["url"] if opportunity else None,
        "subject": subject,
        "body": body,
    }
    return ToolResult(
        tool=ToolName.DRAFT_EMAIL,
        ok=True,
        data={
            "subject": subject,
            "body": body,
            "recipient_email": email,
            "recipient_name": args.get("contact_name"),
            "contact_source": source.value,
            "model": f"{response.provider}/{response.model}",
        },
    )


async def _request_approval(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    draft = ctx.last_draft
    if draft is None:
        return ToolResult(
            tool=ToolName.REQUEST_APPROVAL, ok=False, error="No draft yet — call draft_email first"
        )

    lead_id: UUID | None = None
    if ctx.session is not None:
        lead = OutreachLead(
            id=uuid4(),
            user_id=ctx.user.id,
            run_id=ctx.run_id,
            contact_name=draft["recipient_name"],
            contact_title=draft["contact_title"],
            contact_email=draft["recipient_email"],
            contact_linkedin=draft["contact_linkedin"],
            contact_source=draft["contact_source"].value,
            status=OutreachStatus.PENDING_APPROVAL.value,
            email_subject=draft["subject"],
            email_draft=draft["body"],
            credit_cost=ctx.credits_used,
        )
        if draft["opportunity_id"]:
            lead.opportunity_id = UUID(draft["opportunity_id"])
        ctx.session.add(lead)
        await ctx.session.commit()
        lead_id = lead.id
    ctx.lead_id = lead_id

    approval = ApprovalRequest(
        run_id=ctx.run_id,
        step_index=int(args.get("_step_index", 0)),
        recipient_email=draft["recipient_email"],
        recipient_name=draft["recipient_name"],
        contact_title=draft["contact_title"],
        contact_source=draft["contact_source"],
        company=draft["company"],
        role=draft["role"],
        opportunity_url=draft["opportunity_url"],
        subject=draft["subject"],
        body=draft["body"],
        lead_id=lead_id,
    )
    ctx.pending_approval = approval
    return ToolResult(
        tool=ToolName.REQUEST_APPROVAL,
        ok=True,
        data={"approval_request": approval.model_dump(mode="json")},
    )


async def update_lead(ctx: ToolContext, **values: Any) -> None:
    """Best-effort update of this run's lead row. Never raises."""
    if ctx.session is None or ctx.lead_id is None:
        return
    try:
        await ctx.session.execute(
            sa_update(OutreachLead).where(OutreachLead.id == ctx.lead_id).values(**values)
        )
        await ctx.session.commit()
    except Exception as exc:
        logger.warning("lead_update_failed", extra={"run_id": str(ctx.run_id), "error": str(exc)})
        try:
            await ctx.session.rollback()
        except Exception:
            pass


async def _send_email(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Called by the orchestrator only, with the human-approved payload."""
    final = {"email_subject": args["subject"], "email_draft": args["body"]}
    if ctx.dry_run:
        await update_lead(
            ctx, status=OutreachStatus.SENT.value, sent_at=datetime.now(timezone.utc), **final
        )
        return ToolResult(
            tool=ToolName.SEND_EMAIL,
            ok=True,
            data={
                "sent": True,
                "dry_run": True,
                "recipient": args["recipient_email"],
                "note": "Demo mode: delivery simulated, nothing left your machine. Lead marked sent.",
            },
        )
    error = "Live email delivery is not configured (Gmail OAuth not wired). Nothing was sent."
    await update_lead(ctx, status=OutreachStatus.FAILED.value, error_message=error, **final)
    return ToolResult(tool=ToolName.SEND_EMAIL, ok=False, error=error)


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
}

LLM_CALLABLE_TOOLS = frozenset(s["function"]["name"] for s in TOOL_SCHEMAS)


async def execute_tool(name: str | ToolName, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute a tool by name. Never raises — always returns a ToolResult."""
    try:
        tool_name = name if isinstance(name, ToolName) else ToolName(name)
    except (ValueError, TypeError):
        return ToolResult(tool=str(name), ok=False, error=f"Unknown tool: {name!r}")

    handler = _DISPATCH.get(tool_name)
    if handler is None:
        return ToolResult(
            tool=tool_name.value, ok=False,
            error=f"Tool not registered in dispatch table: {tool_name.value}",
        )

    start = time.monotonic()
    try:
        result = await handler(args, ctx)
    except Exception as exc:
        logger.exception("tool_crashed", extra={"tool": tool_name.value})
        result = ToolResult(tool=tool_name.value, ok=False, error=f"Tool crashed: {exc}")
    result.duration_ms = int((time.monotonic() - start) * 1000)
    return result


def tool_schemas_for_llm() -> list[dict[str, Any]]:
    """Return tool schemas in the format llm_client.chat() expects."""
    return TOOL_SCHEMAS
