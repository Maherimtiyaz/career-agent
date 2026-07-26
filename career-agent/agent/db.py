"""Local SQLite database for tracking sent emails and follow-ups."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "outreach.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            to_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            follow_up_sent INTEGER DEFAULT 0,
            replied INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def already_emailed(company: str, to_email: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id FROM sent_emails WHERE company=? AND to_email=?",
        (company.lower(), to_email.lower())
    ).fetchone()
    conn.close()
    return row is not None


def log_email(opportunity_id: str, company: str, role: str, to_email: str, subject: str, body: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sent_emails (opportunity_id, company, role, to_email, subject, body, sent_at) VALUES (?,?,?,?,?,?,?)",
        (opportunity_id, company, role, to_email, subject, body, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_pending_followups(days: int = 5) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT id, company, role, to_email, subject, sent_at
        FROM sent_emails
        WHERE follow_up_sent = 0
        AND replied = 0
        AND datetime(sent_at) <= datetime('now', ? || ' days')
    """, (f"-{days}",)).fetchall()
    conn.close()
    return [{"id": r[0], "company": r[1], "role": r[2], "to_email": r[3], "subject": r[4], "sent_at": r[5]} for r in rows]


def mark_followup_sent(email_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE sent_emails SET follow_up_sent=1 WHERE id=?", (email_id,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM sent_emails").fetchone()[0]
    followups = conn.execute("SELECT COUNT(*) FROM sent_emails WHERE follow_up_sent=1").fetchone()[0]
    replied = conn.execute("SELECT COUNT(*) FROM sent_emails WHERE replied=1").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE date(sent_at)=date('now')"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "today": today, "followups": followups, "replied": replied}