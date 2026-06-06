from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    domain: str
    name: str | None = None
    industry: str | None = None
