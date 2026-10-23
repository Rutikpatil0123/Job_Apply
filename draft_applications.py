#!/usr/bin/env python3
"""
draft_applications.py — Option A: Batch Gmail Draft Creator

Reads the latest (or specified) linkedin_jobs_*.csv, filters by score / market,
generates a tailored application email via Gemini AI (or template fallback),
and saves it to Gmail Drafts via IMAP.

Usage examples:
  python draft_applications.py                          # all defaults
  python draft_applications.py --limit 5 --dry-run
  python draft_applications.py --csv linkedin_jobs_2026-10-22.csv --market India
  python draft_applications.py --min-score 75 --limit 20
"""

import argparse
import csv
import glob
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DEFAULT_RESUME_PATH
from draft_manager import DraftManager
from email_generator import ApplicationEmailGenerator
from gmail_drafter import GmailDrafter

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("draft_applications")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def find_latest_csv() -> Optional[str]:
    """Return the most-recently modified linkedin_jobs_*.csv file."""
    pattern = "linkedin_jobs_*.csv"
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_jobs_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Parse the CSV and return a list of job dicts."""
    jobs: List[Dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            jobs.append(dict(row))
    return jobs


def normalise_job(row: Dict[str, Any]) -> Dict[str, Any]:
    """Remap CSV column names to internal field names used by email_generator."""
    return {
        "job_id":         row.get("Job ID", ""),
        "market":         row.get("Market / Region", ""),
        "org_name":       row.get("Organization Name", ""),
        "job_title":      row.get("Job Title", ""),
        "role_category":  row.get("Role Category", ""),
        "match_score":    row.get("Match Score", "0"),
        "skills":         row.get("Matched Skills", ""),
        "skill_gaps":     row.get("Potential Gaps", ""),
        "recruiter_name": row.get("Recruiter Name", ""),
        "recruiter_title":row.get("Recruiter Title", ""),
        "recruiter_email":row.get("HR / Recruiter Email", ""),
        "email_source":   row.get("Email Source", ""),
        "domain":         row.get("Company Domain", ""),
        "date_posted":    row.get("Date Posted", ""),
        "location":       row.get("Location", ""),
        "job_url":        row.get("Job URL", ""),
    }


def score_as_int(job: Dict[str, Any]) -> int:
    try:
        return int(str(job.get("match_score", "0")).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0


def is_real_email(email: str) -> bool:
    """Return True if the email is a usable address (not N/A / empty / guessed domain)."""
    if not email:
        return False
    lowered = email.strip().lower()
    if lowered in {"n/a", "na", "none", "", "-"}:
        return False
    return "@" in lowered


def print_table_header():
    print(
        f"\n{'#':<4} {'Company':<22} {'Role':<30} {'Score':<7} {'Recruiter Email':<30} {'Status'}"
    )
    print("─" * 110)


def print_table_row(index: int, job: Dict, status: str):
    company = job.get("org_name", "")[:21]
    title   = job.get("job_title", "")[:29]
    score   = f"{score_as_int(job)}%"
    email   = (job.get("recruiter_email") or "")[:29]
    print(f"{index:<4} {company:<22} {title:<30} {score:<7} {email:<30} {status}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-create Gmail Drafts for top job matches in today's CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        help="Path to the CSV file. Defaults to the latest linkedin_jobs_*.csv.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of drafts to create per run (default: 10).",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=70,
        dest="min_score",
        help="Minimum match score %% to include (default: 70).",
    )
    parser.add_argument(
        "--market",
        choices=["India", "International Big Tech", "all"],
        default="all",
        help="Filter by market segment (default: all).",
    )
    parser.add_argument(
        "--resume",
        default=DEFAULT_RESUME_PATH,
        help=f"Path to resume PDF to attach (default: {DEFAULT_RESUME_PATH}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print email previews without saving to Gmail Drafts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── 1. Find CSV ────────────────────────────────────────────────────────────
    csv_path = args.csv or find_latest_csv()
    if not csv_path or not Path(csv_path).is_file():
        print(f"❌  No CSV file found. Run main.py first, or pass --csv <path>.")
        sys.exit(1)
    print(f"\n📄 Reading jobs from: {csv_path}")

    # ── 2. Load & normalise ────────────────────────────────────────────────────
    raw_jobs = load_jobs_from_csv(csv_path)
    all_jobs = [normalise_job(r) for r in raw_jobs]

    # ── 3. Filter ──────────────────────────────────────────────────────────────
    manager   = DraftManager()
    generator = ApplicationEmailGenerator()
    resume_path = args.resume if Path(args.resume).is_file() else None

    if not resume_path:
        logger.warning(f"Resume file not found at '{args.resume}'. Drafts will be sent without attachment.")

    # Market filter
    if args.market != "all":
        all_jobs = [j for j in all_jobs if j.get("market", "") == args.market]

    # Score filter
    all_jobs = [j for j in all_jobs if score_as_int(j) >= args.min_score]

    # Remove already-drafted jobs
    pending = [j for j in all_jobs if not manager.is_drafted(j["job_id"])]

    # Sort: jobs with a real email address first (better chance of delivery), then by score desc
    pending.sort(key=lambda j: (is_real_email(j.get("recruiter_email", "")), score_as_int(j)), reverse=True)

    candidates = pending[: args.limit]

    print(f"📊 Candidates: {len(all_jobs)} passed filters | {len(pending)} not yet drafted | processing {len(candidates)}")

    if not candidates:
        print("\n✅ Nothing new to draft — all qualifying jobs have already been processed.")
        return

    # ── 4. Draft loop ──────────────────────────────────────────────────────────
    drafter = None if args.dry_run else GmailDrafter()

    print_table_header()
    drafted_count = 0
    failed_count  = 0

    for idx, job in enumerate(candidates, start=1):
        try:
            email = generator.generate_email(job)
            to_address = job.get("recruiter_email", "")
            if not is_real_email(to_address):
                to_address = ""  # will save draft without To: header — still useful

            subject = email["subject"]
            body    = email["body"]
            gen_tag = email.get("generator", "?")

            if args.dry_run:
                print_table_row(idx, job, f"[DRY-RUN] ({gen_tag})")
                print(f"\n{'─'*60}")
                print(f"To:      {to_address or '(no email found)'}")
                print(f"Subject: {subject}")
                print(body)
                print()
            else:
                result = drafter.save_draft(
                    to_email=to_address,
                    subject=subject,
                    body=body,
                    resume_path=resume_path,
                )

                if result.get("status") == "success":
                    manager.mark_drafted(job["job_id"], {
                        "job_title":  job.get("job_title"),
                        "org_name":   job.get("org_name"),
                        "to_email":   to_address,
                        "subject":    subject,
                        "generator":  gen_tag,
                        "csv_source": csv_path,
                        "drafted_at": datetime.now().isoformat(),
                    })
                    print_table_row(idx, job, f"✅ Drafted ({gen_tag})")
                    drafted_count += 1
                else:
                    print_table_row(idx, job, f"❌ Failed: {result.get('message', 'unknown error')}")
                    failed_count += 1

        except Exception as exc:
            print_table_row(idx, job, f"❌ Exception: {exc}")
            logger.exception(f"Unexpected error processing job {job.get('job_id')}: {exc}")
            failed_count += 1

    # ── 5. Summary ─────────────────────────────────────────────────────────────
    print("\n" + "═" * 110)
    if args.dry_run:
        print(f"🔍 DRY-RUN complete. {len(candidates)} email(s) previewed. No drafts saved.")
    else:
        print(f"🎉 Done! {drafted_count} draft(s) saved to Gmail | {failed_count} failed.")
        if resume_path:
            print(f"📎 Resume attached: {resume_path}")
        print(f"📂 Draft tracker updated: drafted_jobs.json")


if __name__ == "__main__":
    main()
