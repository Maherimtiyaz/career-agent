"""Bounded ReAct orchestrator for the career outreach agent.

The loop:
  1. Send goal + tool schemas + observation history to the LLM.
  2. LLM returns the next tool call (or no tool call = done).
  3. Orchestrator executes it via tools.execute_tool() and records a trace step.
  4. Observation appended to messages. Loop until request_approval or max_steps.

Human-in-the-loop:
  - The LLM never sees a send tool. The run pauses at request_approval.
  - approve() sends the APPROVED payload directly — no LLM call after the
    human decision, so nothing the model does can alter or trigger a send.
  - Per-run asyncio.Lock + status re-check inside the lock: double-clicking
    Approve cannot send twice.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.crustdata import CrustdataClient
from app.agents.llm_client import LLMProviderError, chat
from app.agents.schemas import (
    AgentGoal,
    AgentRun,
    AgentStatus,
    AgentStep,
    ApprovalDecision,
    StepStatus,
    ToolCall,
    ToolName,
    ToolResult,
)
from app.agents.tools import (
    LLM_CALLABLE_TOOLS,
    TOOL_SCHEMAS,
    ToolContext,
    applicant_profile_block,
    execute_tool,
    update_lead,
)
from app.models.outreach_lead import OutreachStatus
from app.models.user import User


logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are a career outreach agent. Goal: find ONE relevant opportunity for the user, identify a real person to contact, and draft a personalized email for the user to approve.

## Tools
- db_search_opportunities — FREE. Start here. Use short keyword queries; if nothing relevant comes back, try broader or different keywords.
- crustdata_person_search — find a hiring manager / recruiter / engineering lead at the chosen company.
- crustdata_person_enrich — get that ONE person's email (~2 credits).
- draft_email — write the email. contact_email must come from a tool result.
- request_approval — saves the lead and shows the draft to the user. Ends your work.

## Decisions
- Pick the opportunity that best matches the user's goal and profile.
- Prefer a named person found via Crustdata. If Crustdata fails or finds nobody with an email, and the posting has an application_email, use that instead.
- If a tool fails, adapt (different title, different company, fallback contact). Never repeat an identical call.
- You cannot send email. After request_approval succeeds, stop.

## Style
Before EVERY tool call, write one short sentence (max 20 words) explaining why you chose it. Nothing else.

Budget: {max_steps} tool calls, {budget} Crustdata credits.
"""


@dataclass
class _RunState:
    """Wraps ToolContext with loop-specific state (not visible to tools)."""
    context: ToolContext
    messages: list[dict]
    step_index: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class Orchestrator:
    """Public entrypoint for the agent. Runs are held in memory (single process)."""

    _RUNS: dict[UUID, AgentRun] = {}
    _STATES: dict[UUID, _RunState] = {}
    _TASKS: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def get_run(cls, run_id: UUID) -> AgentRun | None:
        return cls._RUNS.get(run_id)

    @classmethod
    def start_in_background(cls, goal: AgentGoal, user_id: UUID) -> AgentRun:
        """Register a run and execute it in a background task (own DB session).

        Returns immediately so the UI can poll GET /agent/run/{id} and render
        the trace step by step.
        """
        run = AgentRun(user_id=user_id, goal=goal, status=AgentStatus.EXECUTING)
        cls._RUNS[run.id] = run
        task = asyncio.create_task(cls._background(run, user_id))
        cls._TASKS.add(task)
        task.add_done_callback(cls._TASKS.discard)
        return run

    @classmethod
    async def run_goal(
        cls,
        goal: AgentGoal,
        user: User,
        db: AsyncSession,
        dry_run: bool | None = None,
    ) -> AgentRun:
        """Execute a run inline. Returns when paused or finished (eval/smoke)."""
        if dry_run is not None and dry_run != goal.dry_run:
            goal = goal.model_copy(update={"dry_run": dry_run})
        run = AgentRun(user_id=user.id, goal=goal, status=AgentStatus.EXECUTING)
        cls._RUNS[run.id] = run
        await cls._execute(run, user, db)
        return run

    @classmethod
    async def approve(
        cls,
        run_id: UUID,
        decision: ApprovalDecision,
        db: AsyncSession | None = None,
    ) -> AgentRun:
        """Apply the user's HITL decision. On approval, send — no LLM involved."""
        run = cls._RUNS.get(run_id)
        state = cls._STATES.get(run_id)
        if run is None or state is None:
            raise ValueError(f"Run {run_id} not found")

        async with state.lock:
            # Re-check inside the lock: a second concurrent approve must not send twice.
            if run.status != AgentStatus.AWAITING_APPROVAL:
                raise ValueError(f"Run is {run.status.value}, not awaiting approval")
            ctx = state.context
            if db is not None:
                ctx.session = db
            approval = ctx.pending_approval
            if approval is None:
                run.status = AgentStatus.FAILED
                run.error = "Approval requested but no pending approval found"
                return run

            if not decision.approved:
                await update_lead(ctx, status=OutreachStatus.SKIPPED.value)
                run.status = AgentStatus.CANCELLED
                run.error = decision.reason or "Rejected by user — nothing was sent"
                run.updated_at = datetime.now(timezone.utc)
                return run

            # The approved payload (with the user's edits) is the ONLY thing sent.
            if decision.edited_subject and decision.edited_subject.strip():
                approval.subject = decision.edited_subject.strip()
            if decision.edited_body and decision.edited_body.strip():
                approval.body = decision.edited_body.strip()
            args = {
                "recipient_email": approval.recipient_email,
                "subject": approval.subject,
                "body": approval.body,
            }
            run.status = AgentStatus.EXECUTING
            step = cls._record_step(run, state, ToolName.SEND_EMAIL.value, args, "Approved by user.")
            result = await execute_tool(ToolName.SEND_EMAIL, args, ctx)
            cls._finish_step(run, state, step, result)
            if result.ok:
                run.status = AgentStatus.COMPLETED
            else:
                run.status = AgentStatus.FAILED
                run.error = result.error
            run.updated_at = datetime.now(timezone.utc)
        return run

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @classmethod
    async def _background(cls, run: AgentRun, user_id: UUID) -> None:
        from app.db.session import AsyncSessionLocal

        try:
            async with AsyncSessionLocal() as db:
                user = await db.get(User, user_id)
                if user is None:
                    run.status = AgentStatus.FAILED
                    run.error = "User not found"
                    return
                await cls._execute(run, user, db)
        except Exception as exc:  # never let a background task die silently
            logger.exception("agent_background_failed", extra={"run_id": str(run.id)})
            run.status = AgentStatus.FAILED
            run.error = f"{type(exc).__name__}: {exc}"

    @classmethod
    async def _execute(cls, run: AgentRun, user: User, db: AsyncSession) -> None:
        goal = run.goal
        ctx = ToolContext(
            session=db,
            user=user,
            run_id=run.id,
            dry_run=goal.dry_run,
            crustdata=CrustdataClient(credit_budget=goal.credit_budget),
        )
        state = _RunState(
            context=ctx,
            messages=[
                {
                    "role": "system",
                    "content": PLANNER_SYSTEM_PROMPT.format(
                        max_steps=goal.max_steps, budget=goal.credit_budget
                    ),
                },
                {"role": "user", "content": cls._goal_prompt(goal, user)},
            ],
        )
        cls._STATES[run.id] = state
        try:
            await cls._continue_loop(run, state)
        except LLMProviderError as exc:
            run.status = AgentStatus.FAILED
            run.error = f"LLM unavailable: {exc}"
        except Exception as exc:
            run.status = AgentStatus.FAILED
            run.error = f"{type(exc).__name__}: {exc}"
            logger.exception("agent_run_failed", extra={"run_id": str(run.id)})
        finally:
            try:
                if ctx.crustdata is not None:
                    await ctx.crustdata.close()
            except Exception:
                pass
            run.updated_at = datetime.now(timezone.utc)

    @classmethod
    async def _continue_loop(cls, run: AgentRun, state: _RunState) -> None:
        ctx = state.context
        nudges_left = 2

        while state.step_index < run.goal.max_steps:
            response = await chat(state.messages, tools=TOOL_SCHEMAS)

            if not response.tool_calls and nudges_left > 0:
                # Small models sometimes narrate instead of acting. Nudge, don't fail.
                nudges_left -= 1
                state.messages.append({"role": "assistant", "content": response.content or ""})
                state.messages.append({
                    "role": "user",
                    "content": "Continue: call the next tool now. Your work ends only when request_approval succeeds.",
                })
                continue

            if not response.tool_calls:
                # The model stopped without producing a draft for approval.
                run.status = AgentStatus.FAILED
                run.error = (
                    (response.content or "").strip()[:300]
                    or "Agent stopped before producing a draft"
                )
                return

            tc = response.tool_calls[0]
            if len(response.tool_calls) > 1:
                logger.warning(
                    "llm_emitted_multiple_tool_calls",
                    extra={"count": len(response.tool_calls), "run_id": str(run.id)},
                )
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"] or "{}")
                if not isinstance(tool_args, dict):
                    tool_args = {}
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

            step = cls._record_step(run, state, tool_name, tool_args, response.content)
            if tool_name not in LLM_CALLABLE_TOOLS:
                # e.g. the model hallucinates send_email — refuse, never execute.
                result = ToolResult(
                    tool=tool_name, ok=False,
                    error=f"Tool {tool_name!r} is not available to the agent",
                )
            else:
                if tool_name == ToolName.REQUEST_APPROVAL.value:
                    tool_args = {**tool_args, "_step_index": state.step_index}
                result = await execute_tool(tool_name, tool_args, ctx)
            cls._finish_step(run, state, step, result)

            # Only the first tool call is executed; send back just that one so
            # the conversation stays consistent for every provider.
            state.messages.append(
                {"role": "assistant", "content": response.content, "tool_calls": [tc]}
            )
            payload = (
                json.dumps(result.data, default=str)[:2000]
                if result.ok
                else json.dumps({"error": result.error})
            )
            state.messages.append({"role": "tool", "tool_call_id": tc["id"], "content": payload})
            state.step_index += 1

            if tool_name == ToolName.REQUEST_APPROVAL.value and result.ok:
                run.status = AgentStatus.AWAITING_APPROVAL
                return

        run.status = AgentStatus.FAILED
        run.error = f"Max steps ({run.goal.max_steps}) reached before a draft was ready"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_step(
        run: AgentRun, state: _RunState, tool_name: str, tool_args: dict, rationale: str | None
    ) -> AgentStep:
        try:
            call = ToolCall(tool=tool_name, args=tool_args, rationale=(rationale or "").strip() or None)
        except Exception:
            # Unknown tool name: keep the trace honest without failing validation.
            call = ToolCall.model_construct(tool=tool_name, args=tool_args, rationale=rationale)
        step = AgentStep(
            index=len(run.plan),
            call=call,
            status=StepStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        run.plan.append(step)
        run.current_step = step.index
        run.updated_at = datetime.now(timezone.utc)
        return step

    @staticmethod
    def _finish_step(run: AgentRun, state: _RunState, step: AgentStep, result: ToolResult) -> None:
        step.result = result
        step.status = StepStatus.OK if result.ok else StepStatus.FAILED
        step.finished_at = datetime.now(timezone.utc)
        run.credits_used = round(state.context.credits_used, 4)
        run.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _goal_prompt(goal: AgentGoal, user: User) -> str:
        return (
            f"User goal: {goal.prompt}\n\n"
            f"User profile:\n{applicant_profile_block(user)}\n\n"
            "Begin."
        )


__all__ = ["Orchestrator", "PLANNER_SYSTEM_PROMPT"]
