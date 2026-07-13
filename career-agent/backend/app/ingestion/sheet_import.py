"""Google Sheet importer - fetches a public/shared sheet as CSV and upserts into applications."""

import csv
import hashlib
import io
from typing import Optional

import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application import Application


EXPECTED_COLUMNS = {"company", "role", "job_link", "hr_contact", "status", "date_applied", "notes"}


def _row_hash(row: dict) -> str:
    key = f"{row.get('company', '').strip().lower()}:{row.get('role', '').strip().lower()}:{row.get('job_link', '').strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:64]


def _sheet_csv_url(sheet_url: str) -> str:
    import re
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError("Invalid Google Sheets URL - could not extract sheet ID")
    sheet_id = match.group(1)
    gid_match = re.search(r"gid=(\d+)", sheet_url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


async def import_from_sheet(
    db: AsyncSession,
    user_id,
    sheet_url: str,
) -> dict:
    csv_url = _sheet_csv_url(sheet_url)

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(csv_url)
        if response.status_code != 200:
            raise ValueError(f"Could not fetch sheet - make sure it is shared as 'Anyone with the link can view'. Status: {response.status_code}")

    content = response.text
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        raise ValueError("Sheet appears empty or has no header row")

    normalized_fields = {f.strip().lower(): f for f in reader.fieldnames}
    missing = {"company", "role"} - set(normalized_fields.keys())
    if missing:
        raise ValueError(f"Sheet is missing required columns: {missing}. Required: company, role. Optional: job_link, hr_contact, status, date_applied, notes")

    inserted = 0
    skipped = 0

    for raw_row in reader:
        row = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

        company = row.get("company", "").strip()
        role = row.get("role", "").strip()
        if not company or not role:
            skipped += 1
            continue

        row_hash = _row_hash(row)

        existing = await db.execute(
            select(Application).where(
                Application.user_id == user_id,
                Application.source_row_hash == row_hash,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        app = Application(
            user_id=user_id,
            company=company,
            role=role,
            job_link=row.get("job_link") or None,
            hr_contact=row.get("hr_contact") or None,
            status=row.get("status") or "applied",
            date_applied=row.get("date_applied") or None,
            notes=row.get("notes") or None,
            source="sheet",
            source_row_hash=row_hash,
        )
        db.add(app)
        inserted += 1

    await db.commit()
    return {"inserted": inserted, "skipped": skipped}
