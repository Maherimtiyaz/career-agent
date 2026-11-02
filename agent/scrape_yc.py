"""
Run this separately to scrape YC startups and print found emails.
Usage: python scrape_yc.py
       python scrape_yc.py --boards
"""
import asyncio
import sys
from rich.console import Console
from rich.table import Table
from free_email_extractor import run_free_extractor, extract_from_job_page

console = Console()


async def main():
    mode = "boards" if "--boards" in sys.argv else "yc"

    console.print(f"\n[bold purple]Free Email Extractor — mode: {mode}[/bold purple]\n")

    if mode == "yc":
        console.print("[dim]Scraping YC startup directory for hiring companies...[/dim]\n")
        results = await run_free_extractor(mode="yc")
    else:
        console.print("[dim]Scraping startup job boards (RemoteOK)...[/dim]\n")
        results = await run_free_extractor(mode="boards")

    table = Table(show_header=True, header_style="bold dim", border_style="dim")
    table.add_column("Company", style="white", max_width=25)
    table.add_column("Best Email", style="cyan", max_width=35)
    table.add_column("All Emails Found", style="dim", max_width=50)
    table.add_column("Source", style="dim", max_width=15)

    found = 0
    for r in results:
        if r.get("emails"):
            table.add_row(
                r.get("company", "")[:25],
                r["emails"][0],
                ", ".join(r["emails"][:3]),
                r.get("source", mode),
            )
            found += 1

    console.print(table)
    console.print(f"\n[green]Found emails for {found}/{len(results)} companies[/green]")
    console.print("[dim]Copy these emails into your agent/.env or Career Agent dashboard hr_contact field[/dim]")


async def check_single(url: str):
    console.print(f"\n[bold]Checking:[/bold] {url}\n")
    result = await extract_from_job_page(url)
    if result["emails"]:
        console.print(f"[green]Found {len(result['emails'])} email(s):[/green]")
        for e in result["emails"]:
            console.print(f"  [cyan]{e}[/cyan]")
        console.print(f"[dim]Source: {result['source']}[/dim]")
    else:
        console.print("[yellow]No emails found on this page.[/yellow]")
        console.print(f"[dim]Tried: {', '.join(result['tried'])}[/dim]")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        asyncio.run(check_single(args[0]))
    else:
        asyncio.run(main())