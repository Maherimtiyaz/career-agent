"""
Email finder - tries in order:
1. Hunter.io API (25/month free)
2. Apollo.io API (50/month free)
3. Prospeo.io API (75/month free)
4. Free scraper (unlimited - scrapes job page + company site)
"""
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
            "news.ycombinator.com", "github.com", "wellfound.com", "workatastartup.com"]
    if any(s in domain for s in skip):
        return None
    return domain


async def find_via_hunter(domain: str) -> str | None:
    if not HUNTER_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": HUNTER_KEY, "limit": 5},
            )
            emails = resp.json().get("data", {}).get("emails", [])
            priority = ["hr", "recruit", "talent", "people", "founder", "ceo", "cto"]
            for e in emails:
                if any(k in (e.get("position") or "").lower() for k in priority):
                    return e.get("value")
            return emails[0].get("value") if emails else None
    except Exception:
        return None


async def find_via_apollo(domain: str) -> str | None:
    if not APOLLO_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": APOLLO_KEY,
                    "q_organization_domains": domain,
                    "page": 1, "per_page": 5,
                    "person_titles": ["HR", "Recruiter", "Talent", "Founder", "CEO", "CTO"],
                },
            )
            for person in resp.json().get("people", []):
                email = person.get("email")
                if email and "@" in email and not email.endswith("@gmail.com"):
                    return email
    except Exception:
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
            emails = resp.json().get("response", {}).get("emails", [])
            priority = ["hr", "recruit", "talent", "founder", "ceo", "cto"]
            for e in emails:
                if any(k in (e.get("position") or "").lower() for k in priority):
                    return e.get("email")
            return emails[0].get("email") if emails else None
    except Exception:
        return None


async def find_via_free_scraper(job_url: str) -> str | None:
    try:
        from free_email_extractor import extract_from_job_page
        result = await extract_from_job_page(job_url)
        emails = result.get("emails", [])
        return emails[0] if emails else None
    except Exception:
        return None


async def find_email(job_url: str, company: str) -> dict:
    """Try all methods in order. Returns first email found and its source."""
    domain = extract_domain(job_url)

    if domain:
        email = await find_via_hunter(domain)
        if email:
            return {"email": email, "source": "hunter", "domain": domain}

        email = await find_via_apollo(domain)
        if email:
            return {"email": email, "source": "apollo", "domain": domain}

        email = await find_via_prospeo(domain)
        if email:
            return {"email": email, "source": "prospeo", "domain": domain}

    email = await find_via_free_scraper(job_url)
    if email:
        return {"email": email, "source": "free_scraper", "domain": domain}

    return {"email": None, "source": None, "domain": domain}