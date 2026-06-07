from models import Company, Contact, EmailPayload
from orchestrator import Pipeline
from orchestrator.pipeline import PipelineResult


class FakeCompanyDiscovery:
    def find_similar_companies(self, domain: str) -> list[Company]:
        return [
            Company(domain="anthropic.com"),
            Company(domain="cohere.com"),
            Company(domain="broken.example"),
        ]


class FakeContactDiscovery:
    def find_decision_makers(self, company: Company) -> list[Contact]:
        if company.domain == "broken.example":
            raise RuntimeError("provider error")
        return [
            Contact(
                name=f"Lead at {company.domain}",
                title="CTO",
                linkedin_url=f"https://linkedin.com/in/{company.domain}",
                email="lead@example.com",
                email_verified=True,
            )
        ]


class FakeEmailGenerator:
    def generate(self, contacts: list[Contact]) -> list[EmailPayload]:
        return [
            EmailPayload(
                recipient=contact.email or "",
                subject="Quick Question",
                body=f"Hi {contact.name}",
            )
            for contact in contacts
        ]


class ApproveSending:
    def approve(self, result: PipelineResult) -> bool:
        return True


class FakeEmailSender:
    def send_all(self, emails: list[EmailPayload]) -> tuple[int, tuple[str, ...]]:
        return len(emails) - 1, (emails[-1].recipient,)


class ContactDiscoveryWithMissingLinkedIn:
    def find_decision_makers(self, company: Company) -> list[Contact]:
        return [
            Contact(name="No LinkedIn", title="CEO", linkedin_url=""),
            Contact(
                name="Has LinkedIn",
                title="CTO",
                linkedin_url="https://linkedin.com/in/has",
                email="has@example.com",
                email_verified=True,
            ),
        ]


class ContactDiscoveryWithEmailSkips:
    def find_decision_makers(self, company: Company) -> list[Contact]:
        return [
            Contact(
                name="Missing Email",
                title="CEO",
                linkedin_url="https://linkedin.com/in/missing",
            ),
            Contact(
                name="Unverified Email",
                title="CTO",
                linkedin_url="https://linkedin.com/in/unverified",
                email="unverified@example.com",
                email_verified=False,
            ),
            Contact(
                name="Verified Email",
                title="Founder",
                linkedin_url="https://linkedin.com/in/verified",
                email="verified@example.com",
                email_verified=True,
            ),
        ]


def test_pipeline_collects_summary_counts_with_injected_services() -> None:
    result = Pipeline(
        company_discovery=FakeCompanyDiscovery(),
        contact_discovery=FakeContactDiscovery(),
        email_generator=FakeEmailGenerator(),
        confirmation=ApproveSending(),
        email_sender=FakeEmailSender(),
    ).run("openai.com")

    assert result.to_dict() == {
        "domain": "openai.com",
        "companies_found": 3,
        "contacts_found": 2,
        "verified_emails": 2,
        "emails_prepared": 2,
        "emails_sent": 1,
        "emails_failed": 1,
        "failed_recipients": ["lead@example.com"],
    }


def test_default_confirmation_blocks_sending() -> None:
    result = Pipeline().run("openai.com")

    assert result.emails_sent == 0
    assert result.emails_failed == 0


def test_pipeline_skips_contacts_without_linkedin() -> None:
    result = Pipeline(
        company_discovery=lambda_domain_company_discovery(),
        contact_discovery=ContactDiscoveryWithMissingLinkedIn(),
        email_generator=FakeEmailGenerator(),
        confirmation=ApproveSending(),
        email_sender=FakeEmailSender(),
    ).run("openai.com")

    assert result.contacts_found == 2
    assert result.verified_emails == 1


def test_pipeline_skips_missing_and_unverified_emails() -> None:
    result = Pipeline(
        company_discovery=lambda_domain_company_discovery(),
        contact_discovery=ContactDiscoveryWithEmailSkips(),
        email_generator=FakeEmailGenerator(),
        confirmation=ApproveSending(),
        email_sender=FakeEmailSender(),
    ).run("openai.com")

    assert result.contacts_found == 3
    assert result.verified_emails == 1
    assert result.failed_recipients == ("verified@example.com",)


class lambda_domain_company_discovery:
    def find_similar_companies(self, domain: str) -> list[Company]:
        return [Company(domain="anthropic.com")]
