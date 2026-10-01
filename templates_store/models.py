"""
This is the ONE place the app uses table definitions instead of raw
reflection — because these tables belong to *our* app database
(settings.APP_DB_URL), not a client's reflected source. Kept intentionally
simple (Core Table objects, not the ORM) to stay consistent with the rest
of the codebase's SQLAlchemy Core style.
"""

from sqlalchemy import (
    Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, func,
)

from config import settings

metadata = MetaData()

data_sources = Table(
    "data_sources", metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("dialect", String(32), nullable=False),
    Column("config_json", Text, nullable=False),  # encrypted config (crypto.py) as JSON text
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

report_templates = Table(
    "report_templates", metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("author", String(255), nullable=True),
    Column("request_json", Text, nullable=False),  # serialized ReportRequest
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)


def get_app_engine():
    return create_engine(settings.APP_DB_URL)


def init_app_db() -> None:
    """Call once at startup — creates the app's own tables if they don't exist."""
    metadata.create_all(get_app_engine())
