"""Offline end-to-end tests for the agent loop and the human-approval gate.

The LLM is replaced by a scripted fake and the DB by an in-memory stub, so the
full journey (search -> draft -> approval -> send) runs deterministically with
no network, no Postgres, and no API keys.
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents import orchestrator as orch_mod
from app.agents import tools as tools_mod
from app.agents.llm_client import LLMResponse
from app.agents.orchestrator import Orchestrator
from app.agents.schemas import AgentGoal, AgentStatus, ApprovalDecision, StepStatus


OPP_ID = uuid4()


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self):
        self.opportunities = [
            SimpleNamespace(
                id=OPP_ID, title="Machine Learning Intern", organization="Acme AI",
                description="Train models", tags="Internship,email:jobs@acme.ai",
                url="https://acme.ai/jobs/1", location="Remote", is_remote=True, source="test",
            ),
            SimpleNamespace(
                id=uuid4(), title="Sales Lead", organization="Other Co",
                description=None, tags="Senior", url="https://x.co", location=None,
                is_remote=False, source="test",
            ),
        ]
        self.added = []
        self.updates = []

    async def execute(self, stmt):
        if stmt.__class__.__name__ == "Update":
            self.updates.append(stmt.compile().params)
            return _Result([])
        return _Result(self.opportunities)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def rollback(self):
        pass


def _user():
    return SimpleNamespace(
        id=uuid4(), email="demo@example.com", full_name="Demo Student",
        skills="Python, PyTorch", target_roles="ML internship", bio="Builds ML side projects",
        college="State University", graduation_year="2027", github_url="", linkedin_url="",
    )


def _call(name, args, content=None):
    import json

    return LLMResponse(
        content=content,
        tool_calls=[{
            "id": f"call_{uuid4().hex[:6]}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }],
        model="fake", provider="fake",
    )


def _install_fake_llm(monkeypatch, script):
    script = list(script)

    async def fake_chat(messages, tools=None, **kwargs):
        if tools is None:  # draft_email's writing call
            return LLMResponse(
                content="SUBJECT: ML intern question\nHi team,\nI build PyTorch models...\nDemo",
                model="fake", provider="fake",
            )
        if not script:
            return LLMResponse(content="done", model="fake", provider="fake")
        return script.pop(0)

    monkeypatch.setattr(orch_mod, "chat", fake_chat)
    monkeypatch.setattr(tools_mod, "chat", fake_chat)


HAPPY_SCRIPT = [
    lambda: _call("db_search_opportunities", {"query": "ML internship"}, "Searching saved roles first; it's free."),
    # The model tries to send on its own — must be refused, never executed.
    lambda: _call("send_email", {"recipient_email": "x@evil.com", "subject": "s", "body": "b"}),
    # The model invents an address — must be refused.
    lambda: _call("draft_email", {"contact_email": "invented@acme.ai", "company": "Acme AI", "role": "ML Intern"}),
    lambda: _call(
        "draft_email",
        {"contact_email": "jobs@acme.ai", "company": "Acme AI", "role": "Machine Learning Intern",
         "opportunity_id": str(OPP_ID)},
        "Using the application email listed on the posting.",
    ),
    lambda: _call("request_approval", {}, "Draft ready for the user's review."),
]


async def _run_to_approval(monkeypatch):
    _install_fake_llm(monkeypatch, [f() for f in HAPPY_SCRIPT])
    db = FakeSession()
    goal = AgentGoal(prompt="Find an ML internship and draft outreach", max_steps=10, dry_run=True)
    run = await Orchestrator.run_goal(goal, _user(), db)
    return run, db


@pytest.mark.asyncio
async def test_full_journey_pauses_then_sends_only_approved_text(monkeypatch):
    run, db = await _run_to_approval(monkeypatch)

    assert run.status == AgentStatus.AWAITING_APPROVAL, run.error
    tools = [s.call.tool for s in run.plan]
    assert tools[0] == "db_search_opportunities"
    # Hallucinated send was recorded as refused, not executed.
    send_attempt = run.plan[1]
    assert send_attempt.status == StepStatus.FAILED
    assert "not available" in send_attempt.result.error
    # Invented address refused.
    assert run.plan[2].status == StepStatus.FAILED
    # Rationale captured for the trace.
    assert run.plan[0].call.rationale.startswith("Searching")
    # Lead persisted at approval time with attribution.
    assert len(db.added) == 1
    lead = db.added[0]
    assert lead.contact_email == "jobs@acme.ai"
    assert lead.contact_source == "job_posting"
    assert lead.opportunity_id == OPP_ID

    approval = Orchestrator._STATES[run.id].context.pending_approval
    assert approval.opportunity_url == "https://acme.ai/jobs/1"

    decision = ApprovalDecision(
        run_id=run.id, step_index=0, approved=True,
        edited_subject="Edited subject", edited_body="Edited body by the human",
    )
    run = await Orchestrator.approve(run.id, decision, db=db)

    assert run.status == AgentStatus.COMPLETED, run.error
    send = run.plan[-1]
    assert send.call.tool == "send_email"
    assert send.call.args == {
        "recipient_email": "jobs@acme.ai",
        "subject": "Edited subject",
        "body": "Edited body by the human",
    }
    # Only one send ever executed successfully.
    assert sum(1 for s in run.plan if s.call.tool == "send_email" and s.status == StepStatus.OK) == 1


@pytest.mark.asyncio
async def test_second_approve_cannot_send_twice(monkeypatch):
    run, db = await _run_to_approval(monkeypatch)
    decision = ApprovalDecision(run_id=run.id, step_index=0, approved=True)
    await Orchestrator.approve(run.id, decision, db=db)
    with pytest.raises(ValueError):
        await Orchestrator.approve(run.id, decision, db=db)


@pytest.mark.asyncio
async def test_reject_sends_nothing(monkeypatch):
    run, db = await _run_to_approval(monkeypatch)
    decision = ApprovalDecision(run_id=run.id, step_index=0, approved=False)
    run = await Orchestrator.approve(run.id, decision, db=db)
    assert run.status == AgentStatus.CANCELLED
    assert not any(s.call.tool == "send_email" and s.status == StepStatus.OK for s in run.plan)
    assert db.updates and db.updates[-1]["status"] == "skipped"


@pytest.mark.asyncio
async def test_live_mode_reports_delivery_failure_honestly(monkeypatch):
    _install_fake_llm(monkeypatch, [f() for f in HAPPY_SCRIPT])
    db = FakeSession()
    goal = AgentGoal(prompt="Find an ML internship", max_steps=10, dry_run=False)
    run = await Orchestrator.run_goal(goal, _user(), db)
    decision = ApprovalDecision(run_id=run.id, step_index=0, approved=True)
    run = await Orchestrator.approve(run.id, decision, db=db)
    assert run.status == AgentStatus.FAILED
    assert "not configured" in run.error.lower()
    assert db.updates[-1]["status"] == "failed"


@pytest.mark.asyncio
async def test_agent_stopping_without_draft_is_a_failure(monkeypatch):
    _install_fake_llm(monkeypatch, [LLMResponse(content="I give up", model="f", provider="f")])
    run = await Orchestrator.run_goal(AgentGoal(prompt="Find anything at all"), _user(), FakeSession())
    assert run.status == AgentStatus.FAILED
