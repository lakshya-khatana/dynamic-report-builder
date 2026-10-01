"""
SQLAlchemy's bound parameters protect *values* from injection. They cannot
protect *identifiers* (table/column names) because SQL syntax doesn't allow
binding those. So identifiers get a different kind of protection: every one
that reaches the compiler must already exist in the reflected schema for
that source. If it's not in the whitelist, it's rejected before it ever
touches string formatting.
"""

from sqlalchemy import MetaData

from errors.exceptions import UnknownIdentifierError


def validate_table(metadata: MetaData, table_name: str) -> None:
    if table_name not in metadata.tables:
        raise UnknownIdentifierError(f"Table '{table_name}' is not part of this source's reflected schema.")


def validate_column(metadata: MetaData, table_name: str, column_name: str) -> None:
    validate_table(metadata, table_name)
    table = metadata.tables[table_name]
    if column_name not in table.columns:
        raise UnknownIdentifierError(f"Column '{table_name}.{column_name}' does not exist.")


def get_column(metadata: MetaData, qualified_name: str):
    """
    qualified_name like 'orders.amount'. Validates then returns the actual
    SQLAlchemy Column object — callers should always get columns through
    here rather than building 'table.column' strings by hand.
    """
    try:
        table_name, column_name = qualified_name.split(".", 1)
    except ValueError:
        raise UnknownIdentifierError(f"Expected 'table.column', got '{qualified_name}'") from None

    validate_column(metadata, table_name, column_name)
    return metadata.tables[table_name].columns[column_name]
