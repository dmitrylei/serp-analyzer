from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from serp_monitor.config.settings import Settings


class SerperClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def search(self, query: str, region: str | None = None) -> dict[str, Any]:
        url = f"{self._settings.serper_base_url.rstrip('/')}/search"
        payload: dict[str, Any] = {"q": query}
        if region:
            payload["gl"] = region.lower()
        headers = {
            "X-API-KEY": self._settings.serper_api_key,
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(self._settings.http_timeout)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
