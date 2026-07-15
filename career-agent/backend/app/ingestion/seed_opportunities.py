"""Seed script - loads local data files into the opportunities table.
Run with: docker compose exec backend python -m app.ingestion.seed_opportunities
"""
import asyncio
import csv
import hashlib
import io
import os
import sys

import httpx
import pandas as pd
from sqlalchemy import select

sys.path.insert(0, "/app")
from app.db.session import AsyncSessionLocal
from app.models.opportunity import Opportunity

DATA_DIR = "/app/data"


def _hash(title: str, org: str, url: str) -> str:
    key = f"{title.strip().lower()}:{org.strip().lower()}:{url.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:64]


async def _exists(session, sid):
    return (await session.execute(select(Opportunity).where(Opportunity.source_id == sid))).first()


async def seed_from_excel(session, filepath, source):
    print(f"Loading {os.path.basename(filepath)}...")
    df = pd.read_excel(filepath)
    inserted = skipped = 0
    for _, row in df.iterrows():
        title = str(row.get("Position", "")).strip()
        org = str(row.get("Company", "")).strip()
        url = str(row.get("Job Link", "")).strip()
        if not title or not org or url == "nan":
            skipped += 1
            continue
        sid = _hash(title, org, url)
        if await _exists(session, sid):
            skipped += 1
            continue
        level = str(row.get("Level", "")).strip()
        remote = str(row.get("Remote?", "")).strip()
        comp = str(row.get("Compensation", "")).strip()
        loc = str(row.get("Location", "")).strip()
        email = str(row.get("Application Email", "")).strip()
        tags = ",".join(x for x in [level if level != "nan" else "", f"email:{email}" if email and email != "nan" else ""] if x) or None
        session.add(Opportunity(
            title=title, organization=org,
            url=url if url.startswith("http") else f"https://{url}",
            source=source,
            location=loc if loc != "nan" else None,
            is_remote=remote.lower() == "yes",
            stipend=comp if comp != "nan" else None,
            tags=tags, source_id=sid,
        ))
        inserted += 1
    await session.commit()
    print(f"[{source}] inserted={inserted} skipped={skipped}")


async def seed_from_csv(session, filepath, source):
    print(f"Loading {os.path.basename(filepath)}...")
    df = pd.read_csv(filepath)
    inserted = skipped = 0
    for _, row in df.iterrows():
        title = str(row.get("Position", "")).strip()
        org = str(row.get("Company", "")).strip()
        url = str(row.get("Job Link", "")).strip()
        if not title or not org or url == "nan":
            skipped += 1
            continue
        sid = _hash(title, org, url)
        if await _exists(session, sid):
            skipped += 1
            continue
        email = str(row.get("Application Email", "")).strip()
        level = str(row.get("Level", "")).strip()
        tags = ",".join(x for x in [level if level != "nan" else "", f"email:{email}" if email and email != "nan" else ""] if x) or None
        session.add(Opportunity(
            title=title, organization=org,
            url=url if url.startswith("http") else f"https://{url}",
            source=source, is_remote=True, tags=tags, source_id=sid,
        ))
        inserted += 1
    await session.commit()
    print(f"[{source}] inserted={inserted} skipped={skipped}")


async def seed_from_curated_csv(session, filepath, source):
    print(f"Loading {os.path.basename(filepath)}...")
    inserted = skipped = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("Name") or row.get("Opportunity Name") or "").strip()
            org = (row.get("Organizing Institution/Company/University") or row.get("Organization") or row.get("Organizer") or "").strip()
            url = (row.get("Link to Apply or Official Source") or row.get("Official Link") or row.get("How to Find / Source") or "").strip()
            if not title or not org or not url:
                skipped += 1
                continue
            sid = _hash(title, org, url)
            if await _exists(session, sid):
                skipped += 1
                continue
            deadline = (row.get("Application Start & Deadline Dates (2026)") or row.get("2026 Deadline Estimate") or row.get("Deadline Estimate & Notes") or "").strip()
            benefits = (row.get("Benefits") or row.get("Key Benefits") or "").strip()
            opp_type = (row.get("Type") or "").strip()
            mode = (row.get("Mode") or "").strip()
            location = (row.get("Location") or "").strip()
            session.add(Opportunity(
                title=title, organization=org,
                description=benefits or None, url=url, source=source,
                location=location or None,
                is_remote="remote" in mode.lower() or "virtual" in mode.lower(),
                deadline=deadline or None, tags=opp_type or None, source_id=sid,
            ))
            inserted += 1
    await session.commit()
    print(f"[curated:{os.path.basename(filepath)}] inserted={inserted} skipped={skipped}")


async def seed_from_google_sheet(session, sheet_url, source):
    print(f"Fetching Google Sheet...")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(sheet_url)
        if resp.status_code != 200:
            print(f"SKIP: status {resp.status_code}")
            return
    reader = csv.DictReader(io.StringIO(resp.text))
    inserted = skipped = 0
    for row in reader:
        title = (row.get("Position") or row.get("Role") or row.get("Title") or row.get("Job Title") or "").strip()
        org = (row.get("Company") or row.get("Organization") or row.get("Employer") or "").strip()
        url_val = (row.get("Job Link") or row.get("Link") or row.get("URL") or "").strip()
        if not title or not org:
            skipped += 1
            continue
        sid = _hash(title, org, url_val or title)
        if await _exists(session, sid):
            skipped += 1
            continue
        session.add(Opportunity(title=title, organization=org, url=url_val or "", source=source, is_remote=True, source_id=sid))
        inserted += 1
    await session.commit()
    print(f"[{source}] inserted={inserted} skipped={skipped}")


async def main():
    async with AsyncSessionLocal() as session:
        files = sorted(os.listdir(DATA_DIR)) if os.path.exists(DATA_DIR) else []
        print(f"Found {len(files)} files in /app/data")

        curated_files = ["deepseek_csv_20260112_4e4575.txt", "deepseek_csv_20260112_565406.txt", "deepseek_csv_20260112_fefcd2.txt"]

        for fname in files:
            fpath = os.path.join(DATA_DIR, fname)
            if fname.endswith(".xlsx"):
                await seed_from_excel(session, fpath, source="remote_jobs")
            elif fname == "filtered_tech_jobs_with_emails.csv":
                await seed_from_csv(session, fpath, source="tech_jobs")
            elif fname in curated_files:
                await seed_from_curated_csv(session, fpath, source="curated")

        await seed_from_google_sheet(
            session,
            "https://docs.google.com/spreadsheets/d/18bljq3y5YTxPLmA4xj10EaKxs1KWhIdLTr8bF1K5XKI/export?format=csv&gid=0",
            source="google_sheet",
        )

        result = await session.execute(select(Opportunity))
        total = len(result.scalars().all())
        print(f"\nTotal opportunities in database: {total}")


if __name__ == "__main__":
    asyncio.run(main())
