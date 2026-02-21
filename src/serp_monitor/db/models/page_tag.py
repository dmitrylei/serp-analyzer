from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class PageTag(Base):
    __tablename__ = "page_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    watch_url_id: Mapped[int] = mapped_column(ForeignKey("watch_urls.id"), index=True)

    canonical: Mapped[str | None] = mapped_column(String(1000))
    hreflang: Mapped[dict | None] = mapped_column(JSONB)

    raw: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
