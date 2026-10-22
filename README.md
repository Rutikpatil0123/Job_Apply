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
