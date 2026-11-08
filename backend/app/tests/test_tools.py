"""Unit tests for the agent tool layer.

Covers dispatch, approval flow, dry-run behavior, and error guards.
DB-touching and LLM-touching paths are exercised end-to-end in the
orchestrator integration test (T7b) where a real session and provider
are available.
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.schemas import ToolName
from app.agents.tools import (
    TOOL_SCHEMAS,
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
    assert len(names) == 7, f"expected 7 tools, got {len(names)}"
    assert set(names) == {t.value for t in ToolName}


def test_tool_schemas_for_llm_returns_same_list():
    assert tool_schemas_for_llm() is TOOL_SCHEMAS


@pytest.mark.asyncio
async def test_request_approval_sets_pending():
    ctx = _ctx()
    result = await execute_tool(
        ToolName.REQUEST_APPROVAL,
        {
            "recipient_email": "hiring@company.com",
            "recipient_name": "Hiring Manager",
            "subject": "Quick question",
            "body": "Hello...",
            "_step_index": 3,
        },
        ctx,
    )
    assert result.ok is True
    assert result.data is not None
    assert "approval_request" in result.data
    assert result.data["approval_request"]["step_index"] == 3
    assert result.data["approval_request"]["recipient_email"] == "hiring@company.com"
    assert ctx.pending_approval is not None
    assert ctx.pending_approval.recipient_email == "hiring@company.com"


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
