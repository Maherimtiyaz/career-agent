"""Email finder - tries Hunter.io, Apollo.io, Prospeo.io in order."""
import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

HUNTER_KEY = os.getenv("HUNTER_API_KEY", "")
APOLLO_KEY = os.getenv("APOLLO_API_KEY", "")
PROSPEO_KEY = os.getenv("PROSPEO_API_KEY", "")


def extract_domain(url: str) -> str | None:
    match = re.search(r"https?://(?:www\.)?([^/\s]+)", url)
    if not match:
        return None
    domain = match.group(1)
    skip = ["linkedin.com", "indeed.com", "naukri.com", "glassdoor.com",
            "internshala.com", "unstop.com", "devfolio.co", "ycombinator.com",
            "news.ycombinator.com", "github.com", "wellfound.com"]
    if any(s in domain for s in skip):
        return None
    return domain


async def find_via_hunter(domain: str, company: str) -> str | None:
    if not HUNTER_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": HUNTER_KEY, "limit": 5, "type": "personal"},
            )
            data = resp.json()
            emails = data.get("data", {}).get("emails", [])
            for e in emails:
                pos = (e.get("position") or "").lower()
                if any(k in pos for k in ["hr", "recruit", "talent", "people", "founder", "ceo", "cto", "engineer"]):
                    return e.get("value")
            if emails:
                return emails[0].get("value")
    except Exception:
        pass
    return None


async def find_via_apollo(domain: str, company: str) -> str | None:
    if not APOLLO_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
                json={
                    "api_key": APOLLO_KEY,
                    "q_organization_domains": domain,
                    "page": 1,
                    "per_page": 5,
                    "person_titles": ["HR", "Recruiter", "Talent", "Founder", "CEO", "CTO", "Engineering Manager"],
                },
            )
            people = resp.json().get("people", [])
            for person in people:
                email = person.get("email")
                if email and "@" in email and not email.endswith("@gmail.com"):
                    return email
    except Exception:
        pass
    return None


async def find_via_prospeo(domain: str) -> str | None:
    if not PROSPEO_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.prospeo.io/domain-search",
                headers={"X-KEY": PROSPEO_KEY},
                params={"domain": domain, "limit": 5},
            )
            data = resp.json()
            emails = data.get("response", {}).get("emails", [])
            for e in emails:
                pos = (e.get("position") or "").lower()
                if any(k in pos for k in ["hr", "recruit", "talent", "founder", "ceo", "cto"]):
                    return e.get("email")
            if emails:
                return emails[0].get("email")
    except Exception:
        pass
    return None


async def find_email(job_url: str, company: str) -> dict:
    """Try all three APIs in order. Returns email and source."""
    domain = extract_domain(job_url)
    if not domain:
        return {"email": None, "source": None, "domain": None}

    email = await find_via_hunter(domain, company)
    if email:
        return {"email": email, "source": "hunter", "domain": domain}

    email = await find_via_apollo(domain, company)
    if email:
        return {"email": email, "source": "apollo", "domain": domain}

    email = await find_via_prospeo(domain)
    if email:
        return {"email": email, "source": "prospeo", "domain": domain}

    return {"email": None, "source": None, "domain": domain}