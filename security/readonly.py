"""
Spec §1.3: 'Strict Read-Only Enforcement ... blocked at both compiler and
database connection levels.' Two independent layers on purpose — if the
compiler ever has a bug that lets a mutating statement through, this second
layer at the connection is the last line of defense.
"""

import re

from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import settings
from errors.exceptions import ReadOnlyViolationError

# Matches a blocked keyword as a whole word, so "SELECT * FROM updates" isn't
# wrongly flagged just because "updates" contains "UPDATE".
_KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(settings.BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def check_readonly(sql: str) -> None:
    """Layer 1 — call this on the compiled SQL string before ever executing it."""
    match = _KEYWORD_PATTERN.search(sql)
    if match:
        raise ReadOnlyViolationError(
            f"Blocked keyword '{match.group(1).upper()}' is not permitted — this engine is read-only."
        )


def attach_readonly_guard(engine: Engine) -> None:
    """
    Layer 2 — hooks every outgoing statement on this specific engine, right
    before it hits the DBAPI cursor. Catches anything layer 1 missed
    (e.g. a raw SQL string handed in from somewhere layer 1 wasn't called).
    """

    @event.listens_for(engine, "before_cursor_execute")
    def _guard(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        check_readonly(statement)
