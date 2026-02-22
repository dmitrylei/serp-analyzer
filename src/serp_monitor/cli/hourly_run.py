"""CLI for hourly run."""

from __future__ import annotations

import argparse
from typing import Any

from sqlalchemy import select

from serp_monitor.config.loaders import load_config
from serp_monitor.config.settings import get_settings
from serp_monitor.db.models import Keyword
from serp_monitor.db.session import get_session
from serp_monitor.providers.serper import SerperClient
from serp_monitor.services.serp_service import SerpService


def _load_keywords(config_path: str) -> list[dict[str, Any]]:
    data = load_config(config_path)
    items = data.get("keywords") or []
    if not isinstance(items, list):
        raise ValueError("keywords must be a list")
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword") or "").strip()
        region = str(item.get("region") or "").strip()
        if not keyword or not region:
            continue
        language = str(item.get("language") or "EN").strip()
        normalized.append(
            {
                "keyword": keyword,
                "region": region,
                "language": language,
                "proxy_profile": (item.get("proxy_profile") or None),
            }
        )
    return normalized


def _sync_keywords(session, keywords: list[dict[str, Any]]) -> list[Keyword]:
    result: list[Keyword] = []
    for item in keywords:
        stmt = select(Keyword).where(
            Keyword.keyword == item["keyword"],
            Keyword.region == item["region"],
            Keyword.language == item["language"],
            Keyword.proxy_profile == item["proxy_profile"],
        )
        existing = session.execute(stmt).scalar_one_or_none()
        if existing:
            result.append(existing)
            continue
        row = Keyword(**item)
        session.add(row)
        session.flush()
        result.append(row)
    session.commit()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hourly SERP fetch")
    parser.add_argument("--config", required=True, help="Path to keywords config (yaml/json)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    client = SerperClient(settings)
    service = SerpService(client)

    keywords_config = _load_keywords(args.config)
    if not keywords_config:
        print("No keywords found in config")
        return

    with get_session() as session:
        keywords = _sync_keywords(session, keywords_config)
        run = service.run_keywords(session, keywords, kind="hourly")

    print(f"Run {run.id} finished with status={run.status}")
