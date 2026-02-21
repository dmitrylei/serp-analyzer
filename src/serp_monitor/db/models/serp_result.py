from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class SerpResult(Base):
    __tablename__ = "serp_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)

    position: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000))
    snippet: Mapped[str | None] = mapped_column(String(2000))

    raw: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
