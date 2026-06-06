from dataclasses import dataclass


@dataclass
class Contact:
    name: str
    title: str
    linkedin_url: str
    email: str | None = None
