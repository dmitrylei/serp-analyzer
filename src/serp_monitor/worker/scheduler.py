from __future__ import annotations

from datetime import datetime, timedelta
import atexit
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from serp_monitor.config.settings import get_settings
from serp_monitor.db.models import Keyword, KeywordSchedule, SchedulerStatus, Run, RunStatus, TrackedSite
from serp_monitor.db.session import get_session
from serp_monitor.providers.serper import SerperClient
from serp_monitor.services.serp_service import SerpService
from serp_monitor.services.tag_service import TagService


def _now_tz() -> datetime:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.scheduler_tz))


def _run_due_schedules() -> None:
    settings = get_settings()
    client = SerperClient(settings)
    service = SerpService(client)
    now = _now_tz()

    with get_session() as session:
        status = session.get(SchedulerStatus, "keyword-scheduler")
        if not status:
            status = SchedulerStatus(name="keyword-scheduler", running=True)
        status.last_heartbeat = now
        status.running = True
        session.add(status)
        session.commit()

    with get_session() as session:
        schedules = list(
            session.execute(
                select(KeywordSchedule).where(
                    KeywordSchedule.active.is_(True),  # noqa: E712
                    (KeywordSchedule.next_run_at.is_(None))
                    | (KeywordSchedule.next_run_at <= now),
                )
            ).scalars()
        )

    for schedule in schedules:
        with get_session() as session:
            schedule = session.get(KeywordSchedule, schedule.id)
            if not schedule or not schedule.active:
                continue
            keyword = session.get(Keyword, schedule.keyword_id)
            if not keyword:
                continue
            service.run_keywords(session, [keyword], kind="schedule")
            next_run = now + timedelta(hours=schedule.interval_hours)
            schedule.last_run_at = now
            schedule.next_run_at = next_run
            session.add(schedule)
            session.commit()


def _run_favorite_tag_checks() -> None:
    now = _now_tz()
    tag_service = TagService(get_settings())

    with get_session() as session:
        sites = list(session.query(TrackedSite).all())
        if not sites:
            return
        run = Run(kind="favorites", status=RunStatus.running, started_at=now)
        session.add(run)
        session.flush()

        try:
            for site in sites:
                # use https by default; user can add full URL in watch list later if needed
                url = f"https://{site.domain}"
                tag_service.check_url(session, run.id, url, region=None, language=None)
            run.status = RunStatus.success
            run.finished_at = _now_tz()
            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            run.status = RunStatus.failed
            run.error = str(exc)[:500]
            run.finished_at = _now_tz()
            session.add(run)
            session.commit()


def start_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.scheduler_tz)
    scheduler.add_job(
        _run_due_schedules,
        "interval",
        minutes=1,
        id="keyword_schedule_runner",
        coalesce=True,
        misfire_grace_time=90,
        max_instances=1,
    )
    scheduler.add_job(
        _run_favorite_tag_checks,
        "interval",
        hours=1,
        id="favorite_tag_checks",
        coalesce=True,
        misfire_grace_time=300,
        max_instances=1,
    )
    scheduler.start()
    return scheduler


def run_forever() -> None:
    settings = get_settings()
    _register_shutdown()
    scheduler = BlockingScheduler(timezone=settings.scheduler_tz)
    scheduler.add_job(
        _run_due_schedules,
        "interval",
        minutes=1,
        id="keyword_schedule_runner",
        coalesce=True,
        misfire_grace_time=90,
        max_instances=1,
    )
    scheduler.add_job(
        _run_favorite_tag_checks,
        "interval",
        hours=1,
        id="favorite_tag_checks",
        coalesce=True,
        misfire_grace_time=300,
        max_instances=1,
    )
    scheduler.start()


def _register_shutdown() -> None:
    def _mark_stopped() -> None:
        try:
            with get_session() as session:
                status = session.get(SchedulerStatus, "keyword-scheduler")
                if not status:
                    status = SchedulerStatus(name="keyword-scheduler", running=False)
                status.running = False
                session.add(status)
                session.commit()
        except Exception:
            pass

    atexit.register(_mark_stopped)
