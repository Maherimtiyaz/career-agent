"""Fetch opportunities from Career Agent API + fresh scrape + find emails."""
import asyncio
import os
import re
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from email_finder import find_email

load_dotenv()

API_BASE = os.getenv("CAREER_AGENT_API", "http://localhost:8000")
EMAIL = os.getenv("CAREER_AGENT_EMAIL", "")
PASSWORD = os.getenv("CAREER_AGENT_PASSWORD", "")
SKILLS = [s.strip().lower() for s in os.getenv("SENDER_SKILLS", "python,fastapi").split(",")]


async def get_token() -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        return resp.json()["access_token"]


def extract_email_from_text(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text or "")
    return match.group(0) if match else None


def extract_email_from_tags(tags: str) -> str | None:
    match = re.search(r"email:([\w.+-]+@[\w-]+\.[a-zA-Z]{2,})", tags or "")
    return match.group(1) if match else None


def score(opp: dict) -> int:
    text = " ".join(filter(None, [
        opp.get("title", ""), opp.get("organization", ""),
        opp.get("tags", ""), opp.get("description", "")
    ])).lower()
    base = sum(1 for kw in SKILLS if kw in text)
    base += 3 if opp.get("stipend") else 0
    base += 2 if opp.get("is_remote") else 0
    base += 3 if opp.get("source") == "curated" else 0
    return base


async def fetch_from_api(token: str, limit: int = 200) -> list[dict]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{API_BASE}/opportunities?limit={limit}",
            headers={"Authorization": f"Bearer {token}"}
        )
        return resp.json()


async def fetch_fresh_yc() -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search?query=who+is+hiring&tags=story&hitsPerPage=1"
            )
            hits = resp.json().get("hits", [])
            if not hits:
                return []
            thread_id = hits[0]["objectID"]
            resp2 = await client.get(
                f"https://hn.algolia.com/api/v1/search?tags=comment,story_{thread_id}&hitsPerPage=200"
            )
            for comment in resp2.json().get("hits", []):
                text = comment.get("comment_text", "") or ""
                if len(text) < 50:
                    continue
                soup = BeautifulSoup(text, "html.parser")
                plain = soup.get_text(" ", strip=True)
                if not any(kw in plain.lower() for kw in ["intern", "remote", "python", "backend", "api"]):
                    continue
                lines = [l.strip() for l in plain.split("|") if l.strip()]
                title = lines[0][:150] if lines else "Job Opportunity"
                results.append({
                    "id": f"yc_{comment.get('objectID', '')}",
                    "title": title,
                    "organization": "YC Startup",
                    "description": plain[:400],
                    "url": f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}",
                    "source": "yc_fresh",
                    "is_remote": "remote" in plain.lower(),
                    "stipend": None,
                    "tags": "Internship" if "intern" in plain.lower() else "Remote",
                })
        except Exception:
            pass
    return results


async def enrich_with_email(opp: dict) -> dict:
    """Find email from text first, then fall back to API lookup."""
    email = extract_email_from_text(opp.get("description", ""))
    if not email:
        email = extract_email_from_tags(opp.get("tags", ""))
    if email:
        opp["hr_email"] = email
        opp["email_source"] = "embedded"
        return opp

    url = opp.get("url", "")
    if url and "http" in url:
        result = await find_email(url, opp.get("organization", ""))
        if result["email"]:
            opp["hr_email"] = result["email"]
            opp["email_source"] = result["source"]
            return opp

    opp["hr_email"] = None
    opp["email_source"] = None
    return opp


async def get_todays_targets(max_count: int = 30) -> tuple[list[dict], list[dict]]:
    """Returns (targets_with_email, needs_manual_apply)."""
    token = await get_token()
    api_opps = await fetch_from_api(token, limit=200)
    fresh_opps = await fetch_fresh_yc()

    all_opps = api_opps + fresh_opps
    for opp in all_opps:
        opp["_score"] = score(opp)

    all_opps.sort(key=lambda x: x["_score"], reverse=True)
    top = all_opps[:max_count * 2]

    print(f"  Enriching {len(top)} opportunities with emails (API calls)...")
    enriched = await asyncio.gather(*[enrich_with_email(opp) for opp in top])

    has_email = [o for o in enriched if o.get("hr_email")]
    no_email = [o for o in enriched if not o.get("hr_email")]

    return has_email[:max_count], no_email[:10]