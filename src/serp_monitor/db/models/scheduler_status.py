from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class SchedulerStatus(Base):
    __tablename__ = "scheduler_status"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    running: Mapped[bool] = mapped_column(Boolean, default=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
