# Career Agent: goal in, personalized outreach out, human approval in between

**Career Agent turns one sentence ("find me an ML internship") into a ranked opportunity, a real person to contact, and a personalized email. The email is sent only after you approve it.**

Job seekers lose hours on three jobs: finding a role that fits, figuring out *who* to email, and rewriting the same cold message. Career Agent does all three in about a minute. It shows every step it takes, and it cannot send anything on its own.

---

## The user journey

```
"Find an ML internship that fits my skills and email someone on the team"
   │
   ▼  Discover      db_search_opportunities: ranks the seeded opportunity database against the goal (free)
   ▼  Contact       crustdata_person_search → crustdata_person_enrich: names a hiring manager + email
   │                (falls back to the application email listed on the posting)
   ▼  Personalize   draft_email: written from the user's skills, education and projects
   ▼  Approve       request_approval: saves the lead, run PAUSES; the user edits / approves / rejects
   ▼  Send          executed by the orchestrator, not the LLM, using exactly the approved text
   ▼  Track         outreach history: opportunity, contact, source, status, credits
```

The UI streams this live: a five-stage progress bar, a trace of every tool call with the agent's one-line reasoning, timing and credits, a result card with **source attribution** for the contact, and an approval card where you can edit the draft before sending.

## Why it's trustworthy

| Guarantee | How it's enforced |
|---|---|
| **The AI cannot send email** | `send_email` is not in the LLM's tool list. If the model tries to call it anyway, the call is refused and logged in the trace. Only `POST /agent/run/{id}/approve` sends. |
| **What you approve is what's sent** | The send uses the stored approval payload plus your edits. The model is never consulted after approval. |
| **No hallucinated recipients** | Every email a tool returns is recorded with its source. `draft_email` refuses any address that no tool produced in this run. |
| **No double sends** | Per-run lock, and the status is re-checked inside the lock. A second approve gets HTTP 409. |
| **Honest about data** | Each contact is tagged `From job posting`, `Crustdata · live` or `Simulated contact` (Crustdata dry-run). Demo mode says plainly that delivery is simulated. |
| **Bounded cost** | Crustdata budget is checked *before* each call; results are cached in Redis for 24h; at most 10 tool calls per run. |

All of this is covered by offline tests (`app/tests/test_orchestrator.py`) that run the full journey against a scripted fake LLM, with no network and no keys.

---

## Architecture

```
Next.js 15 (dashboard/agent)  ── polls every 1s ──►  FastAPI
                                                     │
            POST /agent/run ───────────────► Orchestrator (bounded ReAct, background task)
                                                     │  LLM picks next tool → execute → observe → repeat
                                                     │  pauses at request_approval
            POST /agent/run/{id}/approve ──► send approved payload (no LLM)
                                                     │
          ┌──────────────────────┬───────────────────┼─────────────────────┐
     PostgreSQL               Redis              Crustdata API        LLM chain (OpenAI-compatible)
  opportunities,           24h cache for        person search /      Gemini Flash-Lite → Gemini Flash
  users, outreach_leads    Crustdata calls      enrich               → Groq → OpenRouter (if keys set)
```

**Key decisions**

- **An LLM-planned loop with guardrails, not free-form autonomy.** The model picks each tool from what it has seen so far: it broadens searches that return nothing, switches contact titles, or falls back to the posting's email when Crustdata finds nobody. Hard limits keep it on track: 5 tools, 10 steps, a credit budget, and a mandatory pause before sending.
- **The human decides at the point that can't be undone.** Sending is not an LLM decision. Taking it away from the model removed an LLM call and a whole class of failures.
- **One OpenAI-compatible client for every provider.** Free-tier rate limits are the main real-world failure, so the client falls through to the next provider instead of failing.
- **Runs live in memory, leads are stored in the database.** This is a single-process demo; the outreach history persists across restarts.

## Tech stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16, Redis 7, OpenAI SDK (for all LLM providers), httpx
**Frontend:** Next.js 15, React 19, TypeScript, TanStack Query
**Infra:** Docker Compose

---

## Quick start

Prerequisites: Docker, and a free Gemini key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)). A free Groq key is strongly recommended as a rate-limit fallback.

```bash
git clone https://github.com/Maherimtiyaz/career-agent.git
cd career-agent
cp backend/.env.example backend/.env           # then set GEMINI_API_KEY (+ GROQ_API_KEY)
cp frontend/.env.local.example frontend/.env.local

docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.demo_setup    # demo user + profile + seeded opportunities
```

Open **http://localhost:3000**, sign in as `demo@example.com` / `demo1234`, choose a preset goal, and click **Run agent**.

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | yes | Primary LLM |
| `GROQ_API_KEY`, `OPENROUTER_API_KEY` | recommended | Fallback LLMs when Gemini rate-limits |
| `CRUSTDATA_API_KEY` | optional | Live contact discovery |
| `CRUSTDATA_DRY_RUN` | default `true` | `true` = simulated contacts, clearly labelled in the UI; no credits spent |
| `ENCRYPTION_KEY` | optional | Fernet key for encrypting per-user API keys at rest |

## Tests

```bash
cd backend && python -m pytest app/tests -q
```

27 tests cover: the full agent journey with a scripted LLM (search, refused self-send, refused invented email, draft, approval, edited send), double-approve protection, reject, honest live-mode delivery failure, search ranking, tool contracts, the Crustdata adapter (dry-run, budget, cache) and recommendations. One cache test needs Redis running.

The live-LLM evaluation harness (`python -m app.agents.eval_harness`) runs 10 scenarios end to end. Results in [`backend/data/eval_results.md`](backend/data/eval_results.md) were recorded **before** today's changes, on the earlier 7-tool loop: 7/10 passed, and all 3 failures were Gemini free-tier 429s.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/agent/run` | Start a run (returns immediately) |
| GET | `/agent/run/{id}` | Live run state: trace, credits, pending approval |
| POST | `/agent/run/{id}/approve` | `{approved, edited_subject?, edited_body?}` |
| GET | `/agent/leads` | Outreach history |

Full OpenAPI docs at `http://localhost:8000/docs`.

## What's real, what's not (yet)

- **Real:** LLM planning and drafting, opportunity search over the seeded dataset, the Crustdata integration (live when `CRUSTDATA_DRY_RUN=false`), the approval gate, lead persistence.
- **Simulated:** email delivery. Gmail OAuth isn't wired into the agent yet, so an approved send marks the lead *sent* and says so in the UI. With `dry_run=false` the run reports a delivery failure instead of pretending.
- **Not yet built:** Gmail sending, a persistent runs table, resume upload. The dataset is a historical snapshot, so some posting links may be stale. `agent/` is an earlier standalone CLI prototype and isn't used by the app.

MIT License

