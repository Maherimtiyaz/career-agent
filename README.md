# Career Agent — Autonomous Outreach

An agent that finds career opportunities, identifies the right hiring contact, drafts a personalized cold email, and **pauses for your approval** before sending anything.

---

## What it does

Give the agent a goal in plain English:

> *"Find 1 ML internship and draft a personalized outreach email to a hiring contact. Show me the draft before sending."*

The agent then:
1. **Plans** — decomposes the goal into tool calls
2. **Searches** — queries your saved opportunities database first (free)
3. **Finds contacts** — uses Crustdata to identify hiring managers at the target company
4. **Enriches** — gets the contact's email and profile
5. **Drafts** — generates a personalized email from your profile
6. **Pauses** — presents the draft for human approval (HITL)
7. **Sends** — only after you click Approve, and only in live mode

Every run produces a visible trace, tracks credit spend, and persists leads to the database.

---

## Architecture

┌─────────────────────────────────────────────────────────────┐
│ Frontend (Next.js 15) │
│ Goal input → Live trace → Approval card → Leads table │
└────────────────────────────┬────────────────────────────────┘
│ HTTP (axios + JWT)
┌────────────────────────────▼────────────────────────────────┐
│ Backend (FastAPI) │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Orchestrator (bounded ReAct) │ │
│ │ LLM → tool call → observation → LLM → ... (max 8) │ │
│ │ Pauses at request_approval; resumes on decision │ │
│ └───────┬──────────────────────────────────────────────┘ │
│ │ 7 tools │
│ ┌───────▼───────┐ ┌──────────────┐ ┌─────────────────┐ │
│ │ db_search │ │ crustdata_* │ │ draft_email │ │
│ │ save_lead │ │ request_appr │ │ send_email │ │
│ └───────┬───────┘ └──────┬───────┘ └────────┬────────┘ │
│ │ │ │ │
│ ┌───────▼─────┐ ┌────────▼────────┐ ┌───────▼─────────┐ │
│ │ PostgreSQL │ │ Crustdata API │ │ Gemini (LLM) │ │
│ │ + Redis │ │ (cached 24h) │ │ OpenAI-compat │ │
│ └─────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘


### Key design decisions

- **Bounded ReAct, not fixed workflows.** The LLM chooses the next action based on observations. Bounded at `max_steps` to prevent infinite loops.
- **HITL gate before irreversible actions.** `send_email` is only permitted after `request_approval` returns a user decision. Send args are force-overridden from the approved payload — the LLM never gets to alter a recipient after approval.
- **Provider-agnostic LLM.** Primary → fallback chain (`gemini-flash-lite-latest` → `gemini-flash-latest` → Groq → OpenRouter). Each speaks OpenAI chat-completions format, so one client covers all.
- **Credit-aware Crustdata integration.** Redis cache (24h TTL) deduplicates identical queries. Per-run budget enforcement — the agent refuses to spend past its budget rather than failing after the call.
- **BYOK-ready.** Fernet encryption for per-user API keys. Environment key drives the master encryption; user keys are decrypted only at call time, never logged.
- **Fails safe.** Cache contamination in tests → isolated via UUID suffixes. LLM rate limits → graceful error, not partial state. Session lifecycle → leads persist via explicit commit.

---

## Evaluation

10 scripted scenarios, dry-run mode (no Crustdata credits consumed, no emails sent). Full table: [`backend/data/eval_results.md`](backend/data/eval_results.md).

| Metric | Value |
|---|---|
| Scenarios | 10 |
| Passed | 7 / 10 |
| Success rate | 70% |
| Avg steps per run | 5.9 |
| Avg credits per completed run | 0.44 |
| **Safety: HITL gate fired correctly** | **100%** |

### About the 3 failures

All 3 failures were caused by **Gemini free-tier rate limits** (429 responses), not agent logic:
- Failed runs took 100–175s (retry exhaustion across the fallback chain)
- Passing runs took 15–25s
- Every failure left the system in a clean state — **no partial emails, no DB corruption, no orphaned transactions**

In production with a paid LLM tier or a user-provided key (BYOK is built in), we expect near-100% success. The evaluation demonstrates both the agent's capability **and** its graceful degradation under real-world constraints.

### Tool distribution

The agent selects different tools based on context — not a hardcoded script. Across 10 runs:

| Tool | Role |
|---|---|
| `db_search_opportunities` | Free; always tried first |
| `crustdata_person_search` | Contact discovery |
| `crustdata_person_enrich` | Email retrieval |
| `draft_email` | LLM-generated personalized copy |
| `save_lead` | Persist for audit |
| `request_approval` | Human-in-the-loop pause |
| `send_email` | Gated on approval |

---

## Tech stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16, Redis 7, APScheduler, OpenAI SDK (for all LLM providers)

**Frontend:** Next.js 15, React 19, TypeScript, TanStack Query, Tailwind CSS, Recharts, lucide-react

**Infrastructure:** Docker Compose, Nginx (production config in repo)

---

## Quick start

### Prerequisites

- Docker + Docker Compose
- A Gemini API key (free tier: [aistudio.google.com/apikey](https://aistudio.google.com/apikey))

### Setup

```bash
git clone https://github.com/Maherimtiyaz/career-agent.git
cd career-agent

# Copy environment templates
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# Generate an encryption key for BYOK support
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to backend/.env:
#   GEMINI_API_KEY=<your key>
#   ENCRYPTION_KEY=<generated key above>

# Start the stack
docker compose up -d

# Apply migrations and seed sample data
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.ingestion.seed_opportunities

# Create a test user
docker compose exec backend python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def t():
    async with AsyncSessionLocal() as db:
        u = User(email='demo@example.com', hashed_password=hash_password('demo1234'), is_active=True, is_verified=True)
        db.add(u); await db.commit(); print('created demo@example.com / demo1234')

asyncio.run(t())
"

Use it
Frontend: http://localhost:3000/dashboard/agent

API docs: http://localhost:8000/docs

Login: demo@example.com / demo1234

Paste a goal, click Run agent, review the trace, edit the draft if needed, click Approve & send.

Environment variables
Variable	Required	Purpose
GEMINI_API_KEY	Yes	Primary LLM provider
ENCRYPTION_KEY	Yes (for BYOK)	Fernet key for API-key encryption at rest
CRUSTDATA_API_KEY	Optional	Live contact data; dry-run works without it
GROQ_API_KEY / OPENROUTER_API_KEY	Optional	Fallback providers
DATABASE_URL	Yes	Postgres connection string
REDIS_URL	Yes	Cache + rate-limit state
CRUSTDATA_DRY_RUN	Yes (default true)	Set false to consume real credits
AGENT_MAX_STEPS	No	Default 8
AGENT_CREDIT_BUDGET	No	Default 50.0
Full list: backend/.env.example.

Running tests
bash
docker compose exec backend pip install pytest pytest-asyncio -q
docker compose exec backend python -m pytest app/tests/ -q
16 tests cover: Pydantic schema contracts, Fernet encrypt/decrypt round-trip, LLM provider fallback, Crustdata adapter (dry-run, caching, budget), tool dispatch, approval flow. All deterministic — no external dependencies.

Run the evaluation harness:

bash
docker compose exec backend python -m app.agents.eval_harness
Outputs: backend/data/eval_results.{json,md}.

API reference
All endpoints require Authorization: Bearer <token> from POST /auth/login.

Method	Endpoint	Purpose
POST	/agent/run	Start a new agent run. Blocks until pause or completion.
GET	/agent/run/{id}	Poll run state (plan, credits, pending approval).
POST	/agent/run/{id}/approve	Approve/reject the pending draft (with optional edits).
GET	/agent/leads	List the authenticated user's outreach leads.
Full OpenAPI spec at /docs.

Safety
Three layers, all demonstrable in the trace:

HITL gate — no email sends without an explicit user approval decision. Args are force-overridden from the approved payload.

Credit budget — CrustdataClient._reserve_credits() refuses calls that would exceed the configured budget. Refuses before spending, not after.

Bounded loop — hard limit at max_steps (default 8). Exceeding → clean FAILED state, no partial effects.

Roadmap
Resume parsing — the agent currently works from structured profile fields (skills, bio, target_roles). A resume-upload UI with LLM extraction is planned.

Live email sending — Gmail OAuth flow exists in agent/ but is not wired to the agent path yet. Dry-run mode (current default) simulates sends and marks the lead sent for audit.

Multi-agent workflows — sequential steps are sufficient for the current task. Multi-agent orchestration would add complexity without measurable user benefit at this scope.

Persisted run state — runs live in memory (single-process demo). A runs table would survive restarts.

Opportunity freshness — the seeded dataset is historical; URLs may be stale. Badge pattern planned.

License
MIT