"""
Career Agent CLI — runs every morning.
Usage: python agent.py
       python agent.py --dry-run   (preview without sending)
       python agent.py --followups (send follow-ups only)
"""
import asyncio
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from db import init_db, already_emailed, log_email, get_pending_followups, mark_followup_sent, get_stats
from email_drafter import draft_cold_email, draft_followup
from gmail_sender import send_email
from opportunity_fetcher import get_todays_targets

console = Console()
DRY_RUN = "--dry-run" in sys.argv
FOLLOWUPS_ONLY = "--followups" in sys.argv
MAX_EMAILS = 30


async def run_outreach():
    init_db()
    console.print(Panel.fit(
        f"[bold purple]Career Agent[/bold purple] — {datetime.now().strftime('%A, %d %B %Y')}\n"
        f"Mode: {'[yellow]DRY RUN[/yellow]' if DRY_RUN else '[green]LIVE[/green]'}",
        border_style="purple"
    ))

    stats = get_stats()
    console.print(f"\n[dim]All time: {stats['total']} sent · {stats['replied']} replies · {stats['followups']} follow-ups[/dim]")
    console.print(f"[dim]Today so far: {stats['today']} sent[/dim]\n")

    if not FOLLOWUPS_ONLY:
        console.print("[bold]Step 1: Fetching opportunities...[/bold]")
        targets = await get_todays_targets(MAX_EMAILS)

        if not targets:
            console.print("[yellow]No opportunities with contact emails found today.[/yellow]")
            console.print("[dim]Tip: Import a Google Sheet with hr_contact column to add more targets.[/dim]")
        else:
            console.print(f"[green]Found {len(targets)} opportunities with emails[/green]\n")

            table = Table(show_header=True, header_style="bold dim", border_style="dim")
            table.add_column("Company", style="white")
            table.add_column("Role", style="dim")
            table.add_column("Email", style="cyan")
            table.add_column("Score", justify="right", style="green")

            sent_count = 0
            skipped_count = 0

            for opp in targets:
                company = opp.get("organization") or opp.get("company", "Unknown")
                role = opp.get("title") or opp.get("role", "Internship")
                hr_email = opp.get("hr_email", "")
                opp_id = str(opp.get("id", ""))

                if not hr_email:
                    skipped_count += 1
                    continue

                if already_emailed(company, hr_email):
                    skipped_count += 1
                    continue

                draft = await draft_cold_email(
                    company=company,
                    role=role,
                    job_link=opp.get("url", ""),
                    notes=opp.get("description", "")[:200] if opp.get("description") else "",
                )

                table.add_row(company[:30], role[:35], hr_email[:35], str(opp.get("_score", 0)))

                if not DRY_RUN:
                    success = send_email(hr_email, draft["subject"], draft["body"])
                    if success:
                        log_email(opp_id, company, role, hr_email, draft["subject"], draft["body"])
                        sent_count += 1
                    else:
                        console.print(f"[red]Failed to send to {hr_email}[/red]")
                else:
                    sent_count += 1
                    console.print(f"\n[dim]--- PREVIEW: {company} ---[/dim]")
                    console.print(f"[cyan]To:[/cyan] {hr_email}")
                    console.print(f"[cyan]Subject:[/cyan] {draft['subject']}")
                    console.print(f"[dim]{draft['body'][:200]}...[/dim]")

            console.print(table)
            console.print(f"\n[green bold]Sent: {sent_count}[/green bold] · [dim]Skipped (already contacted or no email): {skipped_count}[/dim]")

    console.print("\n[bold]Step 2: Checking follow-ups (5+ days no reply)...[/bold]")
    pending = get_pending_followups(days=5)

    if not pending:
        console.print("[dim]No follow-ups due today.[/dim]")
    else:
        console.print(f"[yellow]{len(pending)} follow-ups to send[/yellow]")
        fu_sent = 0
        for item in pending:
            draft = await draft_followup(item["company"], item["role"], item["subject"])
            if not DRY_RUN:
                success = send_email(item["to_email"], draft["subject"], draft["body"])
                if success:
                    mark_followup_sent(item["id"])
                    fu_sent += 1
            else:
                console.print(f"[dim]FOLLOW-UP PREVIEW → {item['company']}: {draft['subject']}[/dim]")
                fu_sent += 1
        console.print(f"[green]Follow-ups sent: {fu_sent}[/green]")

    final_stats = get_stats()
    console.print(Panel.fit(
        f"[bold green]Done![/bold green]\n"
        f"Today: [bold]{final_stats['today']}[/bold] emails sent\n"
        f"Total ever: {final_stats['total']} · Replies: {final_stats['replied']}",
        border_style="green"
    ))


if __name__ == "__main__":
    asyncio.run(run_outreach())