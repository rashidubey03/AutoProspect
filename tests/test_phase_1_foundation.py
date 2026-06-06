import pytest

from config import AppConfig
from models import Company
from utils.dedupe import unique_by
from utils.validators import DomainValidationError, normalize_domain


def test_normalize_domain_removes_protocol_and_path() -> None:
    assert normalize_domain("https://OpenAI.com/") == "openai.com"
    assert normalize_domain("http://example.com/path") == "example.com"


def test_normalize_domain_rejects_invalid_domain() -> None:
    with pytest.raises(DomainValidationError):
        normalize_domain("not-a-domain")


def test_unique_by_keeps_first_item_for_each_key() -> None:
    companies = [
        Company(domain="openai.com"),
        Company(domain="anthropic.com"),
        Company(domain="openai.com", name="Duplicate"),
    ]

    unique_companies = unique_by(companies, key=lambda company: company.domain)

    assert unique_companies == companies[:2]


def test_config_loads_without_requiring_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in (
        "APOLLO_API_KEY",
        "PROSPEO_API_KEY",
        "EAZYREACH_API_KEY",
        "BREVO_API_KEY",
    ):
        monkeypatch.delenv(env_name, raising=False)

    config = AppConfig.from_env()

    assert config.apollo_api_key is None
    assert config.prospeo_api_key is None
    assert config.eazyreach_api_key is None
    assert config.brevo_api_key is None
