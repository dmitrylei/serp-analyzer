"""CLI for CSV export."""

from __future__ import annotations

import argparse
import csv

from sqlalchemy import desc, select

from serp_monitor.db.models import Keyword, Run, SerpResult
from serp_monitor.db.session import SessionLocal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export SERP results to CSV")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--run-id", type=int, default=None, help="Run id to export")
    return parser


def _get_latest_run_id(session) -> int | None:
    stmt = select(Run.id).where(Run.kind == "hourly").order_by(desc(Run.id)).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    with SessionLocal() as session:
        run_id = args.run_id or _get_latest_run_id(session)
        if not run_id:
            print("No runs found")
            return

        stmt = (
            select(
                SerpResult.id,
                SerpResult.position,
                SerpResult.title,
                SerpResult.link,
                SerpResult.snippet,
                SerpResult.created_at,
                Keyword.keyword,
                Keyword.region,
            )
            .join(Keyword, Keyword.id == SerpResult.keyword_id)
            .where(SerpResult.run_id == run_id)
            .order_by(SerpResult.position.asc())
        )
        rows = session.execute(stmt).all()

    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "result_id",
            "position",
            "title",
            "link",
            "snippet",
            "created_at",
            "keyword",
            "region",
        ])
        for row in rows:
            writer.writerow(row)

    print(f"Exported {len(rows)} rows to {args.out}")
