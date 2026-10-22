import re
import json
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from config import GEMINI_API_KEY, CORE_SKILLS, MAYBE_GAPS_TO_CHECK, TARGET_ROLE_KEYWORDS
from recruiter_finder import resolve_recruiter_contact

logger = logging.getLogger("linkedin_extractor")

class TailoredJobExtractionSchema(BaseModel):
    org_name: str = Field(description="Name of the company or organization hiring")
    job_title: str = Field(description="Official job title")
    role_category: str = Field(description="Category of the role, e.g., 'Data Engineering', 'Backend Engineering', or 'Other'")
    matched_skills: List[str] = Field(description="List of skills matching Rutik Patil's core stack (Python, SQL, Spark, ETL, Backend, AWS, etc.)")
    skill_gaps: List[str] = Field(description="List of required tools/skills mentioned in JD that are potential gaps (Airflow, Databricks, Terraform, Trino, Hudi, etc.)")
    recruiter_name: Optional[str] = Field(default="N/A", description="Name of recruiter, hiring manager, or contact person if mentioned in posting")
    recruiter_title: Optional[str] = Field(default="N/A", description="Role/Title of recruiter or hiring contact if mentioned in posting")
    hr_email: Optional[str] = Field(default="N/A", description="Recruiter or HR contact email address found in description, or 'N/A' if not present")
    date_posted: str = Field(description="Date or relative time when the job was posted")


class AIExtractor:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Google Gemini AI client for profile-tailored extraction.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini AI client: {e}. Falling back to rule-based extraction.")

    def _extract_hr_email_regex(self, text: str) -> str:
        """Extract email using regex pattern, including standard and obfuscated emails."""
        if not text:
            return "N/A"

        # Normalize common obfuscations e.g. "name [at] domain [dot] com" or "name(at)domain.com"
        normalized = text
        normalized = re.sub(r"\[at\]|\(at\)|\s+at\s+", "@", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\[dot\]|\(dot\)|\s+dot\s+", ".", normalized, flags=re.IGNORECASE)

        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        matches = re.findall(email_pattern, normalized)

        ignored_domains = ["linkedin.com", "example.com", "domain.com", "w3.org", "sentry.io"]
        valid_emails = []

        for email in matches:
            email_lower = email.lower()
            if not any(domain in email_lower for domain in ignored_domains):
                valid_emails.append(email)

        if valid_emails:
            priority_emails = [
                e for e in valid_emails
                if any(k in e.lower() for k in ["hr", "recruiter", "careers", "jobs", "apply", "talent", "hiring"])
            ]
            return priority_emails[0] if priority_emails else valid_emails[0]

        return "N/A"

    def _extract_recruiter_name_regex(self, text: str) -> tuple[str, str]:
        """Regex fallback to identify mentioned recruiter/hiring manager name and title."""
        if not text:
            return "N/A", "N/A"

        patterns = [
            r"(?:Contact Recruiter|Hiring Manager|Recruiter|Point of Contact|Reach out to)\s*:\s*([A-Z][a-z]+ [A-Z][a-z]+)",
            r"(?:send resumes? to|contact)\s+([A-Z][a-z]+ [A-Z][a-z]+)\s+at",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1).strip(), "Recruiter / Hiring Contact"

        return "N/A", "N/A"

    def _calculate_match_score(self, title: str, text: str, matched_skills: List[str]) -> float:
        """Calculate match percentage for Rutik Patil's profile."""
        score = 50.0  # Base score for matching search criteria
        text_lower = (title + " " + text).lower()

        # Check target role alignment
        if any(term.lower() in text_lower for term in ["data engineer", "data engineering", "etl"]):
            score += 25.0
        elif any(term.lower() in text_lower for term in ["backend", "python developer", "software engineer"]):
            score += 15.0

        # Add points for core skills matched
        score += min(len(matched_skills) * 5.0, 25.0)

        return min(round(score, 1), 100.0)

    def _extract_skills_and_gaps_regex(self, text: str) -> tuple[List[str], List[str]]:
        """Fallback regex skill & gap extraction."""
        text_lower = text.lower()
        matched = []
        gaps = []

        for skill in CORE_SKILLS:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched.append(skill)

        for gap_skill in MAYBE_GAPS_TO_CHECK:
            pattern = r"\b" + re.escape(gap_skill.lower()) + r"\b"
            if re.search(pattern, text_lower):
                gaps.append(gap_skill)

        return matched, gaps

    def extract_details(self, job_data: Dict) -> Dict:
        """Process job posting dictionary and return structured job record tailored to Rutik's profile."""
        description = job_data.get("description", "")
        org_name = job_data.get("org_name", "N/A")
        job_title = job_data.get("job_title", "N/A")
        date_posted = job_data.get("date_posted", "N/A")

        extracted_email = "N/A"
        recruiter_name = "N/A"
        recruiter_title = "N/A"
        matched_skills = []
        skill_gaps = []
        role_category = "Data & Backend"

        # Step 1: AI extraction via Gemini if client is active
        if self.client and description:
            try:
                from google.genai import types

                prompt = (
                    f"Analyze this job posting specifically tailored for Rutik Patil (Data Engineer & Backend Engineer profile):\n\n"
                    f"Title: {job_title}\n"
                    f"Company: {org_name}\n"
                    f"Posting Date: {date_posted}\n\n"
                    f"Job Description:\n{description[:4000]}\n\n"
                    f"Instructions:\n"
                    f"1. Evaluate against Rutik's core skills: {', '.join(CORE_SKILLS)}.\n"
                    f"2. Identify any potential skill gaps from this list if mentioned in JD: {', '.join(MAYBE_GAPS_TO_CHECK)}.\n"
                    f"3. Carefully identify any Recruiter, Hiring Manager, or HR contact name, title, or email if mentioned."
                )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=TailoredJobExtractionSchema,
                        temperature=0.1,
                    ),
                )

                if response and response.text:
                    parsed = json.loads(response.text)
                    if parsed.get("org_name") and org_name in ["N/A", ""]:
                        org_name = parsed["org_name"]
                    if parsed.get("job_title") and job_title in ["N/A", ""]:
                        job_title = parsed["job_title"]
                    if parsed.get("date_posted") and date_posted in ["N/A", ""]:
                        date_posted = parsed["date_posted"]

                    matched_skills = parsed.get("matched_skills", [])
                    skill_gaps = parsed.get("skill_gaps", [])
                    extracted_email = parsed.get("hr_email", "N/A")
                    recruiter_name = parsed.get("recruiter_name", "N/A")
                    recruiter_title = parsed.get("recruiter_title", "N/A")
                    role_category = parsed.get("role_category", "Data & Backend")

            except Exception as e:
                logger.warning(f"Gemini AI extraction failed: {e}. Utilizing fallback extractor.")

        # Step 2: Fallback / Regex refinement
        if not matched_skills:
            matched_skills, skill_gaps = self._extract_skills_and_gaps_regex(description)

        if extracted_email in ["N/A", "", None]:
            extracted_email = self._extract_hr_email_regex(description)

        if recruiter_name in ["N/A", "", None]:
            reg_name, reg_title = self._extract_recruiter_name_regex(description)
            if reg_name != "N/A":
                recruiter_name, recruiter_title = reg_name, reg_title

        # Step 3: Recruiter & Domain Contact Enrichment Engine
        recruiter_contact = resolve_recruiter_contact(
            company_name=org_name,
            direct_email=extracted_email,
            recruiter_name=recruiter_name,
            recruiter_title=recruiter_title,
        )

        match_score = self._calculate_match_score(job_title, description, matched_skills)

        skills_str = ", ".join(matched_skills) if matched_skills else "N/A"
        gaps_str = ", ".join(skill_gaps) if skill_gaps else "None detected"

        return {
            "job_id": job_data.get("job_id", "N/A"),
            "market_type": job_data.get("market_type", "India"),
            "org_name": org_name,
            "job_title": job_title,
            "role_category": role_category,
            "match_score": f"{match_score}%",
            "skills": skills_str,
            "skill_gaps": gaps_str,
            "recruiter_name": recruiter_contact.get("recruiter_name", "N/A"),
            "recruiter_title": recruiter_contact.get("recruiter_title", "N/A"),
            "hr_email": recruiter_contact.get("recruiter_email", "N/A"),
            "email_source": recruiter_contact.get("email_source", "Not Listed"),
            "company_domain": recruiter_contact.get("company_domain", "N/A"),
            "date_posted": date_posted,
            "location": job_data.get("location", "N/A"),
            "job_url": job_data.get("job_url", "N/A"),
        }
