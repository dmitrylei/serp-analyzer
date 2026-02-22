"""Simple UI for Serper queries."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import desc, select

from serp_monitor.config.settings import get_settings
from serp_monitor.db.models import Keyword, KeywordSchedule, PageTag, Run, SerpResult, WatchUrl
from serp_monitor.db.session import get_session
from serp_monitor.providers.serper import SerperClient
from serp_monitor.services.serp_service import SerpService
from serp_monitor.services.tag_service import TagService
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

REGIONS = [
    "US",
    "IN",
    "GB",
    "CA",
    "AU",
    "DE",
    "FR",
    "ES",
    "IT",
    "NL",
    "BR",
    "MX",
    "SG",
    "JP",
]

LANGUAGES = [
    "EN",
    "HI",
    "ES",
    "FR",
    "DE",
    "IT",
    "PT",
    "NL",
    "JA",
]

def _find_project_root() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def _get_or_create_keyword(session, query: str, region: str, language: str) -> Keyword:
    stmt = select(Keyword).where(
        Keyword.keyword == query,
        Keyword.region == region,
        Keyword.language == language,
        Keyword.proxy_profile.is_(None),
    )
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        return existing
    row = Keyword(keyword=query, region=region, language=language, proxy_profile=None)
    session.add(row)
    session.flush()
    session.commit()
    return row


def _load_run_results(session, run_id: int) -> list[SerpResult]:
    stmt = (
        select(SerpResult)
        .where(SerpResult.run_id == run_id)
        .order_by(SerpResult.position.asc())
    )
    return list(session.execute(stmt).scalars())


def _load_latest_page_tag(session, run_id: int, url: str) -> PageTag | None:
    watch = session.execute(
        select(WatchUrl).where(WatchUrl.url == url)
    ).scalar_one_or_none()
    if not watch:
        return None
    stmt = (
        select(PageTag)
        .where(PageTag.run_id == run_id, PageTag.watch_url_id == watch.id)
        .order_by(PageTag.id.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _extract_tag_block(raw: dict | None, key: str) -> dict | None:
    if not isinstance(raw, dict):
        return None
    block = raw.get(key)
    if isinstance(block, dict):
        return block
    return None


def _is_failure(block: dict | None) -> bool:
    if not block:
        return True
    if block.get("error"):
        return True
    status = block.get("status")
    return status not in (None, 200)


def _is_mismatch(bot: dict | None, google: dict | None) -> bool:
    if not bot or not google:
        return False
    if bot.get("canonical") != google.get("canonical"):
        return True
    return (bot.get("hreflang") or {}) != (google.get("hreflang") or {})


def _render_tag_block(tag_data: dict | None, label: str) -> None:
    if not tag_data:
        st.write(f"{label}: —")
        return
    canonical = tag_data.get("canonical")
    hreflang = tag_data.get("hreflang")
    status = tag_data.get("status")
    error = tag_data.get("error")
    st.write(f"{label} canonical: {canonical or '—'}")
    if status is not None:
        st.caption(f"{label} status: {status}")
    if error:
        st.caption(f"{label} error: {error}")
    if hreflang:
        st.write(f"{label} hreflang:")
        st.json(hreflang)
    else:
        st.write(f"{label} hreflang: —")


def _load_history(session, limit: int = 20) -> list[Run]:
    stmt = (
        select(Run)
        .where(Run.kind == "ui")
        .order_by(desc(Run.id))
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())


def main() -> None:
    root = _find_project_root()
    if root is not None:
        load_dotenv(root / ".env")

    st.set_page_config(page_title="SERP Analyzer", layout="wide")
    st.title("SERP Analyzer")
    st.write("Quick Serper.dev query and top 10 organic results.")
    if not os.getenv("DATABASE_URL"):
        st.warning("DATABASE_URL is not set. Add it to .env to enable history.")

    tabs = st.tabs(["New Query", "History", "Keywords"])

    with tabs[0]:
        with st.form("serp_form"):
            query = st.text_input("Keyword", value="aviator")
            region = st.selectbox("Region", REGIONS, index=REGIONS.index("IN"))
            language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index("EN"))
            submitted = st.form_submit_button("Fetch Top 10")

        if submitted:
            if not query.strip():
                st.error("Please enter a keyword")
            else:
                try:
                    settings = get_settings()
                    client = SerperClient(settings)
                    service = SerpService(client)

                    with get_session() as session:
                        keyword = _get_or_create_keyword(session, query.strip(), region, language)
                        run = service.run_keywords(session, [keyword], kind="ui")
                        rows = _load_run_results(session, run.id)[:10]
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Request failed: {exc}")
                    rows = []

                if not rows:
                    st.warning("No results")
                else:
                    table = [
                        {
                            "Position": row.position,
                            "Title": row.title,
                            "Link": row.link,
                            "Snippet": row.snippet,
                        }
                        for row in rows
                    ]
                    st.dataframe(pd.DataFrame(table), width="stretch")

    with tabs[1]:
        try:
            with get_session() as session:
                history = _load_history(session, limit=50)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load history: {exc}")
            return

        if not history:
            st.info("History is empty yet.")
            return

        options = {f"Run {run.id} • {run.created_at} • {run.status}": run.id for run in history}
        selected = st.selectbox("Select run", list(options.keys()))
        run_id = options[selected]

        with get_session() as session:
            rows = _load_run_results(session, run_id)[:10]
            tag_rows = list(
                session.execute(select(PageTag).where(PageTag.run_id == run_id)).scalars()
            )

        if not rows:
            st.warning("No results for this run")
            return

        total_checked = len(tag_rows)
        failures = 0
        mismatches = 0
        for tag in tag_rows:
            raw = tag.raw or {}
            bot_block = _extract_tag_block(raw, "bot")
            google_block = _extract_tag_block(raw, "googlebot")
            if _is_failure(bot_block) or _is_failure(google_block):
                failures += 1
            if _is_mismatch(bot_block, google_block):
                mismatches += 1

        st.subheader("Tag Check Summary")
        st.write(f"Checked: {total_checked} / {len(rows)}")
        st.write(f"Failures: {failures}")
        st.write(f"Mismatches: {mismatches}")

        st.subheader("Results")
        for row in rows:
            with st.container():
                st.markdown(f"**{row.position}. {row.title or ''}**")
                st.write(row.link)
                if row.snippet:
                    st.caption(row.snippet)

                col1, col2 = st.columns([1, 5])
                with col1:
                    do_check = st.button(
                        "Check Tags",
                        key=f"check_tags_{row.id}",
                    )

                with col2:
                    with get_session() as session:
                        existing = _load_latest_page_tag(session, run_id, row.link)
                    if existing:
                        raw = existing.raw or {}
                        bot_block = _extract_tag_block(raw, "bot")
                        google_block = _extract_tag_block(raw, "googlebot")
                        if bot_block or google_block:
                            _render_tag_block(bot_block, "Bot")
                            _render_tag_block(google_block, "Googlebot")
                        else:
                            _render_tag_block(
                                {"canonical": existing.canonical, "hreflang": existing.hreflang},
                                "Bot",
                            )

                if do_check:
                    try:
                        settings = get_settings()
                        service = TagService(settings)
                        with get_session() as session:
                            keyword = session.get(Keyword, row.keyword_id)
                            tag = service.check_url(
                                session,
                                run_id,
                                row.link,
                                region=None,
                                language=(keyword.language if keyword else None),
                            )
                        st.success("Tags fetched")
                        _render_tag_block(tag.get("bot"), "Bot")
                        _render_tag_block(tag.get("googlebot"), "Googlebot")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Tag check failed: {exc}")

    with tabs[2]:
        st.subheader("Keyword Manager")
        try:
            with get_session() as session:
                keywords = list(
                    session.execute(
                        select(Keyword).order_by(Keyword.id.desc()).limit(200)
                    ).scalars()
                )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load keywords: {exc}")
            return

        if keywords:
            table = [
                {
                    "ID": row.id,
                    "Keyword": row.keyword,
                    "Region": row.region,
                    "Language": row.language,
                    "Proxy": row.proxy_profile,
                }
                for row in keywords
            ]
            st.dataframe(pd.DataFrame(table), width="stretch")
        else:
            st.info("No keywords yet.")

        st.divider()
        st.write("Add new keyword")
        with st.form("keyword_create"):
            new_keyword = st.text_input("Keyword", value="")
            new_region = st.selectbox("Region", REGIONS, index=REGIONS.index("IN"))
            new_language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index("EN"))
            submitted = st.form_submit_button("Create")

        if submitted:
            if not new_keyword.strip():
                st.error("Keyword is required")
            else:
                try:
                    with get_session() as session:
                        _get_or_create_keyword(
                            session,
                            new_keyword.strip(),
                            new_region,
                            new_language,
                        )
                    st.success("Keyword saved")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to save keyword: {exc}")

        st.divider()
        st.write("Delete keyword")
        if keywords:
            options = {f"{row.id} • {row.keyword} • {row.region}/{row.language}": row.id for row in keywords}
            selected = st.selectbox("Select keyword", list(options.keys()))
            if st.button("Delete selected"):
                try:
                    with get_session() as session:
                        row = session.get(Keyword, options[selected])
                        if row:
                            session.delete(row)
                            session.commit()
                    st.success("Keyword deleted")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to delete keyword: {exc}")

        st.divider()
        st.subheader("Keyword Schedules")
        try:
            with get_session() as session:
                schedules = list(
                    session.execute(
                        select(KeywordSchedule).order_by(KeywordSchedule.id.desc()).limit(200)
                    ).scalars()
                )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load schedules: {exc}")
            return

        if schedules:
            schedule_table = []
            keyword_map = {}
            with get_session() as session:
                for row in schedules:
                    keyword = session.get(Keyword, row.keyword_id)
                    keyword_map[row.id] = keyword
                    schedule_table.append(
                        {
                            "ID": row.id,
                            "Keyword": keyword.keyword if keyword else "—",
                            "Region": keyword.region if keyword else "—",
                            "Language": keyword.language if keyword else "—",
                            "Interval (h)": row.interval_hours,
                            "Active": row.active,
                            "Last Run": row.last_run_at,
                            "Next Run": row.next_run_at,
                        }
                    )
            st.dataframe(pd.DataFrame(schedule_table), width="stretch")
        else:
            st.info("No schedules yet.")

        st.write("Create or update schedule")
        if keywords:
            kw_options = {f"{row.id} • {row.keyword} • {row.region}/{row.language}": row.id for row in keywords}
            selected_kw = st.selectbox("Keyword", list(kw_options.keys()))
            interval = st.number_input("Interval (hours)", min_value=1, max_value=720, value=24, step=1)
            active = st.checkbox("Active", value=True)
            if st.button("Save schedule"):
                try:
                    with get_session() as session:
                        existing = session.execute(
                            select(KeywordSchedule).where(
                                KeywordSchedule.keyword_id == kw_options[selected_kw]
                            )
                        ).scalar_one_or_none()
                        settings = get_settings()
                        now = datetime.now(ZoneInfo(settings.scheduler_tz))
                        if existing:
                            existing.interval_hours = int(interval)
                            existing.active = bool(active)
                            if existing.active:
                                existing.next_run_at = now + timedelta(hours=int(interval))
                            session.add(existing)
                        else:
                            schedule = KeywordSchedule(
                                keyword_id=kw_options[selected_kw],
                                interval_hours=int(interval),
                                active=bool(active),
                                next_run_at=now + timedelta(hours=int(interval)),
                            )
                            session.add(schedule)
                        session.commit()
                    st.success("Schedule saved")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to save schedule: {exc}")
        else:
            st.info("Create at least one keyword first.")



if __name__ == "__main__":
    main()
