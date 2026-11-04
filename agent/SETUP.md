# Career Agent CLI Setup

## 1. Install dependencies
pip install -r requirements.txt

## 2. Get Gmail API credentials
1. Go to https://console.cloud.google.com
2. Create a new project called "career-agent"
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop App)
5. Download as credentials.json
6. Place credentials.json in this agent/ folder

## 3. Configure .env
Edit agent/.env with your details:
- Your Career Agent login email/password
- Your Anthropic API key (get free at console.anthropic.com)
- Your name, college, skills, GitHub, LinkedIn

## 4. Preview without Gmail
python agent.py --dry-run

This previews drafted messages without sending or logging them. It does not need Gmail OAuth credentials or a token. The preview still fetches opportunities and drafts messages using the integrations configured in `agent/.env`.

## 5. First live run
Before sending, provide either an existing `token.json` or a Gmail OAuth Desktop App credentials file. By default, the client file is `agent/credentials.json`; set `GMAIL_CREDENTIALS_FILE` in `agent/.env` to use another path.

The first live send opens a browser for Gmail authorization when needed and saves the resulting token as `agent/token.json`. If no opportunities or follow-ups need sending, the OAuth browser flow does not start.

## 6. Daily live run
python agent.py

## 7. Only send follow-ups
python agent.py --followups

## How to get more email targets
The agent only emails when it finds an HR/contact email in the job posting.
To maximize targets:
- Import your Google Sheet with hr_contact column filled in
- The YC Who's Hiring thread often has emails in comments
- Add emails manually to applications in the Career Agent dashboard
