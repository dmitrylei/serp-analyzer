from __future__ import annotations

from typing import Any


def parse_organic_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    organic = payload.get("organic") or []
    if not isinstance(organic, list):
        return []
    results: list[dict[str, Any]] = []
    for item in organic:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "position": item.get("position"),
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "raw": item,
            }
        )
    return results
