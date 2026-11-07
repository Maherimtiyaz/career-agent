"""Agent domain schemas — Pydantic v2, strict, JSON-serializable.

Wire format between API layer, orchestrator, and frontend agent console.
Nothing here touches the DB.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


class ToolName(str, Enum):
    DB_SEARCH_OPPORTUNITIES = "db_search_opportunities"
    CRUSTDATA_PERSON_SEARCH = "crustdata_person_search"
    CRUSTDATA_PERSON_ENRICH = "crustdata_person_enrich"
    FIND_EMAIL = "find_email"
    DRAFT_EMAIL = "draft_email"
    REQUEST_APPROVAL = "request_approval"
    SEND_EMAIL = "send_email"
    SAVE_LEAD = "save_lead"


class CreditEventType(str, Enum):
    SEARCH = "search"
    ENRICH = "enrich"
    COMPANY_ENRICH = "company_enrich"
    JOB_SEARCH = "job_search"


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: ToolName
    args: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: ToolName
    ok: bool
    data: Any | None = None
    error: str | None = None
    duration_ms: int | None = None
    credits_spent: float = 0.0


class AgentStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int = Field(ge=0)
    call: ToolCall
    status: StepStatus = StepStatus.PENDING
    result: ToolResult | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def is_terminal(self) -> bool:
        return self.status in {StepStatus.OK, StepStatus.FAILED, StepStatus.SKIPPED}


class AgentGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=5, max_length=1000)
    max_steps: int = Field(default=8, ge=1, le=20)
    credit_budget: float = Field(default=50.0, ge=0.0, le=500.0)
    dry_run: bool = Field(default=True)


class AgentRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    goal: AgentGoal
    status: AgentStatus = AgentStatus.PENDING
    plan: list[AgentStep] = Field(default_factory=list)
    current_step: int = 0
    credits_used: float = 0.0
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def total_steps(self) -> int:
        return len(self.plan)

    def is_finished(self) -> bool:
        return self.status in {AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED}


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    step_index: int = Field(ge=0)
    kind: Literal["email_send"] = "email_send"
    recipient_email: str
    recipient_name: str | None = None
    subject: str
    body: str
    lead_id: UUID | None = None
    expires_at: datetime | None = None


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    step_index: int = Field(ge=0)
    approved: bool
    edited_subject: str | None = None
    edited_body: str | None = None
    reason: str | None = None


class CreditLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    event: CreditEventType
    endpoint: str
    credits: float = Field(ge=0.0)
    result_count: int = Field(default=0, ge=0)
    cache_hit: bool = False
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
