"""
Spec §2: 'Utilize Primary-to-Foreign key relations to automatically
recommend candidate join fields between selected tables.'
"""

from dataclasses import dataclass

from sqlalchemy import MetaData

from security.identifiers import validate_table


@dataclass
class JoinCandidate:
    left_table: str
    left_column: str
    right_table: str
    right_column: str


def recommend_joins(metadata: MetaData, table_a: str, table_b: str) -> list[JoinCandidate]:
    """Direct FK relationships between exactly these two tables, either direction."""
    # Fail loudly on a bad table name instead of silently returning [] —
    # a typo'd or wrong-cased name looks identical to "genuinely no FK link"
    # otherwise, which is exactly the kind of silent failure Spec §6 rules out.
    validate_table(metadata, table_a)
    validate_table(metadata, table_b)

    candidates: list[JoinCandidate] = []

    for table_name, table in ((table_a, metadata.tables[table_a]), (table_b, metadata.tables[table_b])):
        for fk in table.foreign_keys:
            target_table = fk.column.table.name
            other = table_b if table_name == table_a else table_a
            if target_table == other:
                candidates.append(
                    JoinCandidate(
                        left_table=table_name,
                        left_column=fk.parent.name,
                        right_table=target_table,
                        right_column=fk.column.name,
                    )
                )
    return candidates


def build_fk_graph(metadata: MetaData) -> dict[str, list[JoinCandidate]]:
    """
    Adjacency list: table -> list of JoinCandidates reaching directly
    connected tables. Used by compiler/join_builder.py to resolve a join
    path when a user picks two tables that aren't directly FK-linked
    (walk the graph, e.g. via BFS, to find an intermediate table).
    """
    graph: dict[str, list[JoinCandidate]] = {name: [] for name in metadata.tables}

    for table_name, table in metadata.tables.items():
        for fk in table.foreign_keys:
            target = fk.column.table.name
            candidate = JoinCandidate(
                left_table=table_name,
                left_column=fk.parent.name,
                right_table=target,
                right_column=fk.column.name,
            )
            graph.setdefault(table_name, []).append(candidate)
            # Mirror the edge so BFS can walk either direction
            graph.setdefault(target, []).append(
                JoinCandidate(left_table=target, left_column=fk.column.name,
                              right_table=table_name, right_column=fk.parent.name)
            )
    return graph