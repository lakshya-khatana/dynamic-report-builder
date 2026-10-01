"""Spec §3.5: multi-column sort with direction and priority sequencing."""

from sqlalchemy import MetaData, asc, desc

from compiler.request_schema import SortRule
from security.identifiers import get_column


def build_order_by(metadata: MetaData, sort_rules: list[SortRule], alias_lookup: dict[str, object]):
    """
    alias_lookup maps an alias string (from an Aggregate or aliased field) to
    its already-built SQLAlchemy column expression, since you can ORDER BY
    an aggregate alias that doesn't exist as a raw column on any table.
    """
    ordered_rules = sorted(sort_rules, key=lambda r: r.priority)
    clauses = []
    for rule in ordered_rules:
        if rule.column in alias_lookup:
            target = alias_lookup[rule.column]
        else:
            target = get_column(metadata, rule.column)
        clauses.append(asc(target) if rule.direction == "ASC" else desc(target))
    return clauses
