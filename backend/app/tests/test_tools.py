"""Unit tests for the agent tool layer.

Covers dispatch, approval flow, dry-run behavior, and error guards.
DB-touching and LLM-touching paths are exercised end-to-end in the
orchestrator integration test (T7b) where a real session and provider
are available.
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.schemas import ContactSource, ToolName
from app.agents.tools import (
    LLM_CALLABLE_TOOLS,
    TOOL_SCHEMAS,
    _application_email,
    _score_opportunity,
    _search_terms,
    ToolContext,
    execute_tool,
    tool_schemas_for_llm,
)


def _ctx(dry_run: bool = True) -> ToolContext:
    """Build a ToolContext with a fake user and no DB session."""
    return ToolContext(
        session=None,  # type: ignore[arg-type]
        user=SimpleNamespace(  # type: ignore[arg-type]
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            skills="Python, FastAPI",
            target_roles="Backend Engineer",
            bio="",
            college="",
            graduation_year="",
            github_url="",
            linkedin_url="",
        ),
        run_id=uuid4(),
        dry_run=dry_run,
    )


def test_tool_schemas_are_unique_and_complete():
    names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert len(names) == len(set(names)), "duplicate tool name in schemas"
    # Every tool except send_email is offered to the LLM.
    assert set(names) == {t.value for t in ToolName} - {ToolName.SEND_EMAIL.value}


def test_send_email_is_never_offered_to_llm():
    assert ToolName.SEND_EMAIL.value not in LLM_CALLABLE_TOOLS


def test_tool_schemas_for_llm_returns_same_list():
    assert tool_schemas_for_llm() is TOOL_SCHEMAS


@pytest.mark.asyncio
async def test_request_approval_requires_a_draft():
    ctx = _ctx()
    result = await execute_tool(ToolName.REQUEST_APPROVAL, {}, ctx)
    assert result.ok is False
    assert ctx.pending_approval is None


@pytest.mark.asyncio
async def test_request_approval_uses_exact_draft():
    ctx = _ctx()
    ctx.last_draft = {
        "recipient_email": "hiring@company.com",
        "recipient_name": "Hiring Manager",
        "contact_title": "EM",
        "contact_linkedin": None,
        "contact_source": ContactSource.JOB_POSTING,
        "company": "Acme",
        "role": "ML Intern",
        "opportunity_id": None,
        "opportunity_url": None,
        "subject": "Quick question",
        "body": "Hello...",
    }
    result = await execute_tool(ToolName.REQUEST_APPROVAL, {"_step_index": 3}, ctx)
    assert result.ok is True
    req = result.data["approval_request"]
    assert req["step_index"] == 3
    assert req["recipient_email"] == "hiring@company.com"
    assert req["body"] == "Hello..."
    assert req["contact_source"] == "job_posting"
    assert ctx.pending_approval is not None


@pytest.mark.asyncio
async def test_draft_email_refuses_unknown_recipient():
    """An address no tool returned (hallucinated) is refused before any LLM call."""
    ctx = _ctx()
    result = await execute_tool(
        ToolName.DRAFT_EMAIL,
        {"contact_email": "made.up@nowhere.com", "company": "Acme", "role": "Intern"},
        ctx,
    )
    assert result.ok is False
    assert "not returned by any tool" in (result.error or "")


def test_search_terms_tokenizes_and_expands():
    terms = _search_terms("Find an ML internship")
    assert "ml" in terms and "machine learning" in terms and "internship" in terms
    assert "find" not in terms and "an" not in terms


def test_score_prefers_title_and_whole_words():
    terms = _search_terms("ml intern")
    assert _score_opportunity(terms, "Machine Learning Intern", "") > _score_opportunity(
        terms, "Frontend Engineer", "Acme, internship program"
    )
    # 'ml' must not match inside 'html'
    assert _score_opportunity(["ml"], "HTML Developer", "") == 0


def test_application_email_parsed_from_tags():
    assert _application_email("Internship,email:jobs@acme.io") == "jobs@acme.io"
    assert _application_email("Internship") is None


@pytest.mark.asyncio
async def test_send_email_dry_run_returns_ok():
    ctx = _ctx(dry_run=True)
    result = await execute_tool(
        ToolName.SEND_EMAIL,
        {
            "recipient_email": "hiring@company.com",
            "subject": "Hi",
            "body": "Body text",
        },
        ctx,
    )
    assert result.ok is True
    assert result.data is not None
    assert result.data["dry_run"] is True
    assert result.data["recipient"] == "hiring@company.com"


@pytest.mark.asyncio
async def test_send_email_live_mode_refuses():
    ctx = _ctx(dry_run=False)
    result = await execute_tool(
        ToolName.SEND_EMAIL,
        {
            "recipient_email": "hiring@company.com",
            "subject": "Hi",
            "body": "Body text",
        },
        ctx,
    )
    assert result.ok is False
    assert "not configured" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    ctx = _ctx()
    result = await execute_tool("not_a_real_tool", {}, ctx)  # type: ignore[arg-type]
    assert result.ok is False
    assert "unknown tool" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_db_search_guard_against_empty_query():
    ctx = _ctx()
    result = await execute_tool(
        ToolName.DB_SEARCH_OPPORTUNITIES,
        {"query": "   "},
        ctx,
    )
    assert result.ok is False
    assert "required" in (result.error or "").lower()
