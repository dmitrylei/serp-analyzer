"""Simple UI for Serper queries."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import desc, select

from serp_monitor.config.settings import get_settings
from serp_monitor.db.models import Keyword, Run, SerpResult
from serp_monitor.db.session import get_session
from serp_monitor.providers.serper import SerperClient
from serp_monitor.services.serp_service import SerpService

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

        if not rows:
            st.warning("No results for this run")
            return

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

if __name__ == "__main__":
    main()
