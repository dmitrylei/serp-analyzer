from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class RedirectEvent(Base):
    __tablename__ = "redirect_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)

    source_url: Mapped[str] = mapped_column(String(1000), index=True)
    final_url: Mapped[str] = mapped_column(String(1000))
    source_domain: Mapped[str] = mapped_column(String(255), index=True)
    final_domain: Mapped[str] = mapped_column(String(255), index=True)

    chain: Mapped[list[str] | None] = mapped_column(JSONB)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
