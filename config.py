import os
from dotenv import load_dotenv

load_dotenv()

# Gemini AI configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Optional Recruiter Enrichment API (e.g. Hunter.io free tier: 25 searches/month)
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# Gmail Configuration for Drafting Applications
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
DEFAULT_RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

# Candidate Master Facts (Rutik Patil)
CANDIDATE_NAME = "Rutik Patil"
CANDIDATE_EMAIL = GMAIL_ADDRESS
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "")
CANDIDATE_LINKEDIN = "https://www.linkedin.com/in/rutik-patil"
CANDIDATE_GITHUB = "https://github.com/Rutikpatil0123"

# Job quota distribution: 40 India + 10 International Big Tech = 50 daily
DEFAULT_TOTAL_JOBS = int(os.getenv("DEFAULT_TOTAL_JOBS", "50"))
DEFAULT_INDIA_JOBS = int(os.getenv("DEFAULT_INDIA_JOBS", "40"))
DEFAULT_INTL_BIG_TECH_JOBS = int(os.getenv("DEFAULT_INTL_BIG_TECH_JOBS", "10"))

HISTORY_FILE_PATH = "processed_job_ids.json"
DRAFTED_JOBS_FILE = "drafted_jobs.json"

# Search settings for India bucket (40 jobs)
INDIA_KEYWORDS = ["Data Engineer", "Backend Engineer", "Python Developer", "ETL Engineer"]
INDIA_LOCATION = "India"

# International Big Tech Target Companies & Keywords (10 jobs)
BIG_TECH_COMPANIES = [
    "Google", "Microsoft", "Amazon", "Meta", "Apple", "Netflix",
    "Nvidia", "Databricks", "Snowflake", "Uber", "Stripe", "Airbnb", "Salesforce"
]
INTL_LOCATIONS = ["United States", "Remote", "Europe"]

# Rutik Patil Core Stack & Target Role Alignment
TARGET_ROLE_KEYWORDS = ["Data Engineer", "Backend", "Data Engineering", "Software Engineer", "ETL", "Data Platform"]
CORE_SKILLS = [
    "Python", "SQL", "PostgreSQL", "MySQL", "Spark", "PySpark", "ETL",
    "Data Engineering", "Backend", "REST API", "Microservices", "Flask",
    "FastAPI", "Django", "AWS", "Docker", "Git", "Linux", "Database Design"
]

MAYBE_GAPS_TO_CHECK = [
    "StarRocks", "Hudi", "Trino", "Ranger", "Databricks", "Airflow", "Terraform", "Kubernetes"
]

# LinkedIn guest endpoint URLs
LINKEDIN_SEARCH_API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LINKEDIN_JOB_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

# Request headers to mimic browser access
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.5",
}

REQUEST_DELAY_MIN = 0.8
REQUEST_DELAY_MAX = 1.8
