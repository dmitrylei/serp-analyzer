from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup


def parse_page_tags(html: str, link_header: str | None = None) -> dict[str, Any]:
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

    if link_header:
        header_canonical, header_hreflang = _parse_link_header(link_header)
        if header_canonical:
            canonical = canonical or header_canonical
        if header_hreflang:
            hreflang.update({k: v for k, v in header_hreflang.items() if k not in hreflang})

    return {
        "canonical": canonical,
        "hreflang": hreflang or None,
    }


def _parse_link_header(link_header: str) -> tuple[str | None, dict[str, str]]:
    canonical = None
    hreflang: dict[str, str] = {}

    parts = [p.strip() for p in link_header.split(",") if p.strip()]
    for part in parts:
        if not part.startswith("<") or ">;" not in part:
            continue
        url = part[1 : part.index(">")]
        params_raw = part[part.index(">") + 1 :].split(";")
        params = {}
        for p in params_raw:
            p = p.strip()
            if "=" in p:
                k, v = p.split("=", 1)
                params[k.strip().lower()] = v.strip().strip('"')
            elif p:
                params[p.lower()] = ""
        rel = params.get("rel", "").lower()
        if "canonical" in rel:
            canonical = url
        if "alternate" in rel and "hreflang" in params:
            hreflang[params["hreflang"].lower()] = url

    return canonical, hreflang
