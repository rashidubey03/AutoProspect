import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from models import Company, Contact, EmailPayload


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    domain: str
    companies_found: int
    contacts_found: int
    verified_emails: int
    emails_prepared: int
    emails_sent: int
    emails_failed: int
    failed_recipients: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, int | str | list[str]]:
        return {
            "domain": self.domain,
            "companies_found": self.companies_found,
            "contacts_found": self.contacts_found,
            "verified_emails": self.verified_emails,
            "emails_prepared": self.emails_prepared,
            "emails_sent": self.emails_sent,
            "emails_failed": self.emails_failed,
            "failed_recipients": list(self.failed_recipients),
        }


class CompanyDiscoveryService:
    def find_similar_companies(self, domain: str) -> list[Company]:
        logger.info("Apollo.io integration pending; returning no companies")
        return []


class ContactDiscoveryService:
    def find_decision_makers(self, company: Company) -> list[Contact]:
        logger.info("Prospeo integration pending for %s; returning no contacts", company.domain)
        return []


class EmailGenerator:
    def generate(self, contacts: Sequence[Contact]) -> list[EmailPayload]:
        logger.info("Email template generation pending; returning no payloads")
        return []


class ConfirmationService:
    def approve(self, result: PipelineResult) -> bool:
        logger.info("Confirmation checkpoint pending; defaulting to no sends")
        return False


class EmailSendingService:
    def send_all(self, emails: Sequence[EmailPayload]) -> tuple[int, tuple[str, ...]]:
        logger.info("Brevo integration pending; returning no sends")
        return 0, ()


class Pipeline:
    def __init__(
        self,
        *,
        company_discovery: CompanyDiscoveryService | None = None,
        contact_discovery: ContactDiscoveryService | None = None,
        email_generator: EmailGenerator | None = None,
        confirmation: ConfirmationService | None = None,
        email_sender: EmailSendingService | None = None,
    ) -> None:
        self.company_discovery = company_discovery or CompanyDiscoveryService()
        self.contact_discovery = contact_discovery or ContactDiscoveryService()
        self.email_generator = email_generator or EmailGenerator()
        self.confirmation = confirmation or ConfirmationService()
        self.email_sender = email_sender or EmailSendingService()

    def run(self, domain: str) -> PipelineResult:
        logger.info("Starting pipeline")
        logger.info("Domain: %s", domain)

        companies = self.company_discovery.find_similar_companies(domain)
        logger.info("Found %s companies", len(companies))

        contacts = self._find_contacts(companies)
        logger.info("Found %s contacts", len(contacts))

        verified_contacts = self._filter_verified_contacts(contacts)
        logger.info("Found %s verified emails", len(verified_contacts))

        email_payloads = self.email_generator.generate(verified_contacts)
        logger.info("Prepared %s emails", len(email_payloads))

        pending_result = PipelineResult(
            domain=domain,
            companies_found=len(companies),
            contacts_found=len(contacts),
            verified_emails=len(verified_contacts),
            emails_prepared=len(email_payloads),
            emails_sent=0,
            emails_failed=0,
        )

        if not self.confirmation.approve(pending_result):
            logger.info("Sending aborted before Brevo stage")
            return pending_result

        logger.info("Sending emails...")
        sent_count, failed_recipients = self.email_sender.send_all(email_payloads)
        failed_count = len(failed_recipients)
        logger.info("Sent: %s", sent_count)
        logger.error("Failed: %s", failed_count)
        logger.info("Pipeline complete")

        return PipelineResult(
            domain=domain,
            companies_found=len(companies),
            contacts_found=len(contacts),
            verified_emails=len(verified_contacts),
            emails_prepared=len(email_payloads),
            emails_sent=sent_count,
            emails_failed=failed_count,
            failed_recipients=failed_recipients,
        )

    def _find_contacts(self, companies: Iterable[Company]) -> list[Contact]:
        contacts: list[Contact] = []
        for company in companies:
            try:
                contacts.extend(self.contact_discovery.find_decision_makers(company))
            except Exception as error:
                logger.error("Failed contact discovery for %s: %s", company.domain, error)
        return contacts

    def _filter_verified_contacts(self, contacts: Iterable[Contact]) -> list[Contact]:
        verified_contacts: list[Contact] = []
        for contact in contacts:
            if not contact.linkedin_url:
                logger.warning("Skipping contact without LinkedIn URL: %s", contact.name)
                continue
            if not contact.email:
                logger.warning("Skipping contact without email: %s", contact.name)
                continue
            if not contact.email_verified:
                logger.warning("Skipping contact with unverified email: %s", contact.email)
                continue
            verified_contacts.append(contact)
        return verified_contacts
