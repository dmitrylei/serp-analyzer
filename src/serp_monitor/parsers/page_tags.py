from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup


def parse_page_tags(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    canonical = None
    canonical_tag = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    if canonical_tag and canonical_tag.get("href"):
        canonical = canonical_tag.get("href")

    hreflang: dict[str, str] = {}
    for tag in soup.find_all("link", rel=lambda v: v and "alternate" in v.lower()):
        lang = tag.get("hreflang")
        href = tag.get("href")
        if lang and href:
            hreflang[str(lang).lower()] = str(href)

    return {
        "canonical": canonical,
        "hreflang": hreflang or None,
    }
