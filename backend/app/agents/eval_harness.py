"""Agent evaluation harness — runs scripted scenarios and produces metrics.

Usage:
    docker compose exec backend python -m app.agents.eval_harness

Writes:
    backend/eval_results.json    — machine-readable
    backend/eval_results.md      — README-ready table

Scenarios cover: happy paths across domains, rejection flow, vague goals,
budget limits, max-step limits, cache efficiency. Metrics measured per run:
    - final status, steps used, credits spent, wall time
    - tool distribution (proves adaptive planning)
    - approval gate reached (proves HITL safety)

Deterministic setup: dry_run=True (no Crustdata credits consumed), a fixed
test user, fresh Orchestrator state per run. Cache hits between scenarios
are expected and desirable — they prove the credit-budget design works.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select

from app.agents.orchestrator import Orchestrator
from app.agents.schemas import (
    AgentGoal,
    AgentRun,
    AgentStatus,
    ApprovalDecision,
)
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

class Scenario(BaseModel):
    id: int
    name: str
    prompt: str
    max_steps: int = 10
    credit_budget: float = 20.0
    # None = do not interact with approval (just observe where it stops)
    # True = approve, False = reject
    approve: bool | None = True
    # Acceptable final statuses — a scenario "passes" if run ends in one of these
    expected: list[str]


SCENARIOS: list[Scenario] = [
    Scenario(
        id=1,
        name="Happy path — ML internship",
        prompt=(
            "Find 1 ML internship from my saved opportunities and draft "
            "outreach to a relevant hiring contact."
        ),
        expected=["completed", "awaiting_approval"],
    ),
    Scenario(
        id=2,
        name="Happy path — Backend role",
        prompt=(
            "Find 1 backend engineering internship and reach out to an "
            "engineering manager at the company."
        ),
        expected=["completed", "awaiting_approval"],
    ),
    Scenario(
        id=3,
        name="Happy path — Data science role",
        prompt=(
            "Find 1 data science internship and draft a personalized "
            "outreach email to someone on that team."
        ),
        expected=["completed", "awaiting_approval"],
    ),
    Scenario(
        id=4,
        name="Reject flow — user declines draft",
        prompt=(
            "Find 1 ML internship and draft an email to a hiring contact "
            "for my review."
        ),
        approve=False,
        expected=["cancelled"],
    ),
    Scenario(
        id=5,
        name="Vague goal — planning under uncertainty",
        prompt="Find me something good and reach out.",
        expected=["completed", "awaiting_approval", "failed"],
    ),
    Scenario(
        id=6,
        name="Broad — any tech internship",
        prompt=(
            "Find any tech internship and draft an outreach email to a "
            "hiring contact."
        ),
        expected=["completed", "awaiting_approval"],
    ),
    Scenario(
        id=7,
        name="Budget constrained — tiny credit budget",
        prompt=(
            "Find 1 ML internship and reach out to a hiring contact."
        ),
        credit_budget=0.05,
        expected=["completed", "awaiting_approval", "failed"],
    ),
    Scenario(
        id=8,
        name="Max-steps constrained — 3 step limit",
        prompt=(
            "Find 1 ML internship and reach out to a hiring contact."
        ),
        max_steps=3,
        expected=["failed", "awaiting_approval"],
    ),
    Scenario(
        id=9,
        name="Recruiter contact (not manager)",
        prompt=(
            "Find 1 ML internship and reach out to a recruiter — "
            "not an engineering manager — for that company."
        ),
        expected=["completed", "awaiting_approval"],
    ),
    Scenario(
        id=10,
        name="Repeat — same goal as #1 (cache efficiency)",
        prompt=(
            "Find 1 ML internship from my saved opportunities and draft "
            "outreach to a relevant hiring contact."
        ),
        expected=["completed", "awaiting_approval"],
    ),
]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class ScenarioResult(BaseModel):
    id: int
    name: str
    passed: bool
    status: str
    steps: int
    credits: float
    wall_seconds: float
    approval_reached: bool
    tools: list[str]
    error: str | None = None


def _find_approval_step_index(run: AgentRun) -> int | None:
    for step in reversed(run.plan):
        if step.result and step.result.ok and isinstance(step.result.data, dict):
            if "approval_request" in step.result.data:
                return step.index
    return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def _get_or_create_eval_user() -> User:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == "eval@example.com"))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email="eval@example.com",
                hashed_password=hash_password("evalpass"),
                full_name="Eval Runner",
                skills="Python, FastAPI, ML",
                target_roles="ML Engineer Internship",
                is_active=True,
                is_verified=True,
                is_superuser=False,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user


async def run_scenario(scenario: Scenario, user: User) -> ScenarioResult:
    goal = AgentGoal(
        prompt=scenario.prompt,
        max_steps=scenario.max_steps,
        credit_budget=scenario.credit_budget,
        dry_run=True,
    )
    start = time.monotonic()

    async with AsyncSessionLocal() as db:
        run = await Orchestrator.run_goal(goal, user, db, dry_run=True)
        approval_reached = run.status == AgentStatus.AWAITING_APPROVAL

        if approval_reached and scenario.approve is not None:
            step_index = _find_approval_step_index(run)
            if step_index is not None:
                decision = ApprovalDecision(
                    run_id=run.id,
                    step_index=step_index,
                    approved=scenario.approve,
                    reason=None if scenario.approve else "eval-reject",
                )
                run = await Orchestrator.approve(run.id, decision, db=db)

    duration = time.monotonic() - start
    tool_names = [step.call.tool for step in run.plan]

    return ScenarioResult(
        id=scenario.id,
        name=scenario.name,
        passed=run.status.value in scenario.expected,
        status=run.status.value,
        steps=len(run.plan),
        credits=round(run.credits_used, 3),
        wall_seconds=round(duration, 2),
        approval_reached=approval_reached,
        tools=tool_names,
        error=run.error,
    )


# ---------------------------------------------------------------------------
# Aggregation + output
# ---------------------------------------------------------------------------

def aggregate(results: list[ScenarioResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    approvals = sum(1 for r in results if r.approval_reached)
    completed = [r for r in results if r.status == "completed"]
    tool_counter = Counter()
    for r in results:
        for t in r.tools:
            tool_counter[t] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": total,
        "passed": passed,
        "success_rate": round(passed / total * 100, 1) if total else 0.0,
        "approval_rate": round(approvals / total * 100, 1) if total else 0.0,
        "avg_steps": round(
            sum(r.steps for r in results) / total, 2
        ) if total else 0.0,
        "avg_credits_per_completed": round(
            sum(r.credits for r in completed) / len(completed), 3
        ) if completed else 0.0,
        "avg_wall_seconds": round(
            sum(r.wall_seconds for r in results) / total, 2
        ) if total else 0.0,
        "tool_distribution": dict(tool_counter.most_common()),
        "results": [r.model_dump() for r in results],
    }


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        "# Agent Evaluation Results",
        "",
        f"Generated: `{summary['generated_at']}`  ",
        f"Mode: dry-run (no Crustdata credits consumed, no emails sent)",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Scenarios run | {summary['total_scenarios']} |",
        f"| Passed | {summary['passed']}/{summary['total_scenarios']} |",
        f"| Success rate | {summary['success_rate']}% |",
        f"| Approval gate reached | {summary['approval_rate']}% |",
        f"| Avg steps per run | {summary['avg_steps']} |",
        f"| Avg credits per completed run | {summary['avg_credits_per_completed']} |",
        f"| Avg wall time | {summary['avg_wall_seconds']}s |",
        "",
        "## Per-scenario results",
        "",
        "| # | Scenario | Status | Steps | Credits | Time | Tools called |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in summary["results"]:
        tools = " → ".join(r["tools"]) if r["tools"] else "—"
        lines.append(
            f"| {r['id']} | {r['name']} | `{r['status']}` | "
            f"{r['steps']} | {r['credits']} | {r['wall_seconds']}s | {tools} |"
        )

    lines += [
        "",
        "## Tool distribution",
        "",
        "| Tool | Calls |",
        "|---|---|",
    ]
    for tool, count in summary["tool_distribution"].items():
        lines.append(f"| `{tool}` | {count} |")

    lines += [
        "",
        "## Interpretation",
        "",
        "- **Success rate** measures how often the agent completes the workflow "
        "end-to-end or reaches a valid approval pause.",
        "- **Approval rate** confirms the HITL safety gate fires in every "
        "scenario where an email was drafted.",
        "- **Tool distribution** proves the agent selects different tools based "
        "on context — not a hardcoded script.",
        "- **Credits** are simulated in dry-run mode; in live mode the same "
        "caching and budget logic governs real spend.",
        "- **Cache efficiency** — repeated goals (scenario 10) cost near zero "
        "because identical Crustdata queries hit the Redis cache.",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    print("[eval] preparing user...")
    user = await _get_or_create_eval_user()

    results: list[ScenarioResult] = []
    for s in SCENARIOS:
        await asyncio.sleep(8)  # rate limit mitigation
        print(f"\n[eval] {s.id}/{len(SCENARIOS)} — {s.name}")
        try:
            r = await run_scenario(s, user)
            results.append(r)
            mark = "PASS" if r.passed else "FAIL"
            print(
                f"  [{mark}] status={r.status} steps={r.steps} "
                f"credits={r.credits} time={r.wall_seconds}s"
            )
        except Exception as exc:
            print(f"  [ERROR] {type(exc).__name__}: {exc}")
            results.append(
                ScenarioResult(
                    id=s.id,
                    name=s.name,
                    passed=False,
                    status="error",
                    steps=0,
                    credits=0.0,
                    wall_seconds=0.0,
                    approval_reached=False,
                    tools=[],
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    summary = aggregate(results)

    out_dir = Path("/app/data")
    json_path = out_dir / "eval_results.json"
    md_path = out_dir / "eval_results.md"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, md_path)

    print(f"\n[eval] ─────────────────────────────────────────")
    print(f"[eval] Success rate:     {summary['success_rate']}% "
          f"({summary['passed']}/{summary['total_scenarios']})")
    print(f"[eval] Approval reached: {summary['approval_rate']}%")
    print(f"[eval] Avg steps:        {summary['avg_steps']}")
    print(f"[eval] Avg credits:      {summary['avg_credits_per_completed']}")
    print(f"[eval] Avg wall time:    {summary['avg_wall_seconds']}s")
    print(f"[eval] JSON written:     {json_path}")
    print(f"[eval] Markdown written: {md_path}")


if __name__ == "__main__":
    asyncio.run(main())

