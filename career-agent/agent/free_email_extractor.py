"""
Free email extractor - scrapes emails directly from job pages and company sites.
No API keys needed. Works best on startup job boards and company career pages.
Sources: YC startup pages, company websites, job posting pages, startup directories.
"""
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EMAIL_REGEX = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

SKIP_EMAILS = {
    "example.com", "test.com", "domain.com", "email.com",
    "yourcompany.com", "sentry.io", "wixpress.com",
    "amazonaws.com", "cloudfront.net", "githubusercontent.com",
}

PRIORITY_KEYWORDS = ["hr", "recruit", "talent", "hire", "hiring", "jobs",
                     "career", "people", "founder", "ceo", "cto", "team",
                     "hello", "hi", "contact", "info", "apply"]


def clean_emails(emails: list[str], domain: str = "") -> list[str]:
    seen = set()
    result = []
    for email in emails:
        email = email.lower().strip()
        if email in seen:
            continue
        seen.add(email)
        parts = email.split("@")
        if len(parts) != 2:
            continue
        edomain = parts[1]
        if edomain in SKIP_EMAILS:
            continue
        if edomain.endswith((".png", ".jpg", ".gif", ".css", ".js")):
            continue
        if domain and edomain == domain:
            result.insert(0, email)
        else:
            result.append(email)
    return result


def score_email(email: str) -> int:
    local = email.split("@")[0].lower()
    return sum(2 for kw in PRIORITY_KEYWORDS if kw in local)


async def scrape_page_emails(url: str, client: httpx.AsyncClient) -> list[str]:
    try:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=12)
        if resp.status_code != 200:
            return []
        text = resp.text
        emails = EMAIL_REGEX.findall(text)
        domain = urlparse(url).netloc.replace("www.", "")
        return clean_emails(emails, domain)
    except Exception:
        return []


async def find_contact_page(base_url: str, client: httpx.AsyncClient) -> str | None:
    contact_paths = ["/contact", "/contact-us", "/about", "/team",
                     "/careers", "/jobs", "/hire", "/about-us", "/company"]
    domain = urlparse(base_url).scheme + "://" + urlparse(base_url).netloc
    for path in contact_paths:
        try:
            url = domain + path
            resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=8)
            if resp.status_code == 200:
                return url
        except Exception:
            continue
    return None


async def extract_from_job_page(job_url: str) -> dict:
    """Main function - extracts emails from a job posting URL."""
    result = {"emails": [], "source": None, "tried": []}

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        result["tried"].append(job_url)
        emails = await scrape_page_emails(job_url, client)

        if emails:
            result["emails"] = sorted(emails, key=score_email, reverse=True)
            result["source"] = "job_page"
            return result

        parsed = urlparse(job_url)
        base = parsed.scheme + "://" + parsed.netloc
        if base != job_url:
            result["tried"].append(base)
            emails = await scrape_page_emails(base, client)
            if emails:
                result["emails"] = sorted(emails, key=score_email, reverse=True)
                result["source"] = "company_homepage"
                return result

        contact = await find_contact_page(base, client)
        if contact:
            result["tried"].append(contact)
            emails = await scrape_page_emails(contact, client)
            if emails:
                result["emails"] = sorted(emails, key=score_email, reverse=True)
                result["source"] = "contact_page"
                return result

    return result


async def scrape_yc_startups(limit: int = 50) -> list[dict]:
    """
    Scrape YC startup directory for companies hiring.
    Returns list of {company, url, emails}.
    """
    results = []
    urls_to_try = [
        "https://www.ycombinator.com/companies?batch=W24&batch=S24&batch=W23&isHiring=true",
        "https://www.workatastartup.com/jobs?role=eng&jobType=intern",
        "https://www.workatastartup.com/jobs?role=eng&remote=true",
    ]

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for url in urls_to_try:
            try:
                resp = await client.get(url, headers=HEADERS)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")

                company_links = set()
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "ycombinator.com/companies/" in href or "workatastartup.com/companies/" in href:
                        if href.startswith("http"):
                            company_links.add(href)
                        else:
                            company_links.add(urljoin(url, href))

                for link in list(company_links)[:20]:
                    try:
                        resp2 = await client.get(link, headers=HEADERS)
                        if resp2.status_code != 200:
                            continue
                        soup2 = BeautifulSoup(resp2.text, "html.parser")

                        company_name = ""
                        for tag in ["h1", "h2"]:
                            el = soup2.find(tag)
                            if el:
                                company_name = el.get_text(strip=True)
                                break

                        website_link = None
                        for a in soup2.find_all("a", href=True):
                            href = a["href"]
                            if href.startswith("http") and "ycombinator.com" not in href and "workatastartup.com" not in href:
                                text = a.get_text(strip=True).lower()
                                if any(k in text for k in ["website", "visit", "company", company_name.lower()[:5]]):
                                    website_link = href
                                    break

                        emails = EMAIL_REGEX.findall(resp2.text)
                        domain = ""
                        if website_link:
                            domain = urlparse(website_link).netloc.replace("www.", "")

                        cleaned = clean_emails(emails, domain)
                        if cleaned:
                            results.append({
                                "company": company_name or link.split("/")[-1],
                                "url": website_link or link,
                                "yc_url": link,
                                "emails": sorted(cleaned, key=score_email, reverse=True),
                            })
                    except Exception:
                        continue

                    await asyncio.sleep(0.5)

                if len(results) >= limit:
                    break

            except Exception:
                continue

    return results[:limit]


async def scrape_startup_job_boards() -> list[dict]:
    """
    Scrape startup-focused job boards that expose emails.
    """
    results = []
    sources = [
        {
            "url": "https://remoteok.com/remote-intern+jobs",
            "name": "RemoteOK",
        },
        {
            "url": "https://remoteok.com/remote-dev+jobs?location=worldwide",
            "name": "RemoteOK Dev",
        },
    ]

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for source in sources:
            try:
                resp = await client.get(source["url"], headers=HEADERS)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")

                emails = EMAIL_REGEX.findall(resp.text)
                cleaned = clean_emails(emails)

                job_links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "/remote-jobs/" in href or "/job/" in href:
                        full = urljoin(source["url"], href)
                        if full not in job_links:
                            job_links.append(full)

                for link in job_links[:15]:
                    page_emails = await scrape_page_emails(link, client)
                    if page_emails:
                        results.append({
                            "company": link.split("/")[-1].replace("-", " ").title(),
                            "url": link,
                            "emails": page_emails,
                            "source": source["name"],
                        })
                    await asyncio.sleep(0.3)

            except Exception:
                continue

    return results


async def run_free_extractor(job_url: str = "", mode: str = "url") -> list[dict]:
    """
    Main entry point.
    mode="url": extract from a specific job URL
    mode="yc": scrape YC startups
    mode="boards": scrape startup job boards
    """
    if mode == "url" and job_url:
        result = await extract_from_job_page(job_url)
        return [{"url": job_url, "emails": result["emails"], "source": result["source"]}]

    elif mode == "yc":
        return await scrape_yc_startups(limit=30)

    elif mode == "boards":
        return await scrape_startup_job_boards()

    return []