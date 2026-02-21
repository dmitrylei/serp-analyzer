"""Quick one-off Serper query."""

from __future__ import annotations

import argparse
import json

from serp_monitor.config.settings import get_settings
from serp_monitor.providers.serper import SerperClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one Serper query and print JSON")
    parser.add_argument("--q", required=True, help="Search query")
    parser.add_argument("--region", default=None, help="Region code, e.g. IN or US")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    client = SerperClient(settings)
    payload = client.search(args.q, region=args.region)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
