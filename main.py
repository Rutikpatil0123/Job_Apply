import argparse
import logging
import sys
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from config import (
    DEFAULT_INDIA_JOBS,
    DEFAULT_INTL_BIG_TECH_JOBS,
    INDIA_KEYWORDS,
    INDIA_LOCATION,
    BIG_TECH_COMPANIES,
    INTL_LOCATIONS,
)
from scraper import LinkedInScraper
from extractor import AIExtractor
from csv_exporter import export_to_csv, get_daily_filename
from history import HistoryTracker

console = Console()

def setup_logging():
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False)],
    )

def collect_india_jobs(scraper: LinkedInScraper, history: HistoryTracker, target_count: int, seen_set: set):
    """Collect target_count distinct unseen jobs in India."""
    india_jobs = []
    console.print(f"\n[bold cyan]🇮🇳 Bucket 1: Collecting {target_count} jobs from India...[/bold cyan]")

    for kw in INDIA_KEYWORDS:
        if len(india_jobs) >= target_count:
            break

        needed = target_count - len(india_jobs)
        console.print(f"[bold]Searching India for '[yellow]{kw}[/yellow]' (needed: {needed})...[/bold]")

        candidates = scraper.search_jobs(
            keywords=kw,
            location=INDIA_LOCATION,
            limit=needed * 3,
        )

        unseen_batch = []
        for item in candidates:
            jid = item.get("job_id")
            if jid and not history.is_seen(jid) and jid not in seen_set:
                item["market_type"] = "India"
                unseen_batch.append(item)
                seen_set.add(jid)
                if len(unseen_batch) + len(india_jobs) >= target_count:
                    break

        if not unseen_batch:
            continue

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Downloading India {kw} details...", total=len(unseen_batch))
            for summary in unseen_batch:
                detailed = scraper.fetch_job_details(summary)
                detailed["market_type"] = "India"
                india_jobs.append(detailed)
                progress.advance(task)

    console.print(f"[bold green]✔ Collected {len(india_jobs)} India job postings.[/bold green]")
    return india_jobs

def collect_intl_big_tech_jobs(scraper: LinkedInScraper, history: HistoryTracker, target_count: int, seen_set: set):
    """Collect target_count distinct unseen jobs from International Big Tech companies."""
    intl_jobs = []
    console.print(f"\n[bold cyan]🌍 Bucket 2: Collecting {target_count} jobs from International Big Tech...[/bold cyan]")

    # Iterate through top tier tech companies
    for company in BIG_TECH_COMPANIES:
        if len(intl_jobs) >= target_count:
            break

        for role in ["Data Engineer", "Backend Engineer"]:
            if len(intl_jobs) >= target_count:
                break

            kw = f"{role} {company}"
            loc = "United States"  # Primary big tech market, also captures global/remote
            needed = target_count - len(intl_jobs)

            console.print(f"[bold]Searching International Big Tech for '[yellow]{kw}[/yellow]' in '[yellow]{loc}[/yellow]'...[/bold]")

            candidates = scraper.search_jobs(
                keywords=kw,
                location=loc,
                limit=needed * 2,
            )

            unseen_batch = []
            for item in candidates:
                jid = item.get("job_id")
                org = item.get("org_name", "").lower()

                # Verify alignment with big tech
                is_target_company = any(c.lower() in org for c in BIG_TECH_COMPANIES) or company.lower() in org
                if jid and not history.is_seen(jid) and jid not in seen_set and is_target_company:
                    item["market_type"] = "International Big Tech"
                    unseen_batch.append(item)
                    seen_set.add(jid)
                    if len(unseen_batch) + len(intl_jobs) >= target_count:
                        break

            if not unseen_batch:
                continue

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(f"Downloading {company} {role} details...", total=len(unseen_batch))
                for summary in unseen_batch:
                    detailed = scraper.fetch_job_details(summary)
                    detailed["market_type"] = "International Big Tech"
                    intl_jobs.append(detailed)
                    progress.advance(task)

    console.print(f"[bold green]✔ Collected {len(intl_jobs)} International Big Tech job postings.[/bold green]")
    return intl_jobs

def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Daily LinkedIn Job Extractor & Profile Matcher for Rutik Patil",
        prog="main.py",
    )
    parser.add_argument(
        "--india-limit",
        type=int,
        default=DEFAULT_INDIA_JOBS,
        help=f"Target number of jobs from India (default: {DEFAULT_INDIA_JOBS})",
    )
    parser.add_argument(
        "--intl-limit",
        type=int,
        default=DEFAULT_INTL_BIG_TECH_JOBS,
        help=f"Target number of jobs from International Big Tech (default: {DEFAULT_INTL_BIG_TECH_JOBS})",
    )
    parser.add_argument(
        "-u", "--urls",
        nargs="+",
        help="Specific LinkedIn Job URLs or IDs to scrape directly",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Custom output CSV path (default: 'linkedin_jobs_YYYY-MM-DD.csv')",
    )

    args = parser.parse_args()

    total_target = args.india_limit + args.intl_limit
    output_filename = args.output or get_daily_filename()

    console.print(f"[bold green]🎯 Starting LinkedIn Job AI Automation (Target: {total_target} jobs = {args.india_limit} India + {args.intl_limit} International Big Tech)...[/bold green]")
    console.print(f"[bold cyan]📁 Output CSV: [yellow]{output_filename}[/yellow][/bold cyan]")

    scraper = LinkedInScraper()
    extractor = AIExtractor()
    history = HistoryTracker()

    raw_jobs = []
    seen_in_this_run = set()

    # Mode 1: Fetching specific URLs directly
    if args.urls:
        console.print(f"[bold cyan]Fetching {len(args.urls)} direct LinkedIn Job URLs/IDs...[/bold cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching direct URLs...", total=len(args.urls))
            for url in args.urls:
                job_id = scraper.extract_job_id(url)
                if job_id and not history.is_seen(job_id) and job_id not in seen_in_this_run:
                    job_detail = scraper.fetch_job_by_url(url)
                    if job_detail:
                        job_detail["market_type"] = "Direct URL"
                        raw_jobs.append(job_detail)
                        seen_in_this_run.add(job_id)
                progress.advance(task)

    # Mode 2: 40 India + 10 International Big Tech distribution
    else:
        # Collect Bucket 1: India
        india_jobs = collect_india_jobs(
            scraper=scraper,
            history=history,
            target_count=args.india_limit,
            seen_set=seen_in_this_run,
        )
        raw_jobs.extend(india_jobs)

        # Collect Bucket 2: International Big Tech
        intl_jobs = collect_intl_big_tech_jobs(
            scraper=scraper,
            history=history,
            target_count=args.intl_limit,
            seen_set=seen_in_this_run,
        )
        raw_jobs.extend(intl_jobs)

    if not raw_jobs:
        console.print("[bold yellow]No new distinct jobs found today. History tracker prevented duplicate entries.[/bold yellow]")
        sys.exit(0)

    # Extraction & Profile Matching Phase
    console.print(f"\n[bold cyan]Evaluating {len(raw_jobs)} distinct jobs against Rutik's profile & discovering recruiter emails...[/bold cyan]")
    extracted_records = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Matching profile & resolving recruiter emails...", total=len(raw_jobs))
        for raw_job in raw_jobs:
            record = extractor.extract_details(raw_job)
            extracted_records.append(record)
            progress.advance(task)

    # CSV Export Phase to linkedin_jobs_YYYY-MM-DD.csv
    saved_csv_path = export_to_csv(extracted_records, output_path=output_filename)
    if saved_csv_path:
        india_count = sum(1 for r in extracted_records if r.get("market_type") == "India")
        intl_count = sum(1 for r in extracted_records if r.get("market_type") == "International Big Tech")
        console.print(f"\n[bold green]✅ Daily Run Complete! Collected {len(extracted_records)} distinct new jobs ({india_count} India + {intl_count} International Big Tech).[/bold green]")
        console.print(f"[bold green]Saved file:[/bold green] [underline blue]{saved_csv_path}[/underline blue]")

if __name__ == "__main__":
    main()
