import argparse
import json
import sys

from orchestrator import Pipeline
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

    result = Pipeline().run(domain)
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
