"""
Spec §3.3: COUNT/SUM/AVG/MIN/MAX, and 'Automatically append all
non-aggregated selected fields into the GROUP BY clause when at least one
aggregation is specified.' That auto-GROUP-BY rule lives here because it's
directly derived from what this module builds.
"""

from sqlalchemy import MetaData, func

from compiler.request_schema import Aggregate, FieldSelection
from security.identifiers import get_column

_FUNC_MAP = {
    "COUNT": func.count,
    "SUM": func.sum,
    "AVG": func.avg,
    "MIN": func.min,
    "MAX": func.max,
}


def build_aggregate_columns(metadata: MetaData, aggregates: list[Aggregate]) -> list:
    columns = []
    for agg in aggregates:
        col = get_column(metadata, agg.column)
        sql_func = _FUNC_MAP[agg.func]
        columns.append(sql_func(col).label(agg.alias))
    return columns


def build_auto_group_by(
    metadata: MetaData,
    fields: list[FieldSelection],
    aggregates: list[Aggregate],
) -> list:
    """
    Rule: if there's at least one aggregate, every plain (non-aggregated)
    selected field must appear in GROUP BY, or the SQL is invalid on strict
    backends (Postgres/MSSQL reject it outright; MySQL silently gives
    nondeterministic results — worse).
    """
    if not aggregates:
        return []
    return [get_column(metadata, f.column) for f in fields]
