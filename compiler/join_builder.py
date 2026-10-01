"""
Spec §3.1: multi-table joins with explicit column mapping and compound
(AND/OR) conditions. Takes the base table + list of JoinConfig and returns
a single SQLAlchemy FromClause ready to select() from.
"""

from sqlalchemy import MetaData, and_, or_
from sqlalchemy.sql.selectable import FromClause

from compiler.request_schema import JoinConfig
from errors.exceptions import UnsupportedJoinTypeError
from security.identifiers import get_column, validate_table


def _build_condition(metadata: MetaData, join: JoinConfig):
    """Folds a list of JoinCondition into one boolean expression, honoring
    each condition's own boolean_op to decide how it joins the *next* one."""
    exprs = []
    for cond in join.conditions:
        left = get_column(metadata, cond.left_column)
        right = get_column(metadata, cond.right_column)
        exprs.append((left == right, cond.boolean_op))

    if not exprs:
        raise UnsupportedJoinTypeError(f"Join to '{join.target_table}' has no conditions.")

    combined = exprs[0][0]
    for expr, op in exprs[1:]:
        combined = and_(combined, expr) if op == "AND" else or_(combined, expr)
    return combined


def build_from_clause(
    metadata: MetaData,
    base_table: str,
    joins: list[JoinConfig],
    supported_join_types: tuple[str, ...],
) -> FromClause:
    validate_table(metadata, base_table)
    from_clause: FromClause = metadata.tables[base_table]

    for join in joins:
        if join.join_type not in supported_join_types:
            raise UnsupportedJoinTypeError(
                f"This data source does not support {join.join_type} OUTER JOIN "
                f"(supported: {', '.join(supported_join_types)})."
            )
        validate_table(metadata, join.target_table)
        target = metadata.tables[join.target_table]
        condition = _build_condition(metadata, join)

        if join.join_type == "INNER":
            from_clause = from_clause.join(target, condition)
        elif join.join_type == "LEFT":
            from_clause = from_clause.join(target, condition, isouter=True)
        elif join.join_type == "RIGHT":
            # SQLAlchemy Core has no native RIGHT JOIN — swap sides of a LEFT JOIN.
            from_clause = target.join(from_clause, condition, isouter=True)
        elif join.join_type == "FULL":
            from_clause = from_clause.join(target, condition, full=True)

    return from_clause
