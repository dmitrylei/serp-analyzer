from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from serp_monitor.db.models import Keyword, Run, RunStatus, SerpResult, TrackedHit, TrackedSite
from serp_monitor.utils.urls import extract_domain
from serp_monitor.parsers.serper import parse_organic_results
from serp_monitor.providers.serper import SerperClient


class SerpService:
    def __init__(self, client: SerperClient) -> None:
        self._client = client

    def run_keywords(self, session: Session, keywords: list[Keyword], kind: str = "hourly") -> Run:
        run = Run(kind=kind, status=RunStatus.running, started_at=datetime.now(timezone.utc))
        session.add(run)
        session.flush()
        try:
            tracked_sites = list(session.query(TrackedSite).all())
            tracked_domains = {site.domain: site.id for site in tracked_sites}
            for keyword in keywords:
                payload = self._client.search(
                    keyword.keyword,
                    region=keyword.region,
                    language=keyword.language or None,
                )
                rows = parse_organic_results(payload)
                for row in rows:
                    if row.get("position") is None or not row.get("link"):
                        continue
                    domain = extract_domain(row["link"])
                    tracked_site_id = tracked_domains.get(domain)
                    session.add(
                        SerpResult(
                            run_id=run.id,
                            keyword_id=keyword.id,
                            position=int(row["position"]),
                            title=row.get("title"),
                            link=row["link"],
                            snippet=row.get("snippet"),
                            raw=row.get("raw") or {},
                        )
                    )
                    if tracked_site_id:
                        session.add(
                            TrackedHit(
                                tracked_site_id=tracked_site_id,
                                run_id=run.id,
                                keyword_id=keyword.id,
                            )
                        )
            run.status = RunStatus.success
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            return run
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            run.status = RunStatus.failed
            run.error = str(exc)[:500]
            run.finished_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()
            raise
