"""Spec §1: data source connectivity endpoints."""

import json
import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import insert, select

from connectors.registry import get_connector
from security.crypto import encrypt_config
from templates_store.models import data_sources, get_app_engine

router = APIRouter()


class SourceCreateRequest(BaseModel):
    name: str
    dialect: str  # "postgresql" | "mysql" | "mssql" | "sqlite" | "flatfile"
    config: dict  # host/port/database/username/password OR file_path/table_name


@router.post("/test")
def test_source_connection(payload: SourceCreateRequest):
    """
    Spec §1.1: 'Independent connection validation before saving credentials
    ... without application restart or caching overhead.' Deliberately does
    NOT touch the data_sources table — nothing is persisted here.
    """
    connector = get_connector(payload.dialect, source_id="__test__", config=payload.config)
    result = connector.test_connection()
    connector.dispose()
    return {"ok": result.ok, "message": result.message, "latency_ms": result.latency_ms}


@router.post("")
def create_source(payload: SourceCreateRequest):
    source_id = str(uuid.uuid4())
    encrypted_config = encrypt_config(payload.config)

    engine = get_app_engine()
    with engine.begin() as conn:
        conn.execute(
            insert(data_sources).values(
                id=source_id,
                name=payload.name,
                dialect=payload.dialect,
                config_json=json.dumps(encrypted_config),
            )
        )
    return {"id": source_id, "name": payload.name, "dialect": payload.dialect}


@router.get("")
def list_sources():
    engine = get_app_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(data_sources.c.id, data_sources.c.name, data_sources.c.dialect, data_sources.c.created_at)
        ).fetchall()
    return [dict(r._mapping) for r in rows]
