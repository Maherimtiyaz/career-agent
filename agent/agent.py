"""
Career Agent CLI
Usage:
  python agent.py             - run full outreach
  python agent.py --dry-run   - preview without sending
  python agent.py --followups - follow-ups only
"""
import asyncio
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from db import init_db, already_emailed, log_email, get_pending_followups, mark_followup_sent, get_stats
from email_drafter import draft_cold_email, draft_followup
from gmail_sender import send_email
from opportunity_fetcher import get_todays_targets

console = Console()
DRY_RUN = "--dry-run" in sys.argv
FOLLOWUPS_ONLY = "--followups" in sys.argv
MAX_EMAILS = 30


async def run():
    init_db()
    console.print(Panel.fit(
        f"[bold purple]Career Agent[/bold purple] — {datetime.now().strftime('%A, %d %B %Y')}\n"
        f"Mode: {'[yellow]DRY RUN - no emails sent[/yellow]' if DRY_RUN else '[green]LIVE[/green]'}",
        border_style="purple"
    ))

    stats = get_stats()
    console.print(f"\n[dim]All time: {stats['total']} sent · {stats['replied']} replies · {stats['followups']} follow-ups[/dim]")
    console.print(f"[dim]Today: {stats['today']} sent[/dim]\n")

    if not FOLLOWUPS_ONLY:
        console.print("[bold]Finding opportunities and emails...[/bold]")
        targets, manual = await get_todays_targets(MAX_EMAILS)

        sent_count = 0
        skipped_count = 0

        if targets:
            console.print(f"\n[green bold]✓ {len(targets)} opportunities with emails found[/green bold]")

            sent_table = Table(show_header=True, header_style="bold dim", border_style="dim", title="Outreach Queue")
            sent_table.add_column("Company", style="white", max_width=25)
            sent_table.add_column("Role", style="dim", max_width=30)
            sent_table.add_column("Email", style="cyan", max_width=30)
            sent_table.add_column("Source", style="dim", max_width=10)
            sent_table.add_column("Status", max_width=10)

            for opp in targets:
                company = (opp.get("organization") or opp.get("company") or "Unknown")[:25]
                role = (opp.get("title") or opp.get("role") or "Internship")[:30]
                hr_email = opp.get("hr_email", "")
                email_source = opp.get("email_source", "")
                opp_id = str(opp.get("id", ""))

                if already_emailed(company, hr_email):
                    sent_table.add_row(company, role, hr_email, email_source, "[dim]already sent[/dim]")
                    skipped_count += 1
                    continue

                draft = await draft_cold_email(
                    company=company,
                    role=role,
                    job_link=opp.get("url", ""),
                    notes=(opp.get("description", "") or "")[:200],
                )

                if DRY_RUN:
                    sent_table.add_row(company, role, hr_email, email_source, "[yellow]preview[/yellow]")
                    console.print(f"\n[dim]Subject:[/dim] {draft['subject']}")
                    console.print(f"[dim]{draft['body'][:150]}...[/dim]")
                    sent_count += 1
                else:
                    success = send_email(hr_email, draft["subject"], draft["body"])
                    if success:
                        log_email(opp_id, company, role, hr_email, draft["subject"], draft["body"])
                        sent_table.add_row(company, role, hr_email, email_source, "[green]sent ✓[/green]")
                        sent_count += 1
                    else:
                        sent_table.add_row(company, role, hr_email, email_source, "[red]failed[/red]")

            console.print(sent_table)
        else:
            console.print("[yellow]No opportunities with emails found via APIs today.[/yellow]")
            console.print("[dim]Add Hunter.io / Apollo / Prospeo API keys in agent/.env to find more.[/dim]")

        if manual:
            console.print(f"\n[bold yellow]{len(manual)} opportunities need manual apply (no email found):[/bold yellow]")
            manual_table = Table(show_header=True, header_style="bold dim", border_style="dim", title="Apply Manually")
            manual_table.add_column("Company", style="white", max_width=30)
            manual_table.add_column("Role", style="dim", max_width=35)
            manual_table.add_column("Link", style="blue", max_width=50)
            for opp in manual:
                manual_table.add_row(
                    (opp.get("organization") or "")[:30],
                    (opp.get("title") or "")[:35],
                    (opp.get("url") or "")[:50],
                )
            console.print(manual_table)
            console.print("[dim]Open these links and apply directly. The agent could not find a contact email.[/dim]")

        console.print(f"\n[green bold]Emails sent: {sent_count}[/green bold] · [dim]Skipped: {skipped_count}[/dim]")

    console.print("\n[bold]Checking follow-ups (5+ days, no reply)...[/bold]")
    pending = get_pending_followups(days=5)

    if not pending:
        console.print("[dim]No follow-ups due today.[/dim]")
    else:
        fu_sent = 0
        for item in pending:
            draft = await draft_followup(item["company"], item["role"], item["subject"])
            if not DRY_RUN:
                success = send_email(item["to_email"], draft["subject"], draft["body"])
                if success:
                    mark_followup_sent(item["id"])
                    fu_sent += 1
                    console.print(f"[green]↩ Follow-up sent → {item['company']}[/green]")
            else:
                console.print(f"[dim]FOLLOW-UP PREVIEW → {item['company']}: {draft['subject']}[/dim]")
                fu_sent += 1
        console.print(f"[green]Follow-ups sent: {fu_sent}[/green]")

    final = get_stats()
    console.print(Panel.fit(
        f"[bold green]Done![/bold green]\n"
        f"Today: [bold]{final['today']}[/bold] emails sent\n"
        f"Total: {final['total']} · Replies: {final['replied']} · Follow-ups: {final['followups']}",
        border_style="green"
    ))


if __name__ == "__main__":
    asyncio.run(run())