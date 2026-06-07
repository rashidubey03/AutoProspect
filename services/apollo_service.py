import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from models import Company
from utils.dedupe import unique_by


logger = logging.getLogger(__name__)


class ApolloError(RuntimeError):
    pass


class ApolloRateLimitError(ApolloError):
    pass


class ApolloAuthError(ApolloError):
    pass


class ApolloPermissionError(ApolloError):
    pass


@dataclass(frozen=True)
class ApolloCompanyProfile:
    domain: str
    name: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)
    technologies: tuple[str, ...] = field(default_factory=tuple)
    location: str | None = None


class ApolloService:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.apollo.io/api/v1",
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key:
            raise ApolloError("Apollo API key is required.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = session or requests.Session()

    def find_similar_companies(
        self, domain: str, *, limit: int = 20, per_page: int = 25, max_pages: int = 5
    ) -> list[Company]:
        profile = self._enrich_company(domain)
        logger.info("Apollo metadata loaded for %s", domain)

        candidates: list[ApolloCompanyProfile] = []
        for page in range(1, max_pages + 1):
            page_candidates = self._search_companies(profile, page=page, per_page=per_page)
            logger.info("Apollo page %s returned %s companies", page, len(page_candidates))
            candidates.extend(page_candidates)
            if len(candidates) >= limit or len(page_candidates) < per_page:
                break

        unique_candidates = unique_by(
            (candidate for candidate in candidates if candidate.domain != domain),
            key=lambda candidate: candidate.domain,
        )
        ranked = sorted(
            unique_candidates,
            key=lambda candidate: self._similarity_score(profile, candidate),
            reverse=True,
        )
        companies = [
            Company(domain=candidate.domain, name=candidate.name, industry=candidate.industry)
            for candidate in ranked[:limit]
        ]
        logger.info("Apollo retained %s similar companies", len(companies))
        return companies

    def _enrich_company(self, domain: str) -> ApolloCompanyProfile:
        response = self._request(
            "GET",
            "/organizations/enrich",
            params={"domain": domain},
        )
        payload = response.json()
        organization = payload.get("organization") or payload.get("account") or payload
        if not isinstance(organization, dict):
            raise ApolloError("Apollo enrichment response did not include an organization.")
        return self._profile_from_payload(organization, fallback_domain=domain)

    def _search_companies(
        self, profile: ApolloCompanyProfile, *, page: int, per_page: int
    ) -> list[ApolloCompanyProfile]:
        params = self._search_params(profile, page=page, per_page=per_page)
        response = self._request("POST", "/mixed_companies/search", params=params)
        payload = response.json()
        organizations = payload.get("organizations") or payload.get("accounts") or []
        if not isinstance(organizations, list):
            raise ApolloError("Apollo search response did not include organizations.")
        return [
            self._profile_from_payload(organization)
            for organization in organizations
            if isinstance(organization, dict) and self._extract_domain(organization)
        ]

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Accept": "application/json",
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
                    logger.warning("Apollo rate limit hit for %s", path)
                    raise ApolloRateLimitError("Apollo rate limit reached.")
                if response.status_code == 401:
                    raise ApolloAuthError(
                        "Apollo API key was rejected. Check APOLLO_API_KEY in .env."
                    )
                if response.status_code == 403:
                    raise ApolloPermissionError(
                        "Apollo returned 403 for this endpoint. Your API key or Apollo plan likely lacks access to Organization Search."
                    )
                if response.status_code >= 500:
                    raise ApolloError(f"Apollo transient error: {response.status_code}")
                if response.status_code >= 400:
                    raise ApolloError(f"Apollo API error: {response.status_code}")
                return response
            except (ApolloAuthError, ApolloPermissionError):
                raise
            except (requests.RequestException, ApolloRateLimitError, ApolloError) as error:
                last_error = error
                if attempt == self.max_retries:
                    break
                time.sleep(delay)
                delay *= 2
        raise ApolloError(f"Apollo request failed after {self.max_retries} attempts") from last_error

    def _search_params(
        self, profile: ApolloCompanyProfile, *, page: int, per_page: int
    ) -> list[tuple[str, str | int]]:
        params: list[tuple[str, str | int]] = [("page", page), ("per_page", per_page)]

        keyword_values = [value for value in (profile.industry, *profile.keywords) if value]
        for keyword in keyword_values[:5]:
            params.append(("q_organization_keyword_tags[]", keyword))

        if profile.employee_count:
            params.append(("organization_num_employees_ranges[]", self._employee_range(profile.employee_count)))
        if profile.location:
            params.append(("organization_locations[]", profile.location))
        for technology in profile.technologies[:5]:
            params.append(("currently_using_any_of_technology_uids[]", self._technology_uid(technology)))
        return params

    def _profile_from_payload(
        self, payload: dict[str, Any], *, fallback_domain: str | None = None
    ) -> ApolloCompanyProfile:
        domain = self._extract_domain(payload) or fallback_domain
        if not domain:
            raise ApolloError("Apollo company payload is missing a domain.")
        return ApolloCompanyProfile(
            domain=domain.lower(),
            name=payload.get("name"),
            industry=payload.get("industry") or payload.get("industry_tag"),
            employee_count=self._extract_employee_count(payload),
            keywords=tuple(self._extract_values(payload.get("keywords") or payload.get("keywords_list"))),
            technologies=tuple(self._extract_values(payload.get("technology_names") or payload.get("technologies"))),
            location=self._extract_location(payload),
        )

    def _similarity_score(
        self, source: ApolloCompanyProfile, candidate: ApolloCompanyProfile
    ) -> int:
        score = 0
        if source.industry and source.industry == candidate.industry:
            score += 4
        if source.location and source.location == candidate.location:
            score += 1
        if source.employee_count and candidate.employee_count:
            score += max(0, 3 - abs(self._employee_bucket(source.employee_count) - self._employee_bucket(candidate.employee_count)))
        score += len(set(source.keywords).intersection(candidate.keywords))
        score += len(set(source.technologies).intersection(candidate.technologies))
        return score

    def _extract_domain(self, payload: dict[str, Any]) -> str | None:
        domain = payload.get("primary_domain") or payload.get("domain") or payload.get("website_url")
        if not isinstance(domain, str):
            return None
        return domain.replace("https://", "").replace("http://", "").replace("www.", "").split("/", 1)[0]

    def _extract_employee_count(self, payload: dict[str, Any]) -> int | None:
        value = payload.get("estimated_num_employees") or payload.get("num_employees")
        return value if isinstance(value, int) else None

    def _extract_location(self, payload: dict[str, Any]) -> str | None:
        for key in ("city", "state", "country"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value.lower()
        return None

    def _extract_values(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        normalized: list[str] = []
        for value in values:
            if isinstance(value, str):
                normalized.append(value.lower())
            elif isinstance(value, dict) and isinstance(value.get("name"), str):
                normalized.append(value["name"].lower())
        return normalized

    def _employee_range(self, employee_count: int) -> str:
        ranges = [(1, 10), (11, 50), (51, 200), (201, 500), (501, 1000), (1001, 5000), (5001, 10000), (10001, 20000)]
        for lower, upper in ranges:
            if lower <= employee_count <= upper:
                return f"{lower},{upper}"
        return "20001,100000"

    def _employee_bucket(self, employee_count: int) -> int:
        return int(self._employee_range(employee_count).split(",", 1)[0])

    def _technology_uid(self, technology: str) -> str:
        return technology.lower().replace(".", "_").replace(" ", "_")
