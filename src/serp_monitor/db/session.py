from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(database_url, pool_pre_ping=True)


SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=get_engine())
