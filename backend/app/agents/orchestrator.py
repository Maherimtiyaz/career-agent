"""Bounded ReAct orchestrator for the career outreach agent.

The loop:
  1. Send goal + tool schemas + observation history to the LLM.
  2. LLM returns the next tool call (or a final answer with no tool call).
  3. Orchestrator executes the call via tools.execute_tool().
  4. Observation appended to messages. Loop.
  
Pauses at request_approval so the user can review the draft in the UI.
approve() resumes the loop with the user's edits applied.

Safety:
  - Bounded at goal.max_steps — no infinite loops.
  - send_email args FORCED from pending_approval (never trust the LLM
    to repeat the recipient/subject/body correctly after approval).
  - Per-run asyncio.Lock prevents concurrent approve() races.
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
    ApprovalDecision,
    StepStatus,
    ToolCall,
    ToolName,
)
from app.agents.tools import (
    TOOL_SCHEMAS,
    ToolContext,
    execute_tool,
)
from app.models.user import User


logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are an autonomous career outreach agent. You help a user find relevant opportunities and connect with the right people via personalized emails.

## Workflow order (strict)
1. db_search_opportunities — find roles in the user's tracked database. FREE. Do this FIRST.
2. crustdata_person_search — find a contact at a specific company. ~0.03 credits/result.
3. crustdata_person_enrich — get the contact's email. ~2 credits. Only for contacts you WILL email.
4. draft_email — write a personalized email. Pass contact_name, contact_title, contact_email, company, role, context.
5. save_lead — persist the lead. AFTER draft_email, BEFORE request_approval.
6. request_approval — PAUSE for user approval. MANDATORY before send_email.
7. send_email — only after user approval. Then STOP.

## Rules
- One tool call per turn. Read the result before deciding the next action.
- If search returns nothing, try a broader query. Never repeat identical calls.
- If a tool fails, try a variant or skip. Do not retry identical failures.
- When done (email sent OR pending approval), STOP — reply with no tool call.
- Never narrate. Emit only tool calls.

Be efficient. Budget: {max_steps} tool calls, {budget} Crustdata credits.
"""


@dataclass
class _RunState:
    """Wraps ToolContext with loop-specific state (not visible to tools)."""
    context: ToolContext
    messages: list[dict]
    step_index: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class Orchestrator:
    """Public entrypoint for the agent. All methods classmethod/static."""

    _RUNS: dict[UUID, AgentRun] = {}
    _STATES: dict[UUID, _RunState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def get_run(cls, run_id: UUID) -> AgentRun | None:
        return cls._RUNS.get(run_id)

    @classmethod
    async def run_goal(
        cls,
        goal: AgentGoal,
        user: User,
        db: AsyncSession,
        dry_run: bool | None = None,
    ) -> AgentRun:
        """Execute a new agent run. Returns when paused or finished."""
        run = AgentRun(user_id=user.id, goal=goal, status=AgentStatus.EXECUTING)
        cls._RUNS[run.id] = run

        ctx = ToolContext(
            session=db,
            user=user,
            run_id=run.id,
            dry_run=dry_run if dry_run is not None else goal.dry_run,
            crustdata=CrustdataClient(credit_budget=goal.credit_budget),
        )
        system = PLANNER_SYSTEM_PROMPT.format(
            max_steps=goal.max_steps, budget=goal.credit_budget
        )
        state = _RunState(
            context=ctx,
            messages=[
                {"role": "system", "content": system},
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

        return run

    @classmethod
    async def approve(cls, run_id: UUID, decision: ApprovalDecision) -> AgentRun:
        """Resume a paused run after the user's HITL decision."""
        run = cls._RUNS.get(run_id)
        state = cls._STATES.get(run_id)
        if run is None or state is None:
            raise ValueError(f"Run {run_id} not found")
        if run.status != AgentStatus.AWAITING_APPROVAL:
            raise ValueError(
                f"Run is {run.status.value}, not awaiting approval"
            )

        async with state.lock:
            if not decision.approved:
                run.status = AgentStatus.CANCELLED
                run.error = decision.reason or "Rejected by user"
                run.updated_at = datetime.now(timezone.utc)
                return run

            approval = state.context.pending_approval
            if approval is None:
                run.status = AgentStatus.FAILED
                run.error = "Approval requested but no pending approval found"
                return run
            if approval.step_index != decision.step_index:
                raise ValueError(
                    f"Approval step mismatch: pending={approval.step_index}, "
                    f"received={decision.step_index}"
                )

            # Apply user edits to the approved payload — this is what will
            # be sent, regardless of what the LLM later passes to send_email.
            if decision.edited_subject:
                approval.subject = decision.edited_subject
            if decision.edited_body:
                approval.body = decision.edited_body

            state.messages.append(
                {
                    "role": "user",
                    "content": (
                        "The user APPROVED the email. Your next action must be "
                        "send_email with the same recipient. After send_email "
                        "succeeds, STOP and reply with a brief confirmation — "
                        "no more tool calls."
                    ),
                }
            )
            run.status = AgentStatus.EXECUTING
            try:
                await cls._continue_loop(run, state)
            except LLMProviderError as exc:
                run.status = AgentStatus.FAILED
                run.error = f"LLM unavailable on resume: {exc}"
            except Exception as exc:
                run.status = AgentStatus.FAILED
                run.error = f"{type(exc).__name__}: {exc}"
            finally:
                run.updated_at = datetime.now(timezone.utc)

        return run

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    @classmethod
    async def _continue_loop(cls, run: AgentRun, state: _RunState) -> None:
        ctx = state.context

        while state.step_index < run.goal.max_steps:
            response = await chat(state.messages, tools=TOOL_SCHEMAS)

            # LLM signalled completion
            if not response.tool_calls:
                run.status = AgentStatus.COMPLETED
                return

            # Take first tool call only; log any extras the LLM emitted
            tc = response.tool_calls[0]
            if len(response.tool_calls) > 1:
                logger.warning(
                    "llm_emitted_multiple_tool_calls",
                    extra={"count": len(response.tool_calls), "run_id": str(run.id)},
                )

            tool_name_str = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"] or "{}")
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

            # Defense: send_email must use the APPROVED payload
            if tool_name_str == ToolName.SEND_EMAIL.value:
                approval = ctx.pending_approval
                if approval is None:
                    step = cls._record_step(
                        run, state, tool_name_str, tool_args, response.content
                    )
                    step.status = StepStatus.SKIPPED
                    step.result = (
                        cls._make_fail(tool_name_str, "No prior approval")
                    )
                    state.step_index += 1
                    continue
                tool_args = {
                    "recipient_email": approval.recipient_email,
                    "subject": approval.subject,
                    "body": approval.body,
                }

            step = cls._record_step(
                run, state, tool_name_str, tool_args, response.content
            )

            result = await execute_tool(tool_name_str, tool_args, ctx)
            step.result = result
            step.status = StepStatus.OK if result.ok else StepStatus.FAILED
            step.finished_at = datetime.now(timezone.utc)
                        # After send_email succeeds, the run is DONE. Do not rely on the
            # LLM to emit a final no-tool-call turn — some models will try
            # one more action, hitting max_steps and falsely reporting failure.
            if (
                tool_name_str == ToolName.SEND_EMAIL.value
                and result.ok
            ):
                run.status = AgentStatus.COMPLETED
                run.current_step = state.step_index
                run.credits_used = ctx.credits_used
                return

            # Append assistant + tool messages
            state.messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                }
            )
            payload = (
                json.dumps(result.data, default=str)[:2000]
                if result.ok
                else json.dumps({"error": result.error})
            )
            state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": payload,
                }
            )
            state.step_index += 1

            # Pause for HITL
            if tool_name_str == ToolName.REQUEST_APPROVAL.value and result.ok:
                run.status = AgentStatus.AWAITING_APPROVAL
                return

        run.status = AgentStatus.FAILED
        run.error = f"Max steps ({run.goal.max_steps}) exceeded"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_step(
        run: AgentRun,
        state: _RunState,
        tool_name: str,
        tool_args: dict,
        rationale: str | None,
    ):
        from app.agents.schemas import AgentStep

        step = AgentStep(
            index=state.step_index,
            call=ToolCall(tool=tool_name, args=tool_args, rationale=rationale),
            status=StepStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        run.plan.append(step)
        return step

    @staticmethod
    def _make_fail(tool_name: str, error: str):
        from app.agents.schemas import ToolResult

        return ToolResult(tool=tool_name, ok=False, error=error)

    @staticmethod
    def _goal_prompt(goal: AgentGoal, user: User) -> str:
        name = user.full_name or user.email.split("@")[0]
        skills = getattr(user, "skills", None) or "software development"
        target = getattr(user, "target_roles", None) or "internship"
        return (
            f"User goal: {goal.prompt}\n\n"
            f"User profile:\n"
            f"- Name: {name}\n"
            f"- Skills: {skills}\n"
            f"- Target roles: {target}\n"
            f"\nDry-run mode: {'ON' if goal.dry_run else 'OFF'}\n"
            f"Begin. Call db_search_opportunities first."
        )


__all__ = ["Orchestrator", "PLANNER_SYSTEM_PROMPT"]
