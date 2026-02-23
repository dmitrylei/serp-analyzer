from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class TrackedHit(Base):
    __tablename__ = "tracked_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracked_site_id: Mapped[int] = mapped_column(ForeignKey("tracked_sites.id"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    position: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(1000))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
