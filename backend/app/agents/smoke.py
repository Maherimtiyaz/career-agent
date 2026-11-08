"""End-to-end smoke test for the agent.

Runs the full loop against the real DB and real Gemini, with Crustdata
in dry-run. Prints every step, the pending approval, and the final state.

Usage:
    docker compose exec backend python -m app.agents.smoke

Safe: no real emails, no Crustdata credits spent.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.agents.orchestrator import Orchestrator
from app.agents.schemas import AgentGoal, ApprovalDecision
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def _get_or_create_user():
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if user is None:
            user = User(
                email="smoke@agent.test",
                hashed_password="x",
                full_name="Smoke Tester",
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


async def _print_run(run, label: str) -> None:
    print(f"\n[{label}] status={run.status.value} credits={run.credits_used:.2f} steps={len(run.plan)}")
    for step in run.plan:
        icon = {"ok": "+", "failed": "x", "skipped": "-", "running": "..."}.get(
            step.status.value, "?"
        )
        preview = ""
        if step.result and step.result.data:
            data = step.result.data
            if isinstance(data, list):
                preview = f"-> {len(data)} items"
            elif isinstance(data, dict):
                keys = list(data.keys())[:3]
                preview = f"-> {keys}"
        print(f"  [{icon}] {step.index}. {step.call.tool}")
        if preview:
            print(f"        {preview}")
        if step.result and not step.result.ok and step.result.error:
            print(f"        ERROR: {step.result.error[:120]}")


async def main() -> None:
    user = await _get_or_create_user()
    print(f"[smoke] user: {user.email}")

    goal = AgentGoal(
        prompt=(
            "Find 1 ML internship from my saved opportunities and draft "
            "an outreach email to a relevant contact. Show me the draft "
            "for approval before sending."
        ),
        max_steps=8,
        credit_budget=20.0,
        dry_run=True,
    )

    async with AsyncSessionLocal() as db:
        run = await Orchestrator.run_goal(goal, user, db, dry_run=True)
        await _print_run(run, "initial")

        if run.status.value == "awaiting_approval" and run.plan:
            last = run.plan[-1]
            approval = (last.result.data or {}).get("approval_request") or {}
            print("\n[approval] PENDING:")
            print(f"  to:      {approval.get('recipient_email')}")
            print(f"  subject: {approval.get('subject')}")
            body = approval.get("body") or ""
            print(f"  body:    {body[:300]}{'...' if len(body) > 300 else ''}")

            decision = ApprovalDecision(
                run_id=run.id,
                step_index=last.index,
                approved=True,
            )
            print("\n[approval] user APPROVED -- resuming")
            run = await Orchestrator.approve(run.id, decision)
            await _print_run(run, "after-approval")

        if run.status.value == "failed":
            print(f"\n[smoke] FAILED: {run.error}")


if __name__ == "__main__":
    asyncio.run(main())
