import pytest

from models import Company
from services.prospeo_service import (
    ProspeoAuthError,
    ProspeoError,
    ProspeoPermissionError,
    ProspeoRateLimitError,
    ProspeoService,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    def request(self, method: str, url: str, **kwargs) -> FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def test_prospeo_role_filtering_patterns() -> None:
    service = ProspeoService("dummy-key")
    
    # Matching titles
    assert service._title_matches_roles("CEO") is True
    assert service._title_matches_roles("Co-Founder") is True
    assert service._title_matches_roles("Co Founder & CTO") is True
    assert service._title_matches_roles("VP of Engineering") is True
    assert service._title_matches_roles("Vice President of Sales") is True
    assert service._title_matches_roles("Head of Growth & Marketing") is True
    assert service._title_matches_roles("founder & ceo") is True

    # Non-matching titles
    assert service._title_matches_roles("Software Engineer") is False
    assert service._title_matches_roles("Office Coordinator") is False
    assert service._title_matches_roles("Recruiter") is False
    assert service._title_matches_roles("VP of Finance") is False
    assert service._title_matches_roles("") is False
    assert service._title_matches_roles(None) is False


def test_prospeo_service_success() -> None:
    # We will mock two API calls:
    # 1. POST /search-person
    # 2. POST /enrich-person for the matching candidate
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "results": [
                        {
                            "person": {
                                "person_id": "p1",
                                "first_name": "Elon",
                                "last_name": "Musk",
                                "current_job_title": "CEO & Founder",
                                "linkedin_url": "https://linkedin.com/in/elon",
                            }
                        },
                        {
                            "person": {
                                "person_id": "p2",
                                "first_name": "John",
                                "last_name": "Doe",
                                "current_job_title": "Software Developer",
                                "linkedin_url": "https://linkedin.com/in/john",
                            }
                        },
                        {
                            "person": {
                                "person_id": "p3",
                                "first_name": "NoLinkedIn",
                                "last_name": "Person",
                                "current_job_title": "CTO",
                                "linkedin_url": None,
                            }
                        },
                    ]
                },
            ),
            # Enrichment for Elon
            FakeResponse(
                200,
                {
                    "error": False,
                    "person": {
                        "email": {
                            "email": "elon@spacex.com",
                            "status": "VERIFIED",
                        }
                    },
                },
            ),
        ]
    )

    service = ProspeoService("dummy-key", session=session)
    contacts = service.find_decision_makers(Company("spacex.com"))

    # Verify results
    assert len(contacts) == 1
    assert contacts[0].name == "Elon Musk"
    assert contacts[0].title == "CEO & Founder"
    assert contacts[0].linkedin_url == "https://linkedin.com/in/elon"
    assert contacts[0].email == "elon@spacex.com"
    assert contacts[0].email_verified is True

    # Check request endpoints
    assert len(session.requests) == 2
    assert session.requests[0]["url"].endswith("/search-person")
    assert session.requests[1]["url"].endswith("/enrich-person")
    assert session.requests[0]["headers"]["X-KEY"] == "dummy-key"


def test_prospeo_service_retries_transient_errors() -> None:
    session = FakeSession(
        [
            FakeResponse(500, {}),
            FakeResponse(429, {}),
            FakeResponse(502, {}),
        ]
    )

    service = ProspeoService("dummy-key", session=session, backoff_seconds=0)

    with pytest.raises(ProspeoError, match="request failed after 3 attempts"):
        service.find_decision_makers(Company("test.com"))

    assert len(session.requests) == 3


def test_prospeo_service_does_not_retry_auth_errors() -> None:
    session = FakeSession([FakeResponse(401, {})])

    service = ProspeoService("dummy-key", session=session, backoff_seconds=0)

    with pytest.raises(ProspeoAuthError):
        service.find_decision_makers(Company("test.com"))

    assert len(session.requests) == 1


def test_prospeo_service_does_not_retry_permission_errors() -> None:
    session = FakeSession([FakeResponse(403, {})])

    service = ProspeoService("dummy-key", session=session, backoff_seconds=0)

    with pytest.raises(ProspeoPermissionError):
        service.find_decision_makers(Company("test.com"))

    assert len(session.requests) == 1
