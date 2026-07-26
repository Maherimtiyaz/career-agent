"""
Free email extractor - no API key limits.
Sources:
1. GitHub org pages (founders often list emails)
2. Direct job page scraping (works on your machine, not datacenter IPs)
3. Company contact/about pages
4. GitHub README scraping for hiring repos
"""
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

HEADERS_BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

HEADERS_GITHUB = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "career-agent",
}
if GITHUB_TOKEN:
    HEADERS_GITHUB["Authorization"] = f"Bearer {GITHUB_TOKEN}"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

SKIP_DOMAINS = {
    "example.com", "test.com", "domain.com", "sentry.io",
    "wixpress.com", "amazonaws.com", "cloudfront.net",
    "githubusercontent.com", "noreply.github.com",
    "png", "jpg", "gif", "css", "js",
}

PRIORITY = ["hr", "recruit", "talent", "hire", "hiring", "jobs",
            "career", "people", "founder", "ceo", "cto", "hello",
            "contact", "info", "apply", "team", "work"]


def clean_emails(raw: list[str], prefer_domain: str = "") -> list[str]:
    seen, result = set(), []
    for e in raw:
        e = e.lower().strip().rstrip(".")
        if e in seen:
            continue
        seen.add(e)
        parts = e.split("@")
        if len(parts) != 2:
            continue
        domain = parts[1]
        if any(domain.endswith(s) for s in SKIP_DOMAINS):
            continue
        if len(parts[0]) < 2 or len(domain) < 4:
            continue
        result.append(e)
    priority = [e for e in result if any(k in e.split("@")[0] for k in PRIORITY)]
    rest = [e for e in result if e not in priority]
    if prefer_domain:
        priority = sorted(priority, key=lambda e: 0 if prefer_domain in e else 1)
        rest = sorted(rest, key=lambda e: 0 if prefer_domain in e else 1)
    return priority + rest


async def scrape_url(url: str, client: httpx.AsyncClient) -> list[str]:
    try:
        resp = await client.get(url, headers=HEADERS_BROWSER, follow_redirects=True, timeout=12)
        if resp.status_code != 200:
            return []
        domain = urlparse(url).netloc.replace("www.", "")
        return clean_emails(EMAIL_RE.findall(resp.text), domain)
    except Exception:
        return []


async def find_contact_urls(base_url: str, client: httpx.AsyncClient) -> list[str]:
    domain = urlparse(base_url).scheme + "://" + urlparse(base_url).netloc
    paths = ["/contact", "/contact-us", "/about", "/team", "/careers",
             "/jobs", "/hire", "/about-us", "/company", "/work-with-us"]
    found = []
    for path in paths:
        try:
            url = domain + path
            resp = await client.get(url, headers=HEADERS_BROWSER, follow_redirects=True, timeout=8)
            if resp.status_code == 200 and len(resp.text) > 500:
                found.append(url)
                if len(found) >= 2:
                    break
        except Exception:
            continue
    return found


async def extract_from_job_page(job_url: str) -> dict:
    tried = []
    async with httpx.AsyncClient(timeout=15) as client:
        tried.append(job_url)
        emails = await scrape_url(job_url, client)
        if emails:
            return {"emails": emails, "source": "job_page", "tried": tried}

        parsed = urlparse(job_url)
        base = parsed.scheme + "://" + parsed.netloc
        if base != job_url:
            tried.append(base)
            emails = await scrape_url(base, client)
            if emails:
                return {"emails": emails, "source": "homepage", "tried": tried}

        contact_urls = await find_contact_urls(base, client)
        for curl in contact_urls:
            tried.append(curl)
            emails = await scrape_url(curl, client)
            if emails:
                return {"emails": emails, "source": "contact_page", "tried": tried}

    return {"emails": [], "source": None, "tried": tried}


async def search_github_for_hiring(query: str = "python backend intern hiring 2026", limit: int = 20) -> list[dict]:
    """Search GitHub repos and READMEs for hiring notices with contact emails."""
    results = []
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                headers=HEADERS_GITHUB,
                params={"q": query, "sort": "updated", "per_page": limit},
            )
            if resp.status_code != 200:
                print(f"GitHub API: {resp.status_code}")
                return []

            items = resp.json().get("items", [])
            for item in items:
                full_name = item["full_name"]
                company = item.get("organization", {})
                if isinstance(company, dict):
                    company = company.get("login", full_name.split("/")[0])

                readme_resp = await client.get(
                    f"https://api.github.com/repos/{full_name}/readme",
                    headers={**HEADERS_GITHUB, "Accept": "application/vnd.github.v3.raw"},
                )
                if readme_resp.status_code != 200:
                    continue

                emails = clean_emails(EMAIL_RE.findall(readme_resp.text))
                if emails:
                    results.append({
                        "company": company,
                        "url": item["html_url"],
                        "emails": emails[:3],
                        "source": "github_readme",
                    })

                await asyncio.sleep(0.2)

        except Exception as e:
            print(f"GitHub search error: {e}")

    return results


async def scrape_startup_sources() -> list[dict]:
    """Scrape startup sources that work from residential IPs."""
    results = []
    sources = [
        {
            "name": "IndieHackers",
            "url": "https://www.indiehackers.com/jobs",
        },
        {
            "name": "HackerNews Jobs",
            "url": "https://news.ycombinator.com/jobs",
        },
        {
            "name": "GitHub Hiring",
            "url": "https://github.com/trending",
        },
        {
            "name": "AngelList",
            "url": "https://angel.co/jobs",
        },
    ]

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for source in sources:
            try:
                resp = await client.get(source["url"], headers=HEADERS_BROWSER)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                emails = clean_emails(EMAIL_RE.findall(resp.text))

                job_links = set()
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(k in href for k in ["/job/", "/jobs/", "/careers/", "/hiring"]):
                        full = urljoin(source["url"], href)
                        if full.startswith("http"):
                            job_links.add(full)

                for link in list(job_links)[:10]:
                    page_emails = await scrape_url(link, client)
                    if page_emails:
                        results.append({
                            "company": link.split("/")[-2] or source["name"],
                            "url": link,
                            "emails": page_emails[:3],
                            "source": source["name"],
                        })
                    await asyncio.sleep(0.3)

                if emails:
                    results.append({
                        "company": source["name"],
                        "url": source["url"],
                        "emails": emails[:5],
                        "source": source["name"],
                    })

            except Exception:
                continue

    return results


async def run_free_extractor(job_url: str = "", mode: str = "github") -> list[dict]:
    if mode == "url" and job_url:
        result = await extract_from_job_page(job_url)
        return [{"url": job_url, "emails": result["emails"], "source": result["source"]}]
    elif mode == "github":
        return await search_github_for_hiring()
    elif mode == "boards":
        return await scrape_startup_sources()
    return []