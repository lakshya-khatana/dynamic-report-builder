"""
data_admin.py - separate router for viewing/editing table rows (demo/testing helper).
The report engine's read-only guard is NOT touched. Turn this off with ALLOW_DATA_EDIT=false.
"""
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import MetaData, Table, create_engine, delete, func, insert, inspect, select, update
from sqlalchemy.exc import SQLAlchemyError

from connectors.registry import get_connector
from security import crypto
from templates_store.models import data_sources, get_app_engine

router = APIRouter(prefix="/data", tags=["data-admin"])
ENABLED = os.getenv("ALLOW_DATA_EDIT", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Engine lookup: reads the source row, decrypts its config, builds an engine.
# ---------------------------------------------------------------------------
_engines: Dict[str, Any] = {}


def _decrypt(enc):
    for name in ("decrypt_config", "decrypt_json", "decrypt"):
        fn = getattr(crypto, name, None)
        if fn is not None:
            return fn(enc)
    names = ", ".join(n for n in dir(crypto) if not n.startswith("_"))
    raise HTTPException(500, f"security/crypto.py me decrypt function nahi mila. Ye mila: {names}")


def get_engine(source_id: str):
    # Optional override for quick testing: set DATA_DB_URL before starting uvicorn
    url = os.getenv("DATA_DB_URL")
    if url:
        if url not in _engines:
            _engines[url] = create_engine(url)
        return _engines[url]

    if source_id in _engines:
        return _engines[source_id]

    with get_app_engine().connect() as conn:
        row = conn.execute(select(data_sources).where(data_sources.c.id == source_id)).first()
    if row is None:
        raise HTTPException(404, "Source not found.")
    m = row._mapping
    dialect = m["dialect"]
    if dialect == "flatfile":
        raise HTTPException(400, "Flat-file sources cannot be edited here.")

    config = _decrypt(json.loads(m["config_json"]))

    # SQLite: open our own engine straight from the file, so any read-only
    # settings on the report connector do not block writes.
    if dialect == "sqlite":
        path = config.get("file_path") or config.get("database") or config.get("path")
        if path:
            eng = create_engine("sqlite:///" + Path(path).as_posix())
            _engines[source_id] = eng
            return eng

    # Other databases: reuse the connector's engine
    connector = get_connector(dialect, source_id=source_id, config=config)
    for attr in ("engine", "_engine", "get_engine"):
        cand = getattr(connector, attr, None)
        if cand is not None:
            eng = cand() if callable(cand) else cand
            _engines[source_id] = eng
            return eng
    names = ", ".join(n for n in dir(connector) if not n.startswith("__"))
    raise HTTPException(500, f"Connector se engine nahi mila. Connector ke attributes: {names}")


# ---------------------------------------------------------------------------
def _check_enabled():
    if not ENABLED:
        raise HTTPException(403, "Data editing is disabled (ALLOW_DATA_EDIT=false).")


def _table(engine, name: str) -> Table:
    if name not in inspect(engine).get_table_names():
        raise HTTPException(404, f"Table '{name}' not found.")
    return Table(name, MetaData(), autoload_with=engine)


def _pk(t: Table):
    cols = list(t.primary_key.columns)
    return cols[0] if len(cols) == 1 else None  # only single-column primary keys are editable


def _coerce(col, v):
    if v is None:
        return None
    try:
        pt = col.type.python_type
    except NotImplementedError:
        pt = str
    if isinstance(v, str) and v.strip() == "":
        if col.nullable or col.primary_key:
            return None
        if pt is str:
            return ""
        raise HTTPException(422, f"'{col.name}' cannot be empty.")
    try:
        if pt is bool:
            return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "t")
        if pt is int:
            return int(v)
        if pt is float:
            return float(v)
        if pt is Decimal:
            return Decimal(str(v))
        if pt is datetime:
            return datetime.fromisoformat(str(v))
        if pt is date:
            return date.fromisoformat(str(v))
    except (ValueError, ArithmeticError):
        raise HTTPException(422, f"Invalid value for '{col.name}' (expected {pt.__name__}).")
    return v


def _clean(t: Table, values: Dict[str, Any], drop_empty_pk: bool = False) -> Dict[str, Any]:
    out = {}
    for k, v in values.items():
        if k not in t.c:
            raise HTTPException(422, f"Unknown column '{k}'.")
        cv = _coerce(t.c[k], v)
        if drop_empty_pk and t.c[k].primary_key and cv is None:
            continue
        out[k] = cv
    return out


def _db_error(e: SQLAlchemyError):
    msg = str(getattr(e, "orig", e))
    raise HTTPException(400, msg)


class RowBody(BaseModel):
    values: Dict[str, Any]


# ---------------------------------------------------------------------------
@router.get("/{source_id}/tables")
def list_tables(source_id: str):
    eng = get_engine(source_id)
    insp = inspect(eng)
    return {
        "enabled": ENABLED,
        "tables": [
            {"name": n, "editable": len(insp.get_pk_constraint(n).get("constrained_columns", [])) == 1}
            for n in insp.get_table_names()
        ],
    }


@router.get("/{source_id}/tables/{table}/rows")
def list_rows(source_id: str, table: str, limit: int = 50, offset: int = 0):
    eng = get_engine(source_id)
    t = _table(eng, table)
    pk = _pk(t)
    q = select(t).limit(min(max(limit, 1), 200)).offset(max(offset, 0))
    if pk is not None:
        q = q.order_by(pk)
    with eng.connect() as c:
        rows = [dict(r._mapping) for r in c.execute(q)]
        total = c.execute(select(func.count()).select_from(t)).scalar()
    cols = [
        {"name": col.name, "type": str(col.type), "pk": col.primary_key, "nullable": col.nullable}
        for col in t.columns
    ]
    return jsonable_encoder({"columns": cols, "pk": pk.name if pk is not None else None,
                             "editable": pk is not None and ENABLED, "rows": rows, "total": total})


@router.post("/{source_id}/tables/{table}/rows")
def add_row(source_id: str, table: str, body: RowBody):
    _check_enabled()
    eng = get_engine(source_id)
    t = _table(eng, table)
    vals = _clean(t, body.values, drop_empty_pk=True)
    try:
        with eng.begin() as c:
            res = c.execute(insert(t).values(**vals))
        return {"inserted": True, "pk": jsonable_encoder(res.inserted_primary_key[0]) if res.inserted_primary_key else None}
    except SQLAlchemyError as e:
        _db_error(e)


@router.put("/{source_id}/tables/{table}/rows/{pk_value}")
def update_row(source_id: str, table: str, pk_value: str, body: RowBody):
    _check_enabled()
    eng = get_engine(source_id)
    t = _table(eng, table)
    pk = _pk(t)
    if pk is None:
        raise HTTPException(400, "Table needs a single-column primary key to edit rows.")
    vals = _clean(t, body.values)
    vals.pop(pk.name, None)
    if not vals:
        raise HTTPException(422, "Nothing to update.")
    try:
        with eng.begin() as c:
            res = c.execute(update(t).where(pk == _coerce(pk, pk_value)).values(**vals))
        if res.rowcount == 0:
            raise HTTPException(404, "Row not found.")
        return {"updated": res.rowcount}
    except SQLAlchemyError as e:
        _db_error(e)


@router.delete("/{source_id}/tables/{table}/rows/{pk_value}")
def delete_row(source_id: str, table: str, pk_value: str):
    _check_enabled()
    eng = get_engine(source_id)
    t = _table(eng, table)
    pk = _pk(t)
    if pk is None:
        raise HTTPException(400, "Table needs a single-column primary key to delete rows.")
    try:
        with eng.begin() as c:
            res = c.execute(delete(t).where(pk == _coerce(pk, pk_value)))
        if res.rowcount == 0:
            raise HTTPException(404, "Row not found.")
        return {"deleted": res.rowcount}
    except SQLAlchemyError as e:
        _db_error(e)
