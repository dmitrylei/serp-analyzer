from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from serp_monitor.config.settings import get_settings
from serp_monitor.db.models import Keyword, KeywordSchedule
from serp_monitor.db.session import get_session
from serp_monitor.providers.serper import SerperClient
from serp_monitor.services.serp_service import SerpService


def _now_tz() -> datetime:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.scheduler_tz))


def _run_due_schedules() -> None:
    settings = get_settings()
    client = SerperClient(settings)
    service = SerpService(client)
    now = _now_tz()

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


def start_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.scheduler_tz)
    scheduler.add_job(_run_due_schedules, "interval", minutes=1, id="keyword_schedule_runner")
    scheduler.start()
    return scheduler


def run_forever() -> None:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.scheduler_tz)
    scheduler.add_job(_run_due_schedules, "interval", minutes=1, id="keyword_schedule_runner")
    scheduler.start()
