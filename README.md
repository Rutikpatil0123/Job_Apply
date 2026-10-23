# LinkedIn Job & Recruiter AI Automation for Rutik Patil

An intelligent Python automation tool that extracts relevant job openings from LinkedIn, evaluates them against Rutik Patil's **Data Engineering & Backend** profile, discovers verified **Recruiter / Hiring Manager / HR Emails**, and generates a daily dated CSV file (`linkedin_jobs_YYYY-MM-DD.csv`) with 50 distinct, non-repeating jobs:
- 🇮🇳 **40 Roles from India** (Data Engineer, Backend Engineer, Python Developer, ETL Engineer)
- 🌍 **10 Roles from International Big Tech** (Google, Microsoft, Amazon, Meta, Apple, Netflix, Nvidia, Databricks, Snowflake, Uber, Stripe, etc.)

---

## 📌 Extracted Data Fields
The generated CSV file contains 16 comprehensive fields:
1. **Job ID** - Unique LinkedIn Job ID
2. **Market / Region** - `India` or `International Big Tech`
3. **Organization Name** - Company hiring for the role
4. **Job Title** - Title of the opening
5. **Role Category** - e.g., Data & Backend Engineering
6. **Match Score** - Match percentage against Rutik Patil's profile
7. **Matched Skills** - Direct matches with Rutik's core skills (Python, SQL, Spark, PySpark, ETL, AWS, FastAPI, Docker, etc.)
8. **Potential Gaps** - Tools to be honest about in applications (Databricks, Airflow, Terraform, Kubernetes, etc.)
9. **Recruiter Name** - Name of recruiter or talent team
10. **Recruiter Title** - Role/Title (e.g. "Senior Technical Recruiter", "Talent Acquisition Lead")
11. **HR / Recruiter Email** - Direct recruiter email or verified company recruitment inbox
12. **Email Source** - Source type ("Direct from Job Posting", "Hunter.io Verified", or "Verified Company Talent Domain")
13. **Company Domain** - Official company domain (e.g. `ncrvoyix.com`, `amazon.com`)
14. **Date Posted** - Date of posting
15. **Location** - Job location (e.g. Bengaluru, India or Redmond, WA, United States)
16. **Job URL** - Direct LinkedIn job URL

---

## 🔍 How Recruiter & HR Email Discovery Works

1. **Direct Post Scanning**: The engine scans the job description for direct emails and recruiter names using regex and AI (including obfuscated emails like `name [at] domain [dot] com`).
2. **Real-time Domain Resolution**: If no direct email is present in the posting, the engine discovers the official company website domain via Clearbit Autocomplete and DNS MX verification.
3. **Optional Hunter.io Integration**: If you set `HUNTER_API_KEY` in `.env` (free at [hunter.io](https://hunter.io)), the engine queries Hunter's HR department search to obtain personal recruiter names and verified corporate emails with confidence ratings.
4. **Verified Talent Mailbox Fallback**: If Hunter is not configured, the engine verifies the company's mail exchange (MX) and provides the corporate talent address (e.g. `careers@company.com`, `talent@company.com`).

---

## 🛠️ Installation & Setup

1. **Activate Virtual Environment**:
   ```bash
   cd /Users/rutikpatil/Documents/GitHub/Job_Apply
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables (Optional)**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your keys in `.env`:
   ```env
   # Google Gemini API key (optional - offline regex fallback works automatically)
   GEMINI_API_KEY=your_gemini_api_key_here

   # Hunter.io API key (optional - for verified personal recruiter emails)
   HUNTER_API_KEY=your_hunter_api_key_here

   DEFAULT_TOTAL_JOBS=50
   DEFAULT_INDIA_JOBS=40
   DEFAULT_INTL_BIG_TECH_JOBS=10
   ```

---

## 🚀 Running the Automation

### Run Daily Collector (40 India + 10 International Big Tech):
```bash
./daily_runner.sh
```

### Manual CLI Run with Custom Quota:
```bash
python main.py --india-limit 40 --intl-limit 10
```

### Automatic Daily Schedule (macOS Cron):
The automation is scheduled to run every morning at 9:00 AM:
```cron
0 9 * * * /Users/rutikpatil/Documents/GitHub/Job_Apply/daily_runner.sh
```
Logs are saved to `automation.log`, and previously processed job IDs are tracked in `processed_job_ids.json` to prevent duplicates.

---

## ✉️ Part 2: Automated Gmail Drafting

After jobs are collected, the system automatically drafts tailored application emails and saves them to your **Gmail Drafts** folder. You review and send each draft yourself.

### How It Works
- **Gemini AI** generates a personalized, role-specific email for each job
- Falls back to a professional template if AI is unavailable
- Attaches `resume.pdf` if it exists in the project root
- Tracks drafted job IDs in `drafted_jobs.json` — no duplicates across runs
- Never sends emails — only saves Drafts for your review

### Prerequisites
Add Gmail credentials to `.env`:
```env
GMAIL_ADDRESS=Rutikpatil0123@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # 16-char Google App Password
RESUME_PATH=resume.pdf                    # Optional: path to your resume PDF
```
> **How to get a Google App Password**: Google Account → Security → 2-Step Verification → App Passwords → Mail → Generate

---

### Option A — Batch CLI (Automatic Daily Drafts)

Runs automatically as part of `daily_runner.sh` every morning. Also runnable manually:

```bash
# Draft top 10 jobs with score ≥ 70% (default)
python draft_applications.py

# Preview emails without saving to Gmail
python draft_applications.py --dry-run --limit 5

# Custom filters
python draft_applications.py --market India --min-score 80 --limit 20

# Specify a CSV manually
python draft_applications.py --csv linkedin_jobs_2026-10-22.csv --limit 5
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--csv` | Latest `linkedin_jobs_*.csv` | CSV file to read jobs from |
| `--limit` | `10` | Max number of drafts to create |
| `--min-score` | `70` | Minimum match score % |
| `--market` | `all` | `India` / `International Big Tech` / `all` |
| `--resume` | `resume.pdf` | Path to resume to attach |
| `--dry-run` | off | Preview emails without saving |

---

### Option B — In-Chat MCP Tools (Interactive)

Talk to Antigravity in chat to draft specific applications on demand.

**Setup (one-time):**
```bash
bash setup_mcp.sh       # Registers the MCP server
# Then restart Antigravity (agy reload)
```

**Available in-chat commands:**

| Tool | Example Usage |
|---|---|
| `list_available_jobs` | Show today's top undrafted matches |
| `preview_email_draft` | Preview the email for job_id `3956189234` |
| `draft_job_application` | Save a Gmail Draft for job_id `3956189234` |

Example chat flow:
```
You:  list_available_jobs limit=10 market=India
AGY:  [shows table of top India jobs with scores]

You:  preview_email_draft job_id=3956189234
AGY:  [shows full email text — no Gmail write]

You:  draft_job_application job_id=3956189234
AGY:  ✅ Gmail Draft saved! Open Drafts to review.
```

---

## 📁 File Map

| File | Purpose |
|---|---|
| `main.py` | Part 1 — Job collection CLI |
| `scraper.py` | LinkedIn guest API scraper |
| `extractor.py` | Gemini AI job detail extractor |
| `recruiter_finder.py` | Recruiter email discovery (Clearbit + Hunter.io) |
| `csv_exporter.py` | Daily CSV export |
| `history.py` | Cross-day deduplication |
| `draft_applications.py` | Part 2 — Batch Gmail Draft CLI |
| `email_generator.py` | Gemini AI + template email generator |
| `gmail_drafter.py` | IMAP Gmail Drafts writer |
| `draft_manager.py` | Tracks drafted job IDs |
| `mcp_gmail_server.py` | FastMCP server for in-chat drafting |
| `daily_runner.sh` | Chains Part 1 + Part 2 for LaunchAgent/cron |
| `setup_mcp.sh` | One-time MCP server registration |
| `config.py` | Central configuration |
| `.env.example` | Environment variable template |
