import logging
import re
import time
from typing import Any
import requests

from models import Company, Contact

logger = logging.getLogger(__name__)


class ProspeoError(RuntimeError):
    pass


class ProspeoRateLimitError(ProspeoError):
    pass


class ProspeoAuthError(ProspeoError):
    pass


class ProspeoPermissionError(ProspeoError):
    pass


class ProspeoService:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.prospeo.io",
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key:
            raise ProspeoError("Prospeo API key is required.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = session or requests.Session()

    def find_decision_makers(self, company: Company) -> list[Contact]:
        logger.info("Prospeo querying contacts for domain: %s", company.domain)

        payload = {
            "page": 1,
            "filters": {
                "company": {
                    "domains": {
                        "include": [company.domain]
                    }
                }
            }
        }

        try:
            response = self._request("POST", "/search-person", json=payload)
        except Exception as error:
            logger.error("Prospeo search-person failed for domain %s: %s", company.domain, error)
            raise

        search_result = response.json()
        results = search_result.get("results") or []
        if not isinstance(results, list):
            logger.warning("Prospeo search results is not a list for domain: %s", company.domain)
            return []

        candidates = []
        seen_keys = set()
        for item in results:
            if not isinstance(item, dict):
                continue
            person = item.get("person")
            if not isinstance(person, dict):
                continue

            first_name = person.get("first_name") or ""
            last_name = person.get("last_name") or ""
            full_name = person.get("full_name") or f"{first_name} {last_name}".strip()
            title = person.get("current_job_title") or person.get("headline") or ""
            linkedin_url = person.get("linkedin_url")
            person_id = person.get("person_id")

            if not full_name:
                continue

            if not self._title_matches_roles(title):
                continue

            dedupe_key = person_id or linkedin_url or full_name
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            candidates.append({
                "name": full_name,
                "title": title,
                "linkedin_url": linkedin_url,
                "person_id": person_id
            })

        logger.info("Prospeo found %d matching decision maker candidates for domain %s", len(candidates), company.domain)

        contacts = []
        for cand in candidates:
            if not cand["linkedin_url"]:
                logger.warning("Skipping contact %s: missing LinkedIn URL", cand["name"])
                continue

            enrich_payload = {
                "only_verified_email": True,
                "data": {}
            }
            if cand["person_id"]:
                enrich_payload["data"]["person_id"] = cand["person_id"]
            else:
                enrich_payload["data"]["linkedin_url"] = cand["linkedin_url"]

            try:
                enrich_response = self._request("POST", "/enrich-person", json=enrich_payload)
                enrich_result = enrich_response.json()

                if enrich_result.get("error"):
                    err_msg = enrich_result.get("message") or "Unknown enrichment error"
                    logger.warning("Prospeo enrichment error for contact %s: %s", cand["name"], err_msg)
                    continue

                person_data = enrich_result.get("person") or {}

                email_val = None
                email_status = None
                email_data = person_data.get("email")
                if isinstance(email_data, dict):
                    email_val = email_data.get("email")
                    email_status = email_data.get("status")
                elif isinstance(email_data, str):
                    email_val = email_data
                    email_status = person_data.get("email_status")

                if not email_val:
                    logger.warning("Skipping contact %s: empty email response", cand["name"])
                    continue

                is_verified = False
                if email_status and email_status.upper() == "VERIFIED":
                    is_verified = True

                if not is_verified:
                    logger.warning("Skipping contact %s: email status is %s (not VERIFIED)", cand["name"], email_status)
                    continue

                contact = Contact(
                    name=cand["name"],
                    title=cand["title"],
                    linkedin_url=cand["linkedin_url"],
                    email=email_val,
                    email_verified=is_verified
                )
                contacts.append(contact)
            except Exception as enrich_error:
                logger.warning("Failed to enrich contact %s: %s", cand["name"], enrich_error)
                continue

        logger.info("Prospeo successfully verified %d contacts for domain %s", len(contacts), company.domain)
        return contacts

    def _title_matches_roles(self, title: str) -> bool:
        if not title:
            return False
        title_lower = title.lower()
        patterns = [
            r'\bceo\b',
            r'\bcto\b',
            r'\bfounder\b',
            r'\bco-founder\b',
            r'\bco\s+founder\b',
            r'\bvp\s+engineering\b',
            r'\bvp\s+of\s+engineering\b',
            r'\bvp\s+product\b',
            r'\bvp\s+of\s+product\b',
            r'\bvp\s+sales\b',
            r'\bvp\s+of\s+sales\b',
            r'\bvice\s+president\s+of\s+engineering\b',
            r'\bvice\s+president\s+of\s+product\b',
            r'\bvice\s+president\s+of\s+sales\b',
            r'\bhead\s+of\s+growth\b'
        ]
        for pattern in patterns:
            if re.search(pattern, title_lower):
                return True
        return False

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {
            "X-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        delay = self.backoff_seconds
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                if response.status_code == 429:
                    logger.warning("Prospeo rate limit hit for %s", path)
                    raise ProspeoRateLimitError("Prospeo rate limit reached.")
                if response.status_code == 401:
                    raise ProspeoAuthError(
                        "Prospeo API key was rejected. Check PROSPEO_API_KEY in .env."
                    )
                if response.status_code == 403:
                    raise ProspeoPermissionError(
                        "Prospeo returned 403. Your API key or plan lacks access."
                    )
                if response.status_code >= 500:
                    raise ProspeoError(f"Prospeo transient error: {response.status_code}")
                if response.status_code >= 400:
                    raise ProspeoError(f"Prospeo API error: {response.status_code}")
                return response
            except (ProspeoAuthError, ProspeoPermissionError):
                raise
            except (requests.RequestException, ProspeoRateLimitError, ProspeoError) as error:
                last_error = error
                if attempt == self.max_retries:
                    break
                time.sleep(delay)
                delay *= 2
        raise ProspeoError(f"Prospeo request failed after {self.max_retries} attempts") from last_error
