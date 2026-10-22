import os
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from history import HistoryTracker

logger = logging.getLogger("csv_exporter")
console = Console()

COLUMN_MAPPING = {
    "job_id": "Job ID",
    "market_type": "Market / Region",
    "org_name": "Organization Name",
    "job_title": "Job Title",
    "role_category": "Role Category",
    "match_score": "Match Score",
    "skills": "Matched Skills",
    "skill_gaps": "Potential Gaps",
    "recruiter_name": "Recruiter Name",
    "recruiter_title": "Recruiter Title",
    "hr_email": "HR / Recruiter Email",
    "email_source": "Email Source",
    "company_domain": "Company Domain",
    "date_posted": "Date Posted",
    "location": "Location",
    "job_url": "Job URL",
}

# Reverse mapping for loading previously saved CSVs
REVERSE_MAPPING = {v: k for k, v in COLUMN_MAPPING.items()}
REVERSE_MAPPING["HR Email"] = "hr_email"
REVERSE_MAPPING["Skills"] = "skills"

def get_daily_filename(prefix: str = "linkedin_jobs") -> str:
    """Generate daily dated CSV filename format: linkedin_jobs_YYYY-MM-DD.csv"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    return f"{prefix}_{today_str}.csv"

def export_to_csv(job_records: List[Dict], output_path: str = None) -> str:
    """Export extracted job records into daily dated CSV and update master history."""
    if not job_records:
        logger.warning("No new job records to export.")
        return ""

    if not output_path or output_path == "linkedin_jobs.csv":
        output_path = get_daily_filename()

    df = pd.DataFrame(job_records)
    output_abs_path = os.path.abspath(output_path)

    # Read existing daily CSV if it exists
    if os.path.exists(output_abs_path):
        try:
            df_old = pd.read_csv(output_abs_path)
            renames = {col: REVERSE_MAPPING[col] for col in df_old.columns if col in REVERSE_MAPPING}
            df_old.rename(columns=renames, inplace=True)
            combined_df = pd.concat([df_old, df], ignore_index=True)
        except Exception as e:
            logger.warning(f"Could not parse existing daily CSV file: {e}")
            combined_df = df
    else:
        combined_df = df

    for key in COLUMN_MAPPING.keys():
        if key not in combined_df.columns:
            combined_df[key] = "N/A"

    # Clean and filter Job IDs
    combined_df = combined_df[combined_df["job_id"].notna()]
    combined_df = combined_df[combined_df["job_id"].astype(str).str.strip() != ""]
    combined_df = combined_df[combined_df["job_id"].astype(str).str.strip() != "nan"]
    
    # Format Job ID as clean integer string
    combined_df["job_id"] = combined_df["job_id"].astype(str).str.split(".").str[0].str.strip()
    combined_df = combined_df.drop_duplicates(subset=["job_id"], keep="last")

    # Order and rename columns
    final_df = combined_df[list(COLUMN_MAPPING.keys())].copy()
    final_df.rename(columns=COLUMN_MAPPING, inplace=True)

    # Export to dated CSV
    final_df.to_csv(output_abs_path, index=False, encoding="utf-8")
    logger.info(f"Successfully exported {len(final_df)} job opening(s) to '{output_abs_path}'.")

    # Update history tracker
    tracker = HistoryTracker()
    tracker.mark_seen(final_df["Job ID"].tolist())

    # Terminal summary table highlighting recruiter details
    table = Table(
        title=f"Rutik Patil's Job & Recruiter Matches ({len(final_df)} jobs in {os.path.basename(output_abs_path)})",
        show_lines=True,
    )
    preview_cols = [
        ("Job ID", "cyan"),
        ("Market / Region", "magenta"),
        ("Organization Name", "bold cyan"),
        ("Job Title", "white"),
        ("Match Score", "bold green"),
        ("Recruiter Name", "yellow"),
        ("HR / Recruiter Email", "bold magenta"),
        ("Location", "white"),
    ]

    for col, style in preview_cols:
        table.add_column(col, style=style)

    for _, row in final_df.tail(len(job_records)).iterrows():
        table.add_row(
            str(row["Job ID"]),
            str(row["Market / Region"]),
            str(row["Organization Name"]),
            str(row["Job Title"])[:26] + ("..." if len(str(row["Job Title"])) > 26 else ""),
            str(row["Match Score"]),
            str(row["Recruiter Name"])[:20] + ("..." if len(str(row["Recruiter Name"])) > 20 else ""),
            str(row["HR / Recruiter Email"]),
            str(row["Location"])[:18] + ("..." if len(str(row["Location"])) > 18 else ""),
        )

    console.print(table)
    return output_abs_path
