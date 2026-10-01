"""Spec §3.2: checkbox-driven field selection + custom aliasing."""

from sqlalchemy import MetaData

from compiler.request_schema import FieldSelection
from security.identifiers import get_column


def build_selected_columns(metadata: MetaData, fields: list[FieldSelection]) -> list:
    columns = []
    for f in fields:
        col = get_column(metadata, f.column)
        columns.append(col.label(f.alias) if f.alias else col)
    return columns
