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

## 4. First run (opens browser for Gmail auth)
python agent.py --dry-run

This opens your browser once to authorize Gmail.
After that, it runs silently every time.

## 5. Daily run
python agent.py

## 6. Preview without sending
python agent.py --dry-run

## 7. Only send follow-ups
python agent.py --followups

## How to get more email targets
The agent only emails when it finds an HR/contact email in the job posting.
To maximize targets:
- Import your Google Sheet with hr_contact column filled in
- The YC Who's Hiring thread often has emails in comments
- Add emails manually to applications in the Career Agent dashboard
