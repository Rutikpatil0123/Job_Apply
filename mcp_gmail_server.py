#!/usr/bin/env python3
"""
mcp_gmail_server.py — Option B: MCP Server for In-Chat Gmail Drafting

Exposes three in-chat tools via stdio MCP transport:
  • list_available_jobs   — list today's top undrafted jobs
  • preview_email_draft   — preview email in chat (no Gmail write)
  • draft_job_application — generate email & save to Gmail Drafts

Compatibility note: Python 3.14 + pydantic 2.14 has a known import issue with
mcp 1.9.x. We apply a one-line monkey-patch before importing mcp to work around it.

Start (called automatically by MCP host via stdio):
  venv/bin/python mcp_gmail_server.py
"""

import sys
from pathlib import Path

# ── Pydantic 2.14 / Python 3.14 compatibility shim ───────────────────────────
# mcp 1.9.x imports pydantic._internal._typing_extra.eval_type_backport which
# was removed in pydantic 2.14. We inject a no-op shim before mcp is imported.
try:
    import pydantic._internal._typing_extra as _te
    if not hasattr(_te, "eval_type_backport"):
        import typing

        def _eval_type_backport(value, globalns=None, localns=None, type_params=None):
            """Shim for pydantic 2.14 compatibility with Python 3.14."""
            return typing.get_type_hints  # pragma: no cover

        _te.eval_type_backport = _eval_type_backport
except Exception:
    pass  # If pydantic isn't installed at all, mcp will handle the error itself

# ── MCP SDK ──────────────────────────────────────────────────────────────────
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    print(
        f"ERROR: could not import mcp ({exc}). "
        "Install with:  pip install 'mcp>=1.0.0'",
        file=sys.stderr,
    )
    sys.exit(1)

import csv
import glob
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_RESUME_PATH
from draft_manager import DraftManager
from email_generator import ApplicationEmailGenerator
from gmail_drafter import GmailDrafter

# ── Logging (stderr — doesn't pollute the MCP stdio pipe) ───────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_gmail_server")

# ── FastMCP app instance ─────────────────────────────────────────────────────
mcp = FastMCP("job-apply-gmail")


# ── Shared helpers ────────────────────────────────────────────────────────────

def find_latest_csv() -> Optional[str]:
    project_dir = str(Path(__file__).parent)
    files = glob.glob(os.path.join(project_dir, "linkedin_jobs_*.csv"))
    return max(files, key=os.path.getmtime) if files else None


def load_jobs(csv_path: str) -> List[Dict[str, Any]]:
    jobs = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            jobs.append({
                "job_id":          row.get("Job ID", ""),
                "market":          row.get("Market / Region", ""),
                "org_name":        row.get("Organization Name", ""),
                "job_title":       row.get("Job Title", ""),
                "match_score":     row.get("Match Score", "0"),
                "skills":          row.get("Matched Skills", ""),
                "skill_gaps":      row.get("Potential Gaps", ""),
                "recruiter_name":  row.get("Recruiter Name", ""),
                "recruiter_title": row.get("Recruiter Title", ""),
                "recruiter_email": row.get("HR / Recruiter Email", ""),
                "location":        row.get("Location", ""),
                "job_url":         row.get("Job URL", ""),
            })
    return jobs


def score_int(job: Dict) -> int:
    try:
        return int(str(job.get("match_score", "0")).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0


def is_real_email(e: str) -> bool:
    if not e:
        return False
    l = e.strip().lower()
    return l not in {"n/a", "na", "none", "", "-"} and "@" in l


def find_job_by_id(job_id: str, jobs: List[Dict]) -> Optional[Dict]:
    for j in jobs:
        if j["job_id"] == job_id:
            return j
    return None


# ── Tool: list_available_jobs ─────────────────────────────────────────────────

@mcp.tool()
def list_available_jobs(limit: int = 10, market: str = "all", min_score: int = 70) -> str:
    """
    List the top undrafted job matches from today's LinkedIn CSV.
    Use this to pick a job_id before calling draft_job_application.

    Args:
        limit: Maximum number of jobs to return (default 10).
        market: Filter by 'India', 'International Big Tech', or 'all'.
        min_score: Minimum match score % to include (default 70).
    """
    csv_path = find_latest_csv()
    if not csv_path:
        return "⚠️ No linkedin_jobs_*.csv found. Run main.py first to collect jobs."

    jobs    = load_jobs(csv_path)
    manager = DraftManager()

    if market != "all":
        jobs = [j for j in jobs if j.get("market") == market]

    jobs = [j for j in jobs if score_int(j) >= min_score and not manager.is_drafted(j["job_id"])]
    jobs.sort(key=lambda j: (is_real_email(j.get("recruiter_email", "")), score_int(j)), reverse=True)
    jobs = jobs[:limit]

    if not jobs:
        return "✅ No undrafted jobs matching your filters. Lower min_score or change market."

    csv_name = Path(csv_path).name
    lines = [
        f"📋 Top {len(jobs)} undrafted job(s) from {csv_name}\n",
        f"{'#':<4} {'Job ID':<14} {'Company':<22} {'Role':<28} {'Score':<7} {'Email?':<8} Market",
        "─" * 100,
    ]
    for i, j in enumerate(jobs, 1):
        has_email = "✅" if is_real_email(j.get("recruiter_email", "")) else "❌"
        lines.append(
            f"{i:<4} {j['job_id']:<14} {j['org_name'][:21]:<22} {j['job_title'][:27]:<28} "
            f"{score_int(j):<7}% {has_email:<8} {j.get('market','')}"
        )

    lines.append(
        "\n💡 Use `draft_job_application` with a Job ID to save a Gmail Draft, "
        "or `preview_email_draft` to see the email first."
    )
    return "\n".join(lines)


# ── Tool: preview_email_draft ────────────────────────────────────────────────

@mcp.tool()
def preview_email_draft(job_id: str, custom_notes: str = "") -> str:
    """
    Generate and preview the application email for a job (no Gmail write).
    Use this before draft_job_application to verify the email looks good.

    Args:
        job_id: The Job ID string from the CSV (e.g. '3956189234').
        custom_notes: Optional extra context to customize the generated email.
    """
    csv_path = find_latest_csv()
    if not csv_path:
        return "⚠️ No CSV found. Run main.py first."

    jobs = load_jobs(csv_path)
    job  = find_job_by_id(job_id, jobs)

    if not job:
        return f"❌ Job ID '{job_id}' not found in {Path(csv_path).name}. Use list_available_jobs to see valid IDs."

    if custom_notes:
        job["skill_gaps"] = (job.get("skill_gaps") or "") + f"\n[Custom notes: {custom_notes}]"

    gen   = ApplicationEmailGenerator()
    email = gen.generate_email(job)

    return (
        f"📧 EMAIL PREVIEW — not saved to Gmail\n"
        f"{'─'*60}\n"
        f"Job ID:     {job_id}\n"
        f"Company:    {job.get('org_name')}\n"
        f"Role:       {job.get('job_title')}\n"
        f"To:         {job.get('recruiter_email') or '(no email found)'}\n"
        f"Generator:  {email.get('generator', '?')}\n"
        f"{'─'*60}\n"
        f"Subject: {email['subject']}\n\n"
        f"{email['body']}\n"
        f"{'─'*60}\n"
        f"✅ Happy with this? Run `draft_job_application` with job_id='{job_id}' to save it."
    )


# ── Tool: draft_job_application ───────────────────────────────────────────────

@mcp.tool()
def draft_job_application(job_id: str, custom_notes: str = "", attach_resume: bool = True) -> str:
    """
    Generate a tailored application email for a job and save it to Gmail Drafts.
    Attaches resume.pdf if it exists. You review and send the draft manually.

    Args:
        job_id: The Job ID string from the CSV.
        custom_notes: Optional extra instructions to customize the email.
        attach_resume: Whether to attach resume.pdf (default True).
    """
    csv_path = find_latest_csv()
    if not csv_path:
        return "⚠️ No CSV found. Run main.py first."

    jobs    = load_jobs(csv_path)
    job     = find_job_by_id(job_id, jobs)
    manager = DraftManager()

    if not job:
        return f"❌ Job ID '{job_id}' not found. Use list_available_jobs to see valid IDs."

    if manager.is_drafted(job_id):
        return (
            f"ℹ️ Job '{job_id}' ({job.get('org_name')}) was already drafted. "
            "Use preview_email_draft to review it."
        )

    if custom_notes:
        job["skill_gaps"] = (job.get("skill_gaps") or "") + f"\n[Custom notes: {custom_notes}]"

    gen   = ApplicationEmailGenerator()
    email = gen.generate_email(job)

    resume_path: Optional[str] = None
    if attach_resume:
        rp = DEFAULT_RESUME_PATH
        if Path(rp).is_file():
            resume_path = rp
        else:
            logger.warning(f"resume.pdf not found at '{rp}'. Drafting without attachment.")

    to_email = job.get("recruiter_email", "")
    if not is_real_email(to_email):
        to_email = ""

    drafter = GmailDrafter()
    result  = drafter.save_draft(
        to_email=to_email,
        subject=email["subject"],
        body=email["body"],
        resume_path=resume_path,
    )

    if result.get("status") == "success":
        manager.mark_drafted(job_id, {
            "job_title":  job.get("job_title"),
            "org_name":   job.get("org_name"),
            "to_email":   to_email,
            "subject":    email["subject"],
            "generator":  email.get("generator", "?"),
            "csv_source": csv_path,
            "drafted_at": datetime.now().isoformat(),
        })
        return "\n".join([
            "✅ Gmail Draft saved!",
            "",
            f"  Company:  {job.get('org_name')}",
            f"  Role:     {job.get('job_title')}",
            f"  To:       {to_email or '(no email — open Gmail and add manually)'}",
            f"  Subject:  {email['subject']}",
            f"  Engine:   {email.get('generator', '?')}",
            f"  Resume:   {'📎 attached' if resume_path else '⚠️ not found — attach manually'}",
            "",
            "📬 Open Gmail → Drafts to review and send when ready.",
        ])
    else:
        return f"❌ Failed to save draft: {result.get('message', 'unknown error')}"


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting Job-Apply MCP Gmail Server (stdio transport)…")
    mcp.run(transport="stdio")
