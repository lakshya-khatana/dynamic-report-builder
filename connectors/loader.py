"""
Shared by routes_schema.py and routes_reports.py — both need to go from a
source_id in a URL/request to a live, decrypted connector. Kept in one place
so there's exactly one code path that ever decrypts a stored credential.
"""

import json

from sqlalchemy import select

from connectors.base import BaseConnector
from connectors.registry import get_connector
from errors.exceptions import SchemaError
from security.crypto import decrypt_config
from templates_store.models import data_sources, get_app_engine


def load_connector(source_id: str) -> BaseConnector:
    engine = get_app_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(data_sources).where(data_sources.c.id == source_id)
        ).first()

    if row is None:
        raise SchemaError(f"Data source '{source_id}' not found.")

    config = decrypt_config(json.loads(row.config_json))
    dialect = row.dialect if row.dialect != "flatfile" else "flatfile"
    config.setdefault("dialect", dialect)
    return get_connector(dialect, source_id=source_id, config=config)
    return get_connector(dialect, source_id=source_id, config=config)
