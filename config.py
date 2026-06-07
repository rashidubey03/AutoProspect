from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    apollo_api_key: str | None
    prospeo_api_key: str | None
    brevo_api_key: str | None

    @classmethod
    def from_env(
        cls, *, require_keys: bool = False, load_env_file: bool = True
    ) -> "AppConfig":
        if load_env_file:
            load_dotenv()
        config = cls(
            apollo_api_key=getenv("APOLLO_API_KEY"),
            prospeo_api_key=getenv("PROSPEO_API_KEY"),
            brevo_api_key=getenv("BREVO_API_KEY"),
        )
        if require_keys:
            config.validate_required_keys()
        return config

    def validate_required_keys(self) -> None:
        missing = [
            name
            for name, value in {
                "APOLLO_API_KEY": self.apollo_api_key,
                "PROSPEO_API_KEY": self.prospeo_api_key,
                "BREVO_API_KEY": self.brevo_api_key,
            }.items()
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing required environment variables: " + ", ".join(missing)
            )


class ConfigError(RuntimeError):
    pass
