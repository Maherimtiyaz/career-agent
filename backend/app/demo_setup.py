"""One-command demo setup: demo user with a complete profile + seeded opportunities.

    docker compose exec backend python -m app.demo_setup

Idempotent: re-running refreshes the demo profile and skips seeding when
opportunities already exist.
"""
import asyncio

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.opportunity import Opportunity
from app.models.user import User

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"
DEMO_PROFILE = {
    "full_name": "Alex Rivera",
    "college": "State University, B.S. Computer Science",
    "graduation_year": "2027",
    "skills": "Python, PyTorch, scikit-learn, FastAPI, SQL, Docker",
    "target_roles": "Machine learning internship, backend engineering internship",
    "bio": (
        "CS junior who built a retrieval-augmented study assistant used by 300 "
        "classmates and fine-tuned a small vision model for crop-disease detection."
    ),
    "location": "Remote",
    "github_url": "https://github.com/alex-rivera-demo",
}


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one_or_none()
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                is_active=True,
                is_verified=True,
            )
            db.add(user)
        for key, value in DEMO_PROFILE.items():
            setattr(user, key, value)
        await db.commit()
        print(f"Demo user ready: {DEMO_EMAIL} / {DEMO_PASSWORD}")

        count = (await db.execute(select(func.count()).select_from(Opportunity))).scalar_one()
    if count:
        print(f"{count} opportunities already in the database — skipping seed.")
        return

    from app.ingestion import seed_opportunities

    try:
        await seed_opportunities.main()
    except Exception as exc:  # e.g. the optional Google Sheet is unreachable offline
        print(f"Seeding finished with a warning: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
