import logging
from typing import Dict
from config import (
    GEMINI_API_KEY,
    CANDIDATE_NAME,
    CANDIDATE_EMAIL,
    CANDIDATE_LINKEDIN,
    CANDIDATE_GITHUB,
)

logger = logging.getLogger("email_generator")

EMAIL_PROMPT_TEMPLATE = """You are drafting an application email for Rutik Patil applying for the following job opening.

Job Details:
- Role Title: {job_title}
- Company: {org_name}
- Recruiter / Contact: {recruiter_name} ({recruiter_title})
- Matched Skills: {matched_skills}
- Potential Gaps: {potential_gaps}
- Location: {location}

Rutik's Verified Experience:
- Background: Software Engineer with strong specialization in Data Engineering & Backend systems.
- Core Skills: Python, SQL, PostgreSQL, MySQL, Spark, PySpark, ETL pipeline development, REST APIs (FastAPI, Flask), AWS, Docker, Git.
- Target Title convention: "Software Engineer (Data Engineering)" or "Data Engineer".

Strict Rules:
1. No fabrication. Only cite tools and skills listed in his verified experience.
2. If potential gaps are listed ({potential_gaps}), do NOT falsely claim years of production expertise; instead briefly and honestly frame his strong distributed data systems foundation and ability to rapidly bridge adjacent stacks.
3. Keep the email concise (between 100 and 150 words), punchy, and professional.
4. Personalized opening addressed to {recruiter_name} (or "{org_name} Hiring Team" if recruiter is generic/team).
5. Lead with 1-2 matching technical achievements in building robust data pipelines / backend APIs.
6. Clear closing: express enthusiasm for {org_name}'s data initiatives and request a brief 10-15 minute introductory call. Mention that his resume is attached.

Output format:
Return ONLY the email text in this format:
Subject: <compelling subject line>

<email body>
"""

class ApplicationEmailGenerator:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Gemini AI client for personalized email generation.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini AI client: {e}. Falling back to template generator.")

    def _generate_template_email(self, job: Dict) -> Dict[str, str]:
        """High-converting, strictly truthful template fallback when AI client is offline."""
        title = job.get("job_title", "Data Engineer")
        org = job.get("org_name", "your team")
        recruiter = job.get("recruiter_name", "Hiring Team")
        skills = job.get("skills", "Python, SQL, ETL, Data Engineering")
        gaps = job.get("skill_gaps", "None detected")

        # Clean salutation
        if recruiter and "team" in recruiter.lower():
            salutation = f"Dear {recruiter},"
        elif recruiter and recruiter != "N/A" and " " in recruiter:
            first_name = recruiter.split()[0]
            salutation = f"Hi {first_name},"
        else:
            salutation = f"Dear {org} Hiring Team,"

        subject = f"Application: {title} - {CANDIDATE_NAME}"

        # Handle gaps honestly
        gap_sentence = ""
        if gaps and gaps != "None detected":
            gap_sentence = f"While my core production focus has centered on PySpark, Python, and SQL pipelines, my strong distributed systems background enables me to quickly adapt to adjacent platforms like {gaps}. "

        body = (
            f"{salutation}\n\n"
            f"I am writing to express my strong interest in the {title} role at {org}. "
            f"With hands-on experience designing scalable ETL pipelines and high-throughput backend services using {skills}, "
            f"I have delivered reliable data workflows and optimized query performance across distributed environments.\n\n"
            f"{gap_sentence}"
            f"I would welcome the opportunity to discuss how my technical background in data engineering can support {org}'s engineering objectives. "
            f"My resume is attached for your review, and I look forward to connecting for a brief introductory conversation.\n\n"
            f"Best regards,\n"
            f"{CANDIDATE_NAME}\n"
            f"Software Engineer (Data Engineering)\n"
            f"Email: {CANDIDATE_EMAIL}\n"
            f"LinkedIn: {CANDIDATE_LINKEDIN}\n"
            f"GitHub: {CANDIDATE_GITHUB}"
        )

        return {
            "subject": subject,
            "body": body,
            "generator": "Template Engine",
        }

    def generate_email(self, job: Dict) -> Dict[str, str]:
        """Generate tailored application email for a job opening."""
        # Try Gemini AI generation first
        if self.client:
            try:
                prompt = EMAIL_PROMPT_TEMPLATE.format(
                    job_title=job.get("job_title", "Data Engineer"),
                    org_name=job.get("org_name", "Company"),
                    recruiter_name=job.get("recruiter_name", "Hiring Team"),
                    recruiter_title=job.get("recruiter_title", "Talent Acquisition"),
                    matched_skills=job.get("skills", "Python, SQL, PySpark, ETL"),
                    potential_gaps=job.get("skill_gaps", "None detected"),
                    location=job.get("location", "India"),
                )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )

                if response and response.text:
                    raw_text = response.text.strip()
                    lines = raw_text.splitlines()
                    subject = f"Application: {job.get('job_title', 'Role')} - {CANDIDATE_NAME}"
                    body_start = 0

                    if lines and lines[0].lower().startswith("subject:"):
                        subject = lines[0].split(":", 1)[1].strip()
                        body_start = 1
                        while body_start < len(lines) and not lines[body_start].strip():
                            body_start += 1

                    body = "\n".join(lines[body_start:]).strip()

                    # Ensure standard signature is present
                    if CANDIDATE_NAME not in body:
                        body += f"\n\nBest regards,\n{CANDIDATE_NAME}\n{CANDIDATE_EMAIL}"

                    return {
                        "subject": subject,
                        "body": body,
                        "generator": "Gemini AI",
                    }
            except Exception as e:
                logger.warning(f"AI generation failed: {e}. Using template generator.")

        return self._generate_template_email(job)
