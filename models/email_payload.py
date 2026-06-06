from dataclasses import dataclass


@dataclass(frozen=True)
class EmailPayload:
    recipient: str
    subject: str
    body: str
