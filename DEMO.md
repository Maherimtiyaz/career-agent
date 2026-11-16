# Demo script & pitch (2–3 minutes)

## Before you go on stage
- [ ] `docker compose up -d`; run `docker compose exec backend python -m app.demo_setup` once
- [ ] `GROQ_API_KEY` set as LLM fallback. Gemini free tier rate-limits (429s caused all 3 eval failures).
- [ ] Do one full warm-up run 5 minutes before (it also warms the Crustdata cache)
- [ ] Browser at `http://localhost:3000`, logged in as `demo@example.com` / `demo1234`, zoom 110%
- [ ] Backup: a screen recording of a good run, in case the venue Wi-Fi fails

## One-liner
> Career Agent turns a one-sentence career goal into a ranked opportunity, a real person to contact, and a personalized email. It sends only after you approve it.

## Script

**0:00 — Problem (20s)**
"Cold outreach works, but it takes hours: find a role that fits, figure out who to email, write something that doesn't sound like a template. Most students give up after three."

**0:20 — Goal in (15s)**
Landing page → *Try the agent*. On the Agent page, click the preset **"Find an ML internship that fits my skills…"** → **Run agent**.
"I just describe what I want. The agent knows my profile: skills, school, projects."

**0:35 — Watch it work (45s)**
Point at the stage bar and the live trace as steps appear:
- *Search opportunities*: "It searches the saved database first, because that's free. It ranks matches by relevance."
- *Find hiring contacts → Enrich contact*: "Now it picks a real person at that company and gets their email. Here are the credits it spent."
- Point to the italic line under each step: "This is the agent's own reasoning for each call. It isn't a script; if a search comes back empty, it changes the query."
- Point to the **source tag** on the contact: "Every contact shows where it came from. In dry-run mode it says *Simulated contact*; we never pass fake data off as real."

**1:20 — Human in the loop (30s)**
The approval card appears.
"The agent stops here. It *can't* send: there's no send tool in its toolbox. Sending happens only on my click, and it sends exactly what I see." Edit one sentence of the body live → **Approve & send**.

**1:50 — Outcome & tracking (15s)**
Point at the green banner and the *Outreach history* row moving to **Sent**.
"It's saved with the opportunity, the contact, the source and the cost. Delivery is simulated in demo mode, and the UI says so."

**2:05 — Why it's solid (30s)**
- "Invented email addresses are blocked. The agent can only email an address a tool actually returned."
- "Double-clicking approve can't send twice; there's a lock and a status re-check."
- "27 automated tests run the whole journey with a scripted LLM, including the model *trying* to send on its own."
- "If Gemini rate-limits us, it falls back to Groq automatically."

**2:35 — Close**
"One sentence in, one personalized, reviewed email out. Next: Gmail sending, resume upload, and follow-up scheduling."

## Likely judge questions
- **"Is it really autonomous?"** It's an LLM-planned loop with guardrails. The model chooses each tool from what it has seen so far, and we deliberately limited it to 5 tools, 10 steps, a credit budget and a mandatory pause before sending. Autonomy where mistakes are cheap, human control where they aren't.
- **"Are the contacts real?"** With `CRUSTDATA_DRY_RUN=false`, yes: live Crustdata people search and enrichment. The demo may run in dry-run mode to save credits, and the UI labels those contacts *Simulated*.
- **"Does it actually send email?"** Not yet. Gmail OAuth is next. We chose to show "simulated" honestly rather than fake a send.
- **"What happens when the LLM fails?"** The provider chain falls through Gemini → Gemini fallback → Groq → OpenRouter. If all fail, the run ends in a clean *Failed* state with the reason shown and no partial sends.
