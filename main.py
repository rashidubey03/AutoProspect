import argparse
import json
import sys

from orchestrator import Pipeline
from config import AppConfig
from services import ApolloService
from services.apollo_service import ApolloError
from utils.logger import configure_logger
from utils.validators import DomainValidationError, normalize_domain


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the automated B2B outreach pipeline for a company domain."
    )
    parser.add_argument("domain", help="Company domain, for example openai.com")
    return parser


def main() -> int:
    configure_logger()
    parser = build_parser()
    args = parser.parse_args()

    try:
        domain = normalize_domain(args.domain)
    except DomainValidationError as error:
        parser.error(str(error))

    config = AppConfig.from_env()
    company_discovery = (
        ApolloService(config.apollo_api_key) if config.apollo_api_key else None
    )
    try:
        result = Pipeline(company_discovery=company_discovery).run(domain)
    except ApolloError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
