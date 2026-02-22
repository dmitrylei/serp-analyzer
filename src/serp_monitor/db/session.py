from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine


def get_session():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autoflush=False, autocommit=False, bind=get_engine()
        )
    return _session_factory()
