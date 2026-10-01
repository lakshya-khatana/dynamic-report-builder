"""
Every connector (Postgres, MySQL, MSSQL, SQLite, flat-file) implements this
same interface. Nothing outside connectors/ should ever import a specific
connector class directly — always go through registry.get_connector().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine


@dataclass
class ConnectionTestResult:
    ok: bool
    message: str
    latency_ms: float | None = None


class BaseConnector(ABC):
    """One instance = one configured data source."""

    #: which JOIN types this backend actually supports (Spec §3.1 — MySQL/
    #: SQLite have no FULL OUTER JOIN; callers must check this before compiling)
    supported_join_types: tuple[str, ...] = ("INNER", "LEFT", "RIGHT", "FULL")

    def __init__(self, source_id: str, config: dict[str, Any]):
        self.source_id = source_id
        self.config = config
        self._engine: Engine | None = None

    @abstractmethod
    def _build_engine(self) -> Engine:
        """Construct (but do not necessarily connect) the SQLAlchemy Engine."""
        raise NotImplementedError

    def get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Independent validation — must not require an app restart or rely
        on any cached engine (Spec §1.1 'Test Connection Routine')."""
        raise NotImplementedError

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
