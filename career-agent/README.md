# Career Agent v6 — Autonomous Career OS

> An open-source AI-powered career operating system built for students. Browse 2000+ opportunities, track applications, get AI-matched picks, and import from Google Sheets — all in one dark, fast dashboard.

**Built by a student, for students. Free and open source forever.**

---

## What it does

- **Browse 2400+ opportunities** — remote jobs, internships, fellowships, GSoC orgs, YC startup jobs, MLH programs, Devfolio hackathons
- **One-click apply tracking** — Save or mark Applied directly from any opportunity card
- **AI Picks** — keyword-scored recommendations matched to your skills and target roles
- **Application tracker** — table view with status updates (Applied → Interviewing → Offer/Rejected)
- **Google Sheet import** — paste a public Sheet URL, sync your personal tracker instantly
- **Analytics dashboard** — charts for application status, opportunities by source, activity over time
- **Live scrapers** — GSoC, YC Jobs, MLH Fellowship, Devfolio — auto-refreshed every 24h
- **Profile page** — set skills, target roles, bio, GitHub/LinkedIn links
- **Dark UI** — Linear/Raycast-inspired design

---

## Tech Stack

### Backend
- Python 3.12 + FastAPI (async)
- PostgreSQL 16 + SQLAlchemy 2.x + Alembic
- Argon2 password hashing + JWT auth (access + refresh tokens)
- APScheduler — daily auto-scraping
- HTTPX + BeautifulSoup4 — scrapers
- Redis — caching layer

### Frontend
- Next.js 15 (App Router) + React 19 + TypeScript
- TanStack Query — server state
- Recharts — analytics charts
- Tailwind CSS + CSS variables (dark theme)
- Axios — typed API client

### Infrastructure
- Docker Compose — one command to run everything
- Nginx — reverse proxy
- 5 containers: backend, frontend, postgres, redis, nginx

---

## Quickstart

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git

### 1. Clone
```bash
git clone https://github.com/Maherimtiyaz/career-agent.git
cd career-agent/career-agent
```

### 2. Configure
```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

The defaults work for local development. Change `JWT_SECRET_KEY` before production.

### 3. Run
```bash
docker compose up --build
```

First build takes ~5 minutes.

### 4. Access

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |
| Via Nginx | http://localhost |

### 5. Seed opportunities
```bash
docker compose exec backend python -m app.ingestion.seed_opportunities
```

### 6. Run migrations (after pulling updates)
```bash
docker compose exec backend alembic upgrade head
```

---

## Project Structure
career-agent/
├── backend/
│ ├── app/
│ │ ├── api/ # FastAPI routers
│ │ ├── auth/ # JWT dependencies
│ │ ├── core/ # Config, logging, security
│ │ ├── crud/ # Database access layer
│ │ ├── db/ # SQLAlchemy engine + base
│ │ ├── ingestion/ # Scrapers + Sheet importer + Seeder
│ │ ├── models/ # ORM models
│ │ ├── schemas/ # Pydantic schemas
│ │ ├── scheduler/ # APScheduler jobs
│ │ └── main.py
│ ├── alembic/ # Migrations
│ ├── data/ # Local seed files (not committed)
│ └── Dockerfile
├── frontend/
│ ├── app/dashboard/ # All dashboard pages
│ ├── lib/ # API client + auth helpers
│ ├── types/ # TypeScript types
│ └── Dockerfile
├── nginx/nginx.conf
└── docker-compose.yml
---

## API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register |
| POST | `/auth/login` | No | Login, get tokens |
| POST | `/auth/refresh` | No | Refresh token |
| GET | `/auth/me` | Yes | Current user |
| PATCH | `/auth/me` | Yes | Update profile |
| GET | `/opportunities` | No | List/search (supports ?search=, ?source=, ?is_remote=) |
| POST | `/applications` | Yes | Track application |
| PATCH | `/applications/{id}` | Yes | Update status |
| DELETE | `/applications/{id}` | Yes | Remove |
| GET | `/ai/recommendations` | Yes | AI-scored picks |
| GET | `/analytics/summary` | Yes | Full analytics |
| POST | `/ingestion/run` | Yes | Trigger scrapers (?source=all) |
| POST | `/sheet/import` | Yes | Import Google Sheet |
| GET | `/health` | No | Liveness |
| GET | `/health/db` | No | DB check |

Full docs at `http://localhost:8000/docs`

---

## Google Sheet Import

Sheet must be shared as **Anyone with the link can view**.

Required columns: `company`, `role`

Optional: `job_link`, `hr_contact`, `status`, `date_applied`, `notes`

Status values: `applied`, `interviewing`, `offer`, `rejected`, `saved`

---

## Platform Scrapers

| Source | Type | Method |
|---|---|---|
| GSoC | Open Source Fellowships | Public JSON API |
| YC Who is Hiring | Startup jobs | HN Algolia API |
| MLH Fellowship | Student programs | Curated |
| Devfolio | Hackathons | Public API |

Scrapers run every 24h automatically. Trigger manually from Dashboard → Data Sources → Refresh Now.

---

## Environment Variables

### backend/.env

| Variable | Default | Notes |
|---|---|---|
| DATABASE_URL | postgresql+asyncpg://careeruser:careerpass@db:5432/careerdb | |
| REDIS_URL | redis://redis:6379/0 | |
| JWT_SECRET_KEY | change-this-in-production | Change before deploying |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 30 | |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | 7 | |
| CORS_ORIGINS | http://localhost:3000,http://localhost | |

### frontend/.env.local

| Variable | Default | |
|---|---|---|
| NEXT_PUBLIC_API_URL | http://localhost:8000 | |

---

## Contributing

Contributions are very welcome. This is built for students.

**Good first issues:**
- Add scrapers: Unstop, HackerEarth, Internshala, LinkedIn
- Add email alerts for new matched opportunities
- Improve AI with sentence-transformers embeddings
- Resume upload + skill extraction
- Mobile responsive improvements
- Dark/light mode toggle
- Export applications to CSV

**Steps:**
1. Fork the repo
2. `git checkout -b feat/your-feature`
3. Make changes, test with `docker compose up --build`
4. If models changed: `docker compose exec backend alembic revision --autogenerate -m "description"`
5. Open a PR

---

## Roadmap

- [ ] Semantic AI ranking with embeddings
- [ ] Resume upload and skill extraction
- [ ] Email alerts for matched opportunities
- [ ] Unstop / HackerEarth / Internshala scrapers
- [ ] Mobile responsive UI
- [ ] Dark/light mode toggle
- [ ] Email verification
- [ ] Export to CSV
- [ ] Outreach CRM (track HR emails, follow-ups)

---

## License

MIT

---

Built with love by [Mahek Imtiyaz](https://github.com/Maherimtiyaz) · BCA student at Vivekananda Global University, Jaipur