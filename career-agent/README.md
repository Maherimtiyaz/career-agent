# Career Agent v6 — Autonomous Career OS

Milestone 1 (this scaffold): infrastructure only. No auth, ingestion, CRM,
embeddings, or ranking yet — those are later milestones, built and verified
one at a time on top of this foundation.

## Stack
- Backend: FastAPI (async), SQLAlchemy 2.x, PostgreSQL, Redis, Alembic
- Frontend: Next.js 15 (App Router), React 19, TypeScript, Tailwind
- Infra: Docker Compose, Nginx reverse proxy

## Run it

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
docker compose up --build
```

- Frontend: http://localhost:3000 (also proxied at http://localhost/)
- Backend docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health
- DB health (confirms Postgres connection): http://localhost:8000/health/db

## Verify Milestone 1

```bash
docker compose ps                 # all 5 services should be "running (healthy)"
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost/            # via nginx -> frontend
curl http://localhost/api/health  # via nginx -> backend
```

## Next milestones (not started)
1. Alembic + first migration (users table)
2. JWT auth (access + refresh tokens, Argon2 hashing)
3. `opportunities` + `applications` tables
4. Manual Google Sheet import (personal tracker, CSV export endpoint, no OAuth)
5. Platform ingestion (GitHub, GSoC, MLH, YC Jobs, Devfolio, HackerEarth, Unstop)
6. CRM / outreach tracking
7. Analytics dashboard
8. Embeddings + ranking engine (last, per original spec)
