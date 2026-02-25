from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class CanonicalEdge(Base):
    __tablename__ = "canonical_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    source_url: Mapped[str] = mapped_column(String(1000), index=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1000))
    canonical_google: Mapped[str | None] = mapped_column(String(1000))
    canonical_bot: Mapped[str | None] = mapped_column(String(1000))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
