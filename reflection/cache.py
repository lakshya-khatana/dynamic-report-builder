"""
Spec §2: 'Cache schema metadata per session/data source to avoid redundant
round-trips over the network.' In-memory dict is enough for a single-process
dev deployment; swap for Redis behind the same two functions if this ever
needs to run multi-process.
"""

import time

from sqlalchemy import MetaData

from config import settings

_cache: dict[str, tuple[float, MetaData]] = {}


def get_cached_metadata(source_id: str) -> MetaData | None:
    entry = _cache.get(source_id)
    if entry is None:
        return None
    cached_at, metadata = entry
    if time.time() - cached_at > settings.SCHEMA_CACHE_TTL_SECONDS:
        del _cache[source_id]
        return None
    return metadata


def set_cached_metadata(source_id: str, metadata: MetaData) -> None:
    _cache[source_id] = (time.time(), metadata)


def invalidate(source_id: str) -> None:
    """Call after any operation that could change the source's schema
    (e.g. re-uploading a flat file under the same source_id)."""
    _cache.pop(source_id, None)
