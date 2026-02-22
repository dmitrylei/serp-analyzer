from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from serp_monitor.config.settings import Settings
from serp_monitor.db.models import PageTag, WatchUrl
from serp_monitor.parsers.page_tags import parse_page_tags


class TagService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _get_or_create_watch_url(
        self, session: Session, url: str, region: str | None
    ) -> WatchUrl:
        row = (
            session.query(WatchUrl)
            .filter(WatchUrl.url == url)
            .one_or_none()
        )
        if row:
            return row
        row = WatchUrl(url=url, region=region or "US", proxy_profile=None)
        session.add(row)
        session.flush()
        return row

    def check_url(
        self, session: Session, run_id: int, url: str, region: str | None
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(self._settings.http_timeout)
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        parsed = parse_page_tags(html)
        watch_url = self._get_or_create_watch_url(session, url, region)

        row = PageTag(
            run_id=run_id,
            watch_url_id=watch_url.id,
            canonical=parsed.get("canonical"),
            hreflang=parsed.get("hreflang"),
            raw={"url": url},
        )
        session.add(row)
        session.commit()
        return {
            "canonical": row.canonical,
            "hreflang": row.hreflang,
        }
