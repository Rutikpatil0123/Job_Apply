import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config import (
    HTTP_HEADERS,
    LINKEDIN_SEARCH_API_URL,
    LINKEDIN_JOB_DETAIL_URL,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)

logger = logging.getLogger("linkedin_scraper")


class LinkedInScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HTTP_HEADERS)

    def _delay(self):
        """Add randomized delay to avoid rate limiting."""
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    def extract_job_id(self, url_or_urn: str) -> Optional[str]:
        """Extract numeric Job ID from LinkedIn URL or URN string."""
        if not url_or_urn:
            return None
        # URN pattern urn:li:jobPosting:12345678
        urn_match = re.search(r"jobPosting[:\/](\d+)", url_or_urn)
        if urn_match:
            return urn_match.group(1)

        # URL patterns: /jobs/view/12345678 or /jobs/view/title-12345678 or currentJobId=12345678
        url_match = re.search(r"(?:/view/|/view/[^/]+-|currentJobId=)(\d+)", url_or_urn)
        if url_match:
            return url_match.group(1)

        # Fallback to any contiguous numbers >= 8 digits
        digit_match = re.search(r"\b\d{8,12}\b", url_or_urn)
        if digit_match:
            return digit_match.group(0)

        return None

    def search_jobs(
        self, keywords: str, location: str = "", limit: int = 10
    ) -> List[Dict]:
        """Search public LinkedIn job postings by keyword and location."""
        jobs = []
        start = 0

        logger.info(f"Searching LinkedIn jobs for '{keywords}' in '{location}' (limit: {limit})...")

        while len(jobs) < limit:
            params = {
                "keywords": keywords,
                "location": location,
                "start": start,
            }
            try:
                self._delay()
                response = self.session.get(LINKEDIN_SEARCH_API_URL, params=params, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"Search request failed with status code {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("li")

                if not job_cards:
                    # Also try finding job cards directly if not wrapped in <li>
                    job_cards = soup.find_all("div", class_="base-card")

                if not job_cards:
                    logger.info("No more job listings found in search results.")
                    break

                new_count = 0
                for card in job_cards:
                    if len(jobs) >= limit:
                        break

                    # Extract Job ID
                    entity_urn = card.find("div", {"data-entity-urn": True})
                    job_id = None
                    if entity_urn:
                        job_id = self.extract_job_id(entity_urn.get("data-entity-urn", ""))

                    card_link = card.find("a", class_="base-card__full-link")
                    job_url = card_link["href"] if card_link and "href" in card_link.attrs else ""

                    if not job_id and job_url:
                        job_id = self.extract_job_id(job_url)

                    if not job_id:
                        continue

                    # Extract Job Title
                    title_elem = card.find("h3", class_="base-search-card__title") or card.find("h3")
                    title = title_elem.get_text(strip=True) if title_elem else "N/A"

                    # Extract Company / Org Name
                    company_elem = (
                        card.find("h4", class_="base-search-card__subtitle")
                        or card.find("a", class_="hidden-nested-link")
                        or card.find("span", class_="job-search-card__company-name")
                    )
                    org_name = company_elem.get_text(strip=True) if company_elem else "N/A"

                    # Extract Location
                    location_elem = card.find("span", class_="job-search-card__location")
                    loc = location_elem.get_text(strip=True) if location_elem else "N/A"

                    # Extract Date Posted
                    time_elem = card.find("time")
                    date_posted = "N/A"
                    if time_elem:
                        date_posted = (
                            time_elem.get("datetime")
                            or time_elem.get_text(strip=True)
                        )

                    clean_url = f"https://www.linkedin.com/jobs/view/{job_id}"

                    job_info = {
                        "job_id": job_id,
                        "job_title": title,
                        "org_name": org_name,
                        "location": loc,
                        "date_posted": date_posted,
                        "job_url": clean_url,
                        "description": "",  # Will be fetched in detail call
                    }
                    jobs.append(job_info)
                    new_count += 1

                if new_count == 0:
                    break

                start += 25  # LinkedIn search pagination step

            except Exception as e:
                logger.error(f"Error while searching LinkedIn jobs: {e}")
                break

        logger.info(f"Retrieved {len(jobs)} job summaries.")
        return jobs

    def fetch_job_details(self, job_summary: Dict) -> Dict:
        """Fetch full job posting description and details for a given job summary."""
        job_id = job_summary.get("job_id")
        if not job_id:
            return job_summary

        url = LINKEDIN_JOB_DETAIL_URL.format(job_id=job_id)
        try:
            self._delay()
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract org name if not present
                if job_summary.get("org_name") in ["N/A", "", None]:
                    org_elem = (
                        soup.find("a", class_="topcard__org-name-link")
                        or soup.find("span", class_="topcard__flavor")
                    )
                    if org_elem:
                        job_summary["org_name"] = org_elem.get_text(strip=True)

                # Extract posting date if not present
                if job_summary.get("date_posted") in ["N/A", "", None]:
                    date_elem = soup.find("span", class_="posted-time-ago__text") or soup.find("time")
                    if date_elem:
                        job_summary["date_posted"] = date_elem.get_text(strip=True)

                # Extract full job description markup
                desc_elem = (
                    soup.find("div", class_="show-more-less-html__markup")
                    or soup.find("div", class_="description__text")
                    or soup.find("section", class_="description")
                )
                if desc_elem:
                    # Replace <br> and <p> tags with newlines for readable text
                    for br in desc_elem.find_all(["br", "p"]):
                        br.append("\n")
                    job_summary["description"] = desc_elem.get_text().strip()

        except Exception as e:
            logger.error(f"Failed to fetch details for Job ID {job_id}: {e}")

        return job_summary

    def fetch_job_by_url(self, job_url: str) -> Optional[Dict]:
        """Fetch job details directly from a single LinkedIn Job URL or ID."""
        job_id = self.extract_job_id(job_url)
        if not job_id:
            logger.warning(f"Could not parse Job ID from URL: {job_url}")
            return None

        initial_summary = {
            "job_id": job_id,
            "job_title": "N/A",
            "org_name": "N/A",
            "location": "N/A",
            "date_posted": "N/A",
            "job_url": f"https://www.linkedin.com/jobs/view/{job_id}",
            "description": "",
        }
        return self.fetch_job_details(initial_summary)
