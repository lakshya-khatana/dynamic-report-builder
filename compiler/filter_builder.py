"""
Spec §3.4 filter operator table. One function per data-type family, all
returning a plain SQLAlchemy boolean expression — every value flows through
as a *bound parameter* (never string-interpolated), which is what actually
prevents injection here (identifiers are separately protected in
security/identifiers.py).
"""

from sqlalchemy import MetaData, and_

from compiler.relative_dates import resolve_relative_range
from compiler.request_schema import Filter
from errors.exceptions import CompileError
from security.identifiers import get_column


def _string_condition(col, op: str, value):
    if op == "eq":
        return func_ilike_eq(col, value)
    if op == "ne":
        return col != value
    if op == "contains":
        return col.ilike(f"%{value}%")
    if op == "starts_with":
        return col.ilike(f"{value}%")
    if op == "ends_with":
        return col.ilike(f"%{value}")
    if op == "in":
        return col.in_(value)
    raise CompileError(f"Unsupported string operator: {op}")


def func_ilike_eq(col, value):
    # Spec: "Case-insensitive options" for string equality too, not just contains.
    return col.ilike(value)


def _numeric_condition(col, op: str, value):
    if op == "eq":
        return col == float(value)
    if op == "ne":
        return col != float(value)
    if op == "gt":
        return col > float(value)
    if op == "gte":
        return col >= float(value)
    if op == "lt":
        return col < float(value)
    if op == "lte":
        return col <= float(value)
    if op == "between":
        lo, hi = value
        return col.between(float(lo), float(hi))
    raise CompileError(f"Unsupported numeric operator: {op}")


def _datetime_condition(col, op: str, value, relative: str | None):
    if op == "relative":
        if not relative:
            raise CompileError("'relative' operator requires a relative-range keyword.")
        start, end = resolve_relative_range(relative)
        return and_(col >= start, col < end)
    if op == "eq":
        return col == value
    if op == "before":
        return col < value
    if op == "after":
        return col > value
    if op == "between":
        lo, hi = value
        return col.between(lo, hi)
    raise CompileError(f"Unsupported datetime operator: {op}")


def build_filter_condition(metadata: MetaData, filt: Filter):
    col = get_column(metadata, filt.column)
    python_type = col.type.python_type.__name__ if hasattr(col.type, "python_type") else "str"

    if filt.op == "relative" or python_type in ("datetime", "date"):
        return _datetime_condition(col, filt.op, filt.value, filt.relative)
    if python_type in ("int", "float", "Decimal"):
        return _numeric_condition(col, filt.op, filt.value)
    return _string_condition(col, filt.op, filt.value)


def build_where_clause(metadata: MetaData, filters: list[Filter]):
    if not filters:
        return None
    conditions = [build_filter_condition(metadata, f) for f in filters]
    return and_(*conditions)
