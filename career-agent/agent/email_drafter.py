"""AI email drafter using Anthropic API."""
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Mahek")
SENDER_COLLEGE = os.getenv("SENDER_COLLEGE", "VGU Jaipur")
SENDER_SKILLS = os.getenv("SENDER_SKILLS", "Python, FastAPI, Docker")
SENDER_TARGET = os.getenv("SENDER_TARGET", "backend internship")
SENDER_GITHUB = os.getenv("SENDER_GITHUB", "")
SENDER_LINKEDIN = os.getenv("SENDER_LINKEDIN", "")


async def draft_cold_email(company: str, role: str, job_link: str = "", notes: str = "") -> dict:
    links = " | ".join(x for x in [SENDER_GITHUB, SENDER_LINKEDIN] if x)

    prompt = f"""Write a concise professional cold email from a student applying for an internship/job.

Sender:
- Name: {SENDER_NAME}
- College: {SENDER_COLLEGE}
- Skills: {SENDER_SKILLS}
- Links: {links}

Target:
- Company: {company}
- Role: {role}
- Job link: {job_link or "not provided"}
- Notes: {notes or "none"}

Rules:
- Under 120 words total
- Sound human, not templated
- One specific thing about the company/role
- Clear ask: 15-minute call or application review
- No "I hope this email finds you well"
- Sign off with name and links

Return EXACTLY:
SUBJECT: <subject line>
BODY:
<email body>

Nothing else."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 400,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            text = resp.json()["content"][0]["text"].strip()
            lines = text.split("\n")
            subject = ""
            body_lines = []
            in_body = False
            for line in lines:
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    in_body = True
                elif in_body:
                    body_lines.append(line)
            return {"subject": subject, "body": "\n".join(body_lines).strip()}
    except Exception as e:
        return {
            "subject": f"Application for {role} at {company}",
            "body": f"""Hi,

I am {SENDER_NAME}, a {SENDER_COLLEGE} student with skills in {SENDER_SKILLS}.

I am very interested in the {role} opportunity at {company}. Would you have 15 minutes for a quick call?

Best,
{SENDER_NAME}
{links}"""
        }


async def draft_followup(company: str, role: str, original_subject: str) -> dict:
    return {
        "subject": f"Re: {original_subject}",
        "body": f"""Hi,

I wanted to follow up on my previous email regarding the {role} position at {company}.

I remain very interested and would love to connect. Please let me know if you need any additional information.

Best,
{SENDER_NAME}
{" | ".join(x for x in [SENDER_GITHUB, SENDER_LINKEDIN] if x)}"""
    }