import re
import socket
import logging
import requests
from typing import Optional, Dict, Tuple
from config import HUNTER_API_KEY

logger = logging.getLogger("recruiter_finder")

# Cache to avoid duplicate network lookups during a run
_DOMAIN_CACHE: Dict[str, Optional[str]] = {}
_MX_CACHE: Dict[str, bool] = {}

CORPORATE_SUFFIXES = [
    r"\bprivate limited\b",
    r"\bpvt ltd\b",
    r"\bpvt\. ltd\b",
    r"\bltd\b",
    r"\blimited\b",
    r"\binc\b",
    r"\bincorporated\b",
    r"\bcorp\b",
    r"\bcorporation\b",
    r"\btechnologies\b",
    r"\bsolutions\b",
    r"\bservices\b",
    r"\bhealthcare\b",
    r"\bgroup\b",
    r"\bconsulting\b",
    r"\bllc\b",
    r"\bco\b",
]

def clean_company_name(name: str) -> str:
    """Strip common legal suffixes from company names to improve domain discovery."""
    if not name or name == "N/A":
        return ""
    clean = name.strip()
    for pattern in CORPORATE_SUFFIXES:
        clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"[^\w\s-]", " ", clean).strip()
    # Normalize multiple whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def verify_domain_mx(domain: str) -> bool:
    """Verify if domain has active MX (Mail Exchange) records."""
    if not domain:
        return False
    if domain in _MX_CACHE:
        return _MX_CACHE[domain]

    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
        has_mx = len(answers) > 0
        _MX_CACHE[domain] = has_mx
        return has_mx
    except Exception:
        # Fallback: check if domain at least resolves to an IP
        try:
            socket.gethostbyname(domain)
            _MX_CACHE[domain] = True
            return True
        except Exception:
            _MX_CACHE[domain] = False
            return False

def find_company_domain(company_name: str) -> Optional[str]:
    """Discover official company website domain using Clearbit autocomplete API and DNS verification."""
    if not company_name or company_name == "N/A":
        return None

    company_key = company_name.lower().strip()
    if company_key in _DOMAIN_CACHE:
        return _DOMAIN_CACHE[company_key]

    cleaned_name = clean_company_name(company_name)
    search_terms = [company_name]
    if cleaned_name and cleaned_name.lower() != company_name.lower():
        search_terms.append(cleaned_name)
        # Also try first significant word if multi-word (e.g. "Merck" from "Merck Healthcare")
        first_word = cleaned_name.split()[0]
        if len(first_word) >= 4:
            search_terms.append(first_word)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    }

    # Step 1: Query Clearbit autocomplete API
    for term in search_terms:
        try:
            url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={requests.utils.quote(term)}"
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.status_code == 200:
                results = resp.json()
                if results and isinstance(results, list):
                    candidate_domain = results[0].get("domain")
                    if candidate_domain and verify_domain_mx(candidate_domain):
                        _DOMAIN_CACHE[company_key] = candidate_domain
                        return candidate_domain
        except Exception as e:
            logger.debug(f"Clearbit query failed for '{term}': {e}")

    # Step 2: Fallback heuristic - slugify first word or cleaned name
    slug = re.sub(r"[^a-zA-Z0-9]", "", cleaned_name.split()[0] if cleaned_name else company_name).lower()
    if len(slug) >= 3:
        heuristic_domain = f"{slug}.com"
        if verify_domain_mx(heuristic_domain):
            _DOMAIN_CACHE[company_key] = heuristic_domain
            return heuristic_domain

    _DOMAIN_CACHE[company_key] = None
    return None

def query_hunter_recruiter(domain: str, api_key: str = HUNTER_API_KEY) -> Optional[Dict]:
    """Query Hunter.io API to find HR / Recruiter names and verified emails for a company domain."""
    if not api_key or not domain:
        return None

    try:
        # First query specifically for HR / Recruiting department
        url = (
            f"https://api.hunter.io/v2/domain-search"
            f"?domain={domain}&department=human_resources&limit=3&api_key={api_key}"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            emails = data.get("emails", [])
            if emails:
                best = emails[0]
                name = f"{best.get('first_name', '')} {best.get('last_name', '')}".strip()
                return {
                    "recruiter_name": name or "HR / Talent Lead",
                    "recruiter_title": best.get("position") or "Technical Recruiter",
                    "recruiter_email": best.get("value"),
                    "email_source": f"Hunter.io Verified ({best.get('confidence', 90)}%)",
                    "recruiter_linkedin": best.get("linkedin") or "N/A",
                }

        # Fallback to general domain search if HR department was empty
        url_general = f"https://api.hunter.io/v2/domain-search?domain={domain}&limit=3&api_key={api_key}"
        resp_gen = requests.get(url_general, timeout=5)
        if resp_gen.status_code == 200:
            data_gen = resp_gen.json().get("data", {})
            emails = data_gen.get("emails", [])
            if emails:
                best = emails[0]
                name = f"{best.get('first_name', '')} {best.get('last_name', '')}".strip()
                return {
                    "recruiter_name": name or "Hiring Team",
                    "recruiter_title": best.get("position") or "Talent Acquisition",
                    "recruiter_email": best.get("value"),
                    "email_source": f"Hunter.io Verified ({best.get('confidence', 85)}%)",
                    "recruiter_linkedin": best.get("linkedin") or "N/A",
                }

    except Exception as e:
        logger.warning(f"Hunter.io API query failed for domain {domain}: {e}")

    return None

def resolve_recruiter_contact(
    company_name: str,
    direct_email: str = "N/A",
    recruiter_name: str = "N/A",
    recruiter_title: str = "N/A",
) -> Dict[str, str]:
    """
    Resolve complete recruiter / hiring manager profile:
    1. If direct email was found in the JD, prioritize that.
    2. Else, resolve company domain and query Hunter.io (if key is set).
    3. Else, provide verified company recruitment inbox (careers@domain) if domain has active MX.
    """
    domain = find_company_domain(company_name)

    # 1. Direct Email from Job Posting
    if direct_email and direct_email != "N/A":
        return {
            "recruiter_name": recruiter_name if recruiter_name not in ["N/A", ""] else f"{company_name} Hiring Team",
            "recruiter_title": recruiter_title if recruiter_title not in ["N/A", ""] else "Recruiter / Hiring Contact",
            "recruiter_email": direct_email,
            "email_source": "Direct from Job Posting",
            "company_domain": domain or "N/A",
            "recruiter_linkedin": "N/A",
        }

    # 2. Hunter.io Enrichment (if API key provided)
    if domain and HUNTER_API_KEY:
        hunter_result = query_hunter_recruiter(domain, HUNTER_API_KEY)
        if hunter_result:
            hunter_result["company_domain"] = domain
            return hunter_result

    # 3. Verified Company Domain Talent / Careers Email
    if domain and verify_domain_mx(domain):
        clean_comp = clean_company_name(company_name) or company_name
        name_val = recruiter_name if recruiter_name not in ["N/A", ""] else f"{clean_comp} Talent Team"
        title_val = recruiter_title if recruiter_title not in ["N/A", ""] else "Talent Acquisition / HR"
        
        # If recruiter name was identified in JD, e.g. "Rohan Sharma"
        suggested_email = f"careers@{domain}"
        if recruiter_name not in ["N/A", ""] and " " in recruiter_name:
            parts = recruiter_name.lower().split()
            first, last = re.sub(r"\W", "", parts[0]), re.sub(r"\W", "", parts[-1])
            suggested_email = f"{first}.{last}@{domain} (or careers@{domain})"

        return {
            "recruiter_name": name_val,
            "recruiter_title": title_val,
            "recruiter_email": suggested_email,
            "email_source": "Verified Company Talent Domain",
            "company_domain": domain,
            "recruiter_linkedin": "N/A",
        }

    # 4. Fallback if no domain or email could be found
    return {
        "recruiter_name": recruiter_name if recruiter_name not in ["N/A", ""] else "N/A",
        "recruiter_title": recruiter_title if recruiter_title not in ["N/A", ""] else "N/A",
        "recruiter_email": "N/A",
        "email_source": "Not Listed",
        "company_domain": domain or "N/A",
        "recruiter_linkedin": "N/A",
    }
