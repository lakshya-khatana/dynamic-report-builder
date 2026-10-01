"""Spec §5.1: pagination + strict preview limit enforcement."""

from sqlalchemy.sql import Select

from config import settings
from errors.exceptions import CompileError


def paginate(stmt: Select, page: int, page_size: int) -> Select:
    if page < 1:
        raise CompileError("page must be >= 1")
    page_size = min(page_size, settings.MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    return stmt.limit(page_size).offset(offset)


def apply_preview_cap(stmt: Select) -> Select:
    """Used only for the interactive preview endpoint — always hard-capped
    regardless of what the request's page_size asked for (Spec §5.1)."""
    return stmt.limit(settings.PREVIEW_ROW_LIMIT)


def total_pages(total_rows: int, page_size: int) -> int:
    page_size = min(page_size, settings.MAX_PAGE_SIZE) or 1
    return (total_rows + page_size - 1) // page_size
