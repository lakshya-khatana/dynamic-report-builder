"""
Spec §2: 'Inspect selected tables to capture column names, database types,
mapped Python types, and Primary/Foreign Key metadata.'

This is the one function whose output the frontend actually renders as
"available fields" — and whose returned MetaData object every other module
(security/identifiers.py, compiler/*) treats as the single source of truth
for what identifiers are allowed to exist.
"""

from dataclasses import dataclass, field

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine


@dataclass
class ColumnInfo:
    name: str
    db_type: str          # e.g. "VARCHAR(255)", "INTEGER" — dialect-reported
    python_type: str      # e.g. "String", "Numeric", "DateTime", "Boolean"
    nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    references: str | None = None  # "other_table.other_column" if FK


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)


_TYPE_MAP = {
    "INTEGER": "Numeric", "BIGINT": "Numeric", "SMALLINT": "Numeric",
    "NUMERIC": "Numeric", "DECIMAL": "Numeric", "FLOAT": "Numeric", "REAL": "Numeric",
    "VARCHAR": "String", "CHAR": "String", "TEXT": "String", "CLOB": "String",
    "DATETIME": "DateTime", "TIMESTAMP": "DateTime", "DATE": "DateTime", "TIME": "DateTime",
    "BOOLEAN": "Boolean",
}


def _map_python_type(db_type_str: str) -> str:
    upper = db_type_str.upper()
    for prefix, mapped in _TYPE_MAP.items():
        if upper.startswith(prefix):
            return mapped
    return "String"  # safe fallback — unknown types still get filterable as text


def reflect_metadata(engine: Engine, schema: str | None = None) -> MetaData:
    """
    The one call every other module depends on. Reflects ALL tables in the
    given schema in a single round trip — Spec §2's caching layer (cache.py)
    exists specifically so this expensive call doesn't repeat on every request.
    """
    metadata = MetaData(schema=schema)
    metadata.reflect(bind=engine, schema=schema)
    return metadata


def extract_table_info(metadata: MetaData, table_name: str) -> TableInfo:
    table = metadata.tables[table_name]
    pk_columns = {c.name for c in table.primary_key.columns}

    fk_map: dict[str, str] = {}
    for fk in table.foreign_keys:
        fk_map[fk.parent.name] = f"{fk.column.table.name}.{fk.column.name}"

    columns = []
    for col in table.columns:
        db_type_str = str(col.type)
        columns.append(
            ColumnInfo(
                name=col.name,
                db_type=db_type_str,
                python_type=_map_python_type(db_type_str),
                nullable=col.nullable,
                is_primary_key=col.name in pk_columns,
                is_foreign_key=col.name in fk_map,
                references=fk_map.get(col.name),
            )
        )
    return TableInfo(name=table_name, columns=columns)


def extract_all_tables(metadata: MetaData) -> list[TableInfo]:
    return [extract_table_info(metadata, name) for name in metadata.tables]
