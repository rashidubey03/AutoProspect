import pytest

from services.apollo_service import ApolloError, ApolloService


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


def test_apollo_service_returns_ranked_unique_companies() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "organization": {
                        "primary_domain": "openai.com",
                        "name": "OpenAI",
                        "industry": "software",
                        "estimated_num_employees": 1000,
                        "keywords": ["ai", "automation"],
                        "technology_names": ["Python"],
                        "country": "united states",
                    }
                },
            ),
            FakeResponse(
                200,
                {
                    "organizations": [
                        {
                            "primary_domain": "cohere.com",
                            "name": "Cohere",
                            "industry": "software",
                            "estimated_num_employees": 800,
                            "keywords": ["ai"],
                            "technology_names": ["Python"],
                            "country": "united states",
                        },
                        {
                            "primary_domain": "openai.com",
                            "name": "OpenAI Duplicate",
                            "industry": "software",
                        },
                        {
                            "primary_domain": "example.com",
                            "name": "Example",
                            "industry": "retail",
                        },
                    ]
                },
            ),
        ]
    )

    companies = ApolloService("test-key", session=session).find_similar_companies(
        "openai.com", limit=2, per_page=25, max_pages=1
    )

    assert [company.domain for company in companies] == ["cohere.com", "example.com"]
    assert companies[0].name == "Cohere"
    assert companies[0].industry == "software"


def test_apollo_service_sets_auth_header_and_search_filters() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "organization": {
                        "primary_domain": "openai.com",
                        "industry": "software",
                        "estimated_num_employees": 300,
                        "keywords": ["ai"],
                        "technology_names": ["Google Analytics"],
                        "country": "united states",
                    }
                },
            ),
            FakeResponse(200, {"organizations": []}),
        ]
    )

    ApolloService("test-key", session=session).find_similar_companies("openai.com")

    enrich_request, search_request = session.requests
    assert enrich_request["headers"]["X-Api-Key"] == "test-key"
    assert search_request["method"] == "POST"
    assert ("q_organization_keyword_tags[]", "software") in search_request["params"]
    assert ("organization_num_employees_ranges[]", "201,500") in search_request["params"]
    assert ("currently_using_any_of_technology_uids[]", "google_analytics") in search_request["params"]


def test_apollo_service_retries_rate_limits() -> None:
    session = FakeSession(
        [
            FakeResponse(429, {}),
            FakeResponse(429, {}),
            FakeResponse(429, {}),
        ]
    )

    service = ApolloService("test-key", session=session, backoff_seconds=0)

    with pytest.raises(ApolloError):
        service.find_similar_companies("openai.com")

    assert len(session.requests) == 3
