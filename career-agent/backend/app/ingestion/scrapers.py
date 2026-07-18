"""Live platform scrapers - GSoC, YC Jobs (HN), MLH Fellowship."""

import hashlib
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity


def _hash(title: str, org: str, url: str) -> str:
    key = f"{title.strip().lower()}:{org.strip().lower()}:{url.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:64]


async def _upsert(session: AsyncSession, opp: Opportunity) -> bool:
    exists = (await session.execute(
        select(Opportunity).where(Opportunity.source_id == opp.source_id)
    )).first()
    if exists:
        return False
    session.add(opp)
    return True


async def scrape_gsoc(session: AsyncSession) -> dict:
    """Fetch GSoC organizations from the public API."""
    inserted = 0
    url = "https://summerofcode.withgoogle.com/api/program/2024/organizations/?limit=100"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"source": "gsoc", "inserted": 0, "error": f"status {resp.status_code}"}
            data = resp.json()
        except Exception as e:
            return {"source": "gsoc", "inserted": 0, "error": str(e)}

    orgs = data if isinstance(data, list) else data.get("results", [])
    for org in orgs:
        name = org.get("name", "").strip()
        slug = org.get("slug", "")
        desc = org.get("description", "").strip()
        tech = ", ".join(org.get("technologies", [])[:5])
        opp_url = f"https://summerofcode.withgoogle.com/programs/2024/organizations/{slug}"
        sid = _hash(f"GSoC 2024 - {name}", "Google Summer of Code", opp_url)
        opp = Opportunity(
            title=f"GSoC 2024 - {name}",
            organization="Google Summer of Code",
            description=desc[:500] if desc else None,
            url=opp_url,
            source="gsoc",
            is_remote=True,
            stipend="-",
            deadline="April 2024",
            tags=f"Open Source,Fellowship,{tech}" if tech else "Open Source,Fellowship",
            source_id=sid,
        )
        if await _upsert(session, opp):
            inserted += 1

    await session.commit()
    return {"source": "gsoc", "inserted": inserted}


async def scrape_ycombinator(session: AsyncSession) -> dict:
    """Fetch jobs from HN Who's Hiring via Algolia API."""
    inserted = 0
    url = "https://hn.algolia.com/api/v1/search?query=who+is+hiring&tags=story&hitsPerPage=1"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"source": "yc_jobs", "inserted": 0, "error": f"status {resp.status_code}"}
            data = resp.json()
            hits = data.get("hits", [])
            if not hits:
                return {"source": "yc_jobs", "inserted": 0, "error": "no hiring thread found"}

            thread_id = hits[0]["objectID"]
            comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{thread_id}&hitsPerPage=100"
            resp2 = await client.get(comments_url)
            if resp2.status_code != 200:
                return {"source": "yc_jobs", "inserted": 0, "error": "could not fetch comments"}
            comments = resp2.json().get("hits", [])
        except Exception as e:
            return {"source": "yc_jobs", "inserted": 0, "error": str(e)}

    for comment in comments:
        text = comment.get("comment_text", "") or ""
        if not text or len(text) < 50:
            continue
        soup = BeautifulSoup(text, "html.parser")
        plain = soup.get_text(" ", strip=True)
        lines = [l.strip() for l in plain.split("|") if l.strip()]
        if not lines:
            continue

        title_line = lines[0][:200]
        is_remote = "remote" in plain.lower()
        is_intern = any(w in plain.lower() for w in ["intern", "student", "entry level", "junior"])
        if not is_intern and not is_remote:
            continue

        comment_url = f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}"
        sid = _hash(title_line, "YC Who's Hiring", comment_url)
        opp = Opportunity(
            title=title_line,
            organization="YC Who's Hiring",
            description=plain[:400],
            url=comment_url,
            source="yc_jobs",
            is_remote=is_remote,
            tags="Intern" if is_intern else "Remote",
            source_id=sid,
        )
        if await _upsert(session, opp):
            inserted += 1

    await session.commit()
    return {"source": "yc_jobs", "inserted": inserted}


async def scrape_mlh(session: AsyncSession) -> dict:
    """Scrape MLH Fellowship page."""
    inserted = 0
    url = "https://fellowship.mlh.io/"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0"}) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"source": "mlh", "inserted": 0, "error": f"status {resp.status_code}"}
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            return {"source": "mlh", "inserted": 0, "error": str(e)}

    programs = [
        {"title": "MLH Fellowship - Explorer", "tags": "Fellowship,Open Source,Beginner"},
        {"title": "MLH Fellowship - Open Source", "tags": "Fellowship,Open Source"},
        {"title": "MLH Fellowship - Production Engineering", "tags": "Fellowship,SRE,DevOps"},
    ]
    for prog in programs:
        sid = _hash(prog["title"], "Major League Hacking", url)
        opp = Opportunity(
            title=prog["title"],
            organization="Major League Hacking",
            description="12-week fellowship for students. Work on real open source projects with mentors from top tech companies.",
            url=url,
            source="mlh",
            is_remote=True,
            stipend="",
            tags=prog["tags"],
            source_id=sid,
        )
        if await _upsert(session, opp):
            inserted += 1

    await session.commit()
    return {"source": "mlh", "inserted": inserted}


async def scrape_devfolio(session: AsyncSession) -> dict:
    """Fetch hackathons from Devfolio public API."""
    inserted = 0
    url = "https://api.devfolio.co/api/hackathons?type=online&page=1&per_page=20"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0"}) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"source": "devfolio", "inserted": 0, "error": f"status {resp.status_code}"}
            data = resp.json()
        except Exception as e:
            return {"source": "devfolio", "inserted": 0, "error": str(e)}

    hackathons = data if isinstance(data, list) else data.get("hackathons", data.get("results", []))
    for h in hackathons:
        name = (h.get("name") or h.get("title") or "").strip()
        slug = h.get("slug", "")
        if not name:
            continue
        opp_url = f"https://devfolio.co/hackathons/{slug}" if slug else "https://devfolio.co"
        sid = _hash(name, "Devfolio", opp_url)
        opp = Opportunity(
            title=name,
            organization="Devfolio",
            description=(h.get("tagline") or h.get("description") or "")[:400] or None,
            url=opp_url,
            source="devfolio",
            is_remote=True,
            tags="Hackathon,Student",
            source_id=sid,
        )
        if await _upsert(session, opp):
            inserted += 1

    await session.commit()
    return {"source": "devfolio", "inserted": inserted}


SCRAPERS = {
    "gsoc": scrape_gsoc,
    "yc_jobs": scrape_ycombinator,
    "mlh": scrape_mlh,
    "devfolio": scrape_devfolio,
}
