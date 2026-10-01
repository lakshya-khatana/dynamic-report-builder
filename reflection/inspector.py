"""
Spec §2: 'Auto-fetch all available tables, views, and schemas upon selecting
or testing a data source.' Thin wrapper over sqlalchemy.inspect() — kept
separate from metadata_extractor.py because listing tables and extracting
per-column detail are different costs (this is cheap, that one reflects
full column/PK/FK info).
"""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def list_schemas(engine: Engine) -> list[str]:
    inspector = inspect(engine)
    try:
        return inspector.get_schema_names()
    except NotImplementedError:
        # SQLite has no schema concept — fine, just report none.
        return []


def list_tables(engine: Engine, schema: str | None = None) -> list[str]:
    inspector = inspect(engine)
    return inspector.get_table_names(schema=schema)


def list_views(engine: Engine, schema: str | None = None) -> list[str]:
    inspector = inspect(engine)
    try:
        return inspector.get_view_names(schema=schema)
    except NotImplementedError:
        return []
