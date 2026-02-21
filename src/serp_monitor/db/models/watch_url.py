from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from serp_monitor.db.base import Base


class WatchUrl(Base):
    __tablename__ = "watch_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    region: Mapped[str] = mapped_column(String(8), index=True)
    proxy_profile: Mapped[str | None] = mapped_column(String(64), index=True)
