"""
Spec §6 'Query Compiler Service': the only function anything outside
compiler/ should call. Takes a validated ReportRequest + reflected metadata,
returns a ready-to-execute SQLAlchemy Select — never a raw SQL string.
"""

from dataclasses import dataclass

from sqlalchemy import MetaData, func, select
from sqlalchemy.sql import Select

from compiler.aggregate_builder import build_aggregate_columns, build_auto_group_by
from compiler.field_builder import build_selected_columns
from compiler.filter_builder import build_where_clause
from compiler.join_builder import build_from_clause
from compiler.request_schema import ReportRequest
from compiler.sort_builder import build_order_by
from security.readonly import check_readonly


@dataclass
class CompiledReport:
    statement: Select
    count_statement: Select  # same filters/joins, no pagination — for total-row count


def compile_report(
    metadata: MetaData,
    request: ReportRequest,
    supported_join_types: tuple[str, ...],
) -> CompiledReport:
    from_clause = build_from_clause(metadata, request.base_table, request.joins, supported_join_types)

    field_columns = build_selected_columns(metadata, request.fields)
    agg_columns = build_aggregate_columns(metadata, request.aggregates)
    all_columns = field_columns + agg_columns

    stmt = select(*all_columns).select_from(from_clause)

    where_clause = build_where_clause(metadata, request.filters)
    if where_clause is not None:
        stmt = stmt.where(where_clause)

    group_by_cols = build_auto_group_by(metadata, request.fields, request.aggregates)
    if group_by_cols:
        stmt = stmt.group_by(*group_by_cols)

    having_clause = build_where_clause(metadata, request.having)
    if having_clause is not None:
        stmt = stmt.having(having_clause)

    # Aliases (both plain field aliases and aggregate aliases) become
    # sortable by name even though they're not raw table columns.
    alias_lookup = {c._label: c for c in all_columns if getattr(c, "_label", None)}
    order_clauses = build_order_by(metadata, request.sort, alias_lookup)
    if order_clauses:
        stmt = stmt.order_by(*order_clauses)

    # Compile to a plain string purely to run it through the keyword guard —
    # defense in depth alongside the connection-level hook in security/readonly.py.
    check_readonly(str(stmt.compile(compile_kwargs={"literal_binds": False})))

    # Row-count query: same shape pre-pagination, wrapped in an outer COUNT(*)
    # so GROUP BY / HAVING (which already collapse rows) are counted correctly.
    base_for_count = select(*all_columns).select_from(from_clause)
    if where_clause is not None:
        base_for_count = base_for_count.where(where_clause)
    if group_by_cols:
        base_for_count = base_for_count.group_by(*group_by_cols)
    if having_clause is not None:
        base_for_count = base_for_count.having(having_clause)
    count_stmt = select(func.count()).select_from(base_for_count.subquery())

    return CompiledReport(statement=stmt, count_statement=count_stmt)
