import re


DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$"
)


class DomainValidationError(ValueError):
    pass


def normalize_domain(value: str) -> str:
    if value is None:
        raise DomainValidationError("Domain is required.")

    domain = value.strip().lower()
    if not domain:
        raise DomainValidationError("Domain is required.")

    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/", 1)[0]
    domain = domain.strip().rstrip(".")

    if not DOMAIN_PATTERN.match(domain):
        raise DomainValidationError(f"Invalid domain format: {value}")

    return domain
