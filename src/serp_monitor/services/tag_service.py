from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from serp_monitor.config.settings import Settings
from serp_monitor.db.models import PageTag, WatchUrl
from serp_monitor.parsers.page_tags import parse_page_tags


class RetriableStatus(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class TagService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _headers(self, user_agent: str, language: str | None) -> dict[str, str]:
        lang = (language or "en").lower()
        lang_map = {
            "en": "en-US,en;q=0.9",
            "hi": "hi-IN,hi;q=0.9,en;q=0.8",
            "es": "es-ES,es;q=0.9,en;q=0.8",
            "fr": "fr-FR,fr;q=0.9,en;q=0.8",
            "de": "de-DE,de;q=0.9,en;q=0.8",
            "it": "it-IT,it;q=0.9,en;q=0.8",
            "pt": "pt-BR,pt;q=0.9,en;q=0.8",
            "nl": "nl-NL,nl;q=0.9,en;q=0.8",
            "ja": "ja-JP,ja;q=0.9,en;q=0.8",
        }
        accept_language = lang_map.get(lang, "en-US,en;q=0.9")
        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": accept_language,
            "Referer": "https://www.google.com/",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(RetriableStatus),
    )
    def _fetch_html(self, url: str, headers: dict[str, str]) -> tuple[str, str | None]:
        timeout = httpx.Timeout(self._settings.http_timeout)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            if response.status_code in {403, 429}:
                raise RetriableStatus(response.status_code)
            response.raise_for_status()
            return response.text, response.headers.get("Link")

    def _safe_fetch(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        try:
            html, link_header = self._fetch_html(url, headers)
            return {"html": html, "link": link_header, "status": 200, "error": None}
        except RetriableStatus as exc:
            return {"html": None, "link": None, "status": exc.status_code, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"html": None, "link": None, "status": None, "error": str(exc)}

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
        self,
        session: Session,
        run_id: int,
        url: str,
        region: str | None,
        language: str | None = None,
    ) -> dict[str, Any]:
        bot_ua = "SerpMonitorBot/1.0 (+https://example.com/bot)"
        googlebot_ua = (
            "Mozilla/5.0 (compatible; Googlebot/2.1; "
            "+http://www.google.com/bot.html)"
        )

        bot_fetch = self._safe_fetch(url, self._headers(bot_ua, language))
        google_fetch = self._safe_fetch(url, self._headers(googlebot_ua, language))

        bot_parsed = parse_page_tags(bot_fetch["html"] or "", bot_fetch.get("link"))
        google_parsed = parse_page_tags(google_fetch["html"] or "", google_fetch.get("link"))
        bot_parsed.update({"status": bot_fetch["status"], "error": bot_fetch["error"]})
        google_parsed.update(
            {"status": google_fetch["status"], "error": google_fetch["error"]}
        )

        watch_url = self._get_or_create_watch_url(session, url, region)

        row = PageTag(
            run_id=run_id,
            watch_url_id=watch_url.id,
            canonical=bot_parsed.get("canonical"),
            hreflang=bot_parsed.get("hreflang"),
            raw={
                "url": url,
                "bot": bot_parsed,
                "googlebot": google_parsed,
            },
        )
        session.add(row)
        session.commit()
        return {
            "bot": bot_parsed,
            "googlebot": google_parsed,
        }
