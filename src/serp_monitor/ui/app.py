"""Simple UI for Serper queries."""

from __future__ import annotations

import sys

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import desc, select, func

# Ensure src/ is on sys.path for Streamlit Cloud
_src_path = Path(__file__).resolve().parents[2]
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from serp_monitor.config.settings import get_settings
from serp_monitor.db.models import (
    Keyword,
    KeywordSchedule,
    PageTag,
    Run,
    SchedulerStatus,
    SerpResult,
    TrackedHit,
    TrackedSite,
    WatchUrl,
)
from serp_monitor.db.session import get_session
from serp_monitor.providers.serper import SerperClient
from serp_monitor.services.serp_service import SerpService
from serp_monitor.services.tag_service import TagService
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from serp_monitor.utils.urls import extract_domain

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


def _scheduler_status_block() -> None:
    st.subheader("Scheduler Status")
    try:
        with get_session() as session:
            status = session.get(SchedulerStatus, "keyword-scheduler")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load scheduler status: {exc}")
        return

    if not status:
        st.info("No scheduler heartbeat yet.")
        return

    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.scheduler_tz))
    last = status.last_heartbeat
    stale = False
    if last:
        delta = (now - last).total_seconds()
        stale = delta > 180

    st.write(f"Running: {status.running}")
    st.write(f"Last heartbeat: {status.last_heartbeat}")
    st.write(f"Updated at: {status.updated_at}")
    if stale:
        st.warning("Scheduler heartbeat is stale. It may be stopped.")


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


def _load_history(session, limit: int = 50, offset: int = 0) -> list[Run]:
    stmt = select(Run).order_by(desc(Run.id)).limit(limit).offset(offset)
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

    tabs = st.tabs(["New Query", "History", "Keywords", "Sites", "Settings"])

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
                total_runs = session.execute(select(func.count(Run.id))).scalar_one()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load history: {exc}")
            return

        if not total_runs:
            st.info("History is empty yet.")
            return

        with get_session() as session:
            keyword_values = session.execute(
                select(Keyword.keyword).distinct().order_by(Keyword.keyword)
            ).scalars().all()
            region_values = session.execute(
                select(Keyword.region).distinct().order_by(Keyword.region)
            ).scalars().all()

        filter_cols = st.columns([2, 2])
        with filter_cols[0]:
            selected_keyword_filter = st.selectbox(
                "Filter by keyword",
                options=["All"] + keyword_values,
                index=0,
            )
        with filter_cols[1]:
            selected_region_filter = st.selectbox(
                "Filter by region",
                options=["All"] + region_values,
                index=0,
            )

        with get_session() as session:
            base_stmt = select(Run).order_by(desc(Run.id))
            if selected_keyword_filter != "All" or selected_region_filter != "All":
                base_stmt = (
                    select(Run)
                    .join(SerpResult, SerpResult.run_id == Run.id)
                    .join(Keyword, Keyword.id == SerpResult.keyword_id)
                )
                if selected_keyword_filter != "All":
                    base_stmt = base_stmt.where(Keyword.keyword == selected_keyword_filter)
                if selected_region_filter != "All":
                    base_stmt = base_stmt.where(Keyword.region == selected_region_filter)
                base_stmt = base_stmt.order_by(desc(Run.id)).distinct()

            total_runs = session.execute(
                select(func.count()).select_from(base_stmt.subquery())
            ).scalar_one()

        page_size = st.selectbox("Page size", [25, 50, 100], index=1)
        total_pages = max(1, (total_runs + page_size - 1) // page_size)
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
        offset = (page - 1) * page_size

        with get_session() as session:
            history = list(
                session.execute(base_stmt.limit(page_size).offset(offset)).scalars()
            )

        run_ids = [run.id for run in history]
        run_meta = {}
        if run_ids:
            with get_session() as session:
                rows = session.execute(
                    select(
                        SerpResult.run_id,
                        Keyword.keyword,
                        Keyword.region,
                        Keyword.language,
                    )
                    .join(Keyword, Keyword.id == SerpResult.keyword_id)
                    .where(SerpResult.run_id.in_(run_ids))
                ).all()
            for run_id, keyword, region, language in rows:
                meta = run_meta.setdefault(run_id, {"keywords": set(), "regions": set(), "languages": set()})
                if keyword:
                    meta["keywords"].add(keyword)
                if region:
                    meta["regions"].add(region)
                if language:
                    meta["languages"].add(language)

        run_table = []
        for run in history:
            meta = run_meta.get(run.id, {})
            keywords = ", ".join(sorted(meta.get("keywords", [])))
            regions = ", ".join(sorted(meta.get("regions", [])))
            languages = ", ".join(sorted(meta.get("languages", [])))
            run_table.append(
                {
                    "Run ID": run.id,
                    "Kind": run.kind,
                    "Status": run.status,
                    "Keyword(s)": keywords or "—",
                    "Region(s)": regions or "—",
                    "Language(s)": languages or "—",
                    "Created At": run.created_at,
                    "Started At": run.started_at,
                    "Finished At": run.finished_at,
                }
            )
        st.subheader("Runs")
        st.dataframe(pd.DataFrame(run_table), width="stretch")
        st.caption(f"Showing {offset + 1}–{min(offset + page_size, total_runs)} of {total_runs}")

        options = {
            f"Run {run.id} • {run.kind} • {run.created_at} • {run.status}": run.id
            for run in history
        }
        selected = st.selectbox("Select run", list(options.keys()))
        run_id = options[selected]
        run_obj = next((r for r in history if r.id == run_id), None)

        with get_session() as session:
            rows = _load_run_results(session, run_id)
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

        keyword_map = {}
        for row in rows:
            keyword_map.setdefault(row.keyword_id, row)

        keyword_options = {}
        with get_session() as session:
            for row in rows:
                keyword = session.get(Keyword, row.keyword_id)
                if keyword:
                    label = f"{keyword.keyword} • {keyword.region}/{keyword.language}"
                    keyword_options[label] = keyword.id
        selected_keyword = st.selectbox("Keyword", list(keyword_options.keys()))
        selected_keyword_id = keyword_options[selected_keyword]

        filtered_rows = [r for r in rows if r.keyword_id == selected_keyword_id]
        if not filtered_rows:
            st.info("No results for selected keyword.")
            return

        with get_session() as session:
            keyword = session.get(Keyword, selected_keyword_id)
        st.markdown(
            f"**Run ID:** {run_id}  \n"
            f"**Keyword:** {keyword.keyword if keyword else '—'}  \n"
            f"**Region:** {keyword.region if keyword else '—'}  \n"
            f"**Date:** {run_obj.created_at.date() if run_obj else '—'}  \n"
            f"**Time:** {run_obj.created_at.time() if run_obj else '—'}"
        )

        tag_map = {}
        with get_session() as session:
            for row in filtered_rows:
                existing = _load_latest_page_tag(session, run_id, row.link)
                if existing:
                    raw = existing.raw or {}
                    tag_map[row.link] = {
                        "bot": _extract_tag_block(raw, "bot")
                        or {"canonical": existing.canonical, "hreflang": existing.hreflang},
                        "googlebot": _extract_tag_block(raw, "googlebot"),
                    }

        st.subheader("Results Table")
        header_cols = st.columns([1, 3, 3, 3, 2, 2, 2, 2, 1, 1])
        headers = [
            "Position",
            "URL",
            "Meta Title",
            "Meta Description",
            "Bot Canonical",
            "Bot Hreflang",
            "Google Bot Canonical",
            "Google Bot Hreflang",
            "Check",
            "★",
        ]
        for col, title in zip(header_cols, headers, strict=False):
            col.markdown(f"**{title}**")

        for row in filtered_rows:
            tags = tag_map.get(row.link, {})
            bot = tags.get("bot") or {}
            google = tags.get("googlebot") or {}

            cols = st.columns([1, 3, 3, 3, 2, 2, 2, 2, 1, 1])
            cols[0].write(row.position)
            cols[1].write(row.link)
            cols[2].write(row.title or "—")
            cols[3].write(row.snippet or "—")
            cols[4].write(bot.get("canonical") or "—")
            cols[5].write(bot.get("hreflang") or "—")
            cols[6].write(google.get("canonical") or "—")
            cols[7].write(google.get("hreflang") or "—")

            if cols[8].button("Check Tags", key=f"check_{row.id}"):
                try:
                    settings = get_settings()
                    service = TagService(settings)
                    with get_session() as session:
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

            if cols[9].button("★", key=f"star_{row.id}"):
                try:
                    domain = extract_domain(row.link)
                    with get_session() as session:
                        existing = (
                            session.query(TrackedSite)
                            .filter(TrackedSite.domain == domain)
                            .one_or_none()
                        )
                        if not existing:
                            session.add(TrackedSite(domain=domain))
                            session.commit()
                    st.success(f"Tracking {domain}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to track site: {exc}")

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

    with tabs[3]:
        st.subheader("Tracked Sites")
        try:
            with get_session() as session:
                sites = list(session.query(TrackedSite).order_by(TrackedSite.id.desc()).all())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load tracked sites: {exc}")
            return

        if not sites:
            st.info("No tracked sites yet. Use ★ in History to add.")
        else:
            site_options = {f"{s.id} • {s.domain}": s.id for s in sites}
            selected_site = st.selectbox("Select site", list(site_options.keys()))
            site_id = site_options[selected_site]

            with get_session() as session:
                hits = list(
                    session.query(TrackedHit)
                    .filter(TrackedHit.tracked_site_id == site_id)
                    .order_by(TrackedHit.detected_at.desc())
                    .limit(200)
                )
                if hits:
                    rows = []
                    for hit in hits:
                        keyword = session.get(Keyword, hit.keyword_id)
                        rows.append(
                            {
                                "Detected At": hit.detected_at,
                                "Keyword": keyword.keyword if keyword else "—",
                                "Region": keyword.region if keyword else "—",
                                "Language": keyword.language if keyword else "—",
                                "Run ID": hit.run_id,
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), width="stretch")
                else:
                    st.info("No detections yet.")

        st.divider()
        st.write("Remove tracked site")
        if sites:
            remove_site = st.selectbox("Site to remove", list(site_options.keys()), key="remove_site")
            if st.button("Remove"):
                try:
                    with get_session() as session:
                        site = session.get(TrackedSite, site_options[remove_site])
                        if site:
                            session.query(TrackedHit).filter(
                                TrackedHit.tracked_site_id == site.id
                            ).delete()
                            session.delete(site)
                            session.commit()
                    st.success("Removed")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to remove site: {exc}")

    with tabs[4]:
        _scheduler_status_block()



if __name__ == "__main__":
    main()
