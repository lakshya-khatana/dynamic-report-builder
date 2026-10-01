"""
Spec §5.3: 'For large exports, data must be fetched and streamed in chunks
rather than buffering the entire dataset in RAM.'
"""

from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select

from config import settings


def stream_rows(engine: Engine, stmt: Select) -> Iterator[tuple]:
    """
    Yields rows in chunks of settings.EXPORT_CHUNK_SIZE. The
    stream_results=True execution option tells the DBAPI driver itself not
    to buffer the full result server-side-cursor style — combined with
    fetchmany(), this is what actually keeps memory flat for a 10-lakh-row
    export.
    """
    with engine.connect().execution_options(stream_results=True) as conn:
        result = conn.execute(stmt)
        while True:
            chunk = result.fetchmany(settings.EXPORT_CHUNK_SIZE)
            if not chunk:
                break
            for row in chunk:
                yield row


def stream_column_names(engine: Engine, stmt: Select) -> list[str]:
    with engine.connect() as conn:
        result = conn.execute(stmt.limit(0))
        return list(result.keys())
