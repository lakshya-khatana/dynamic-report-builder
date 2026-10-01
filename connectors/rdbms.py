"""
Connector for real relational databases. One pooled Engine per data source,
built fresh from decrypted credentials — never cached across sources.
"""

import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from connectors.base import BaseConnector, ConnectionTestResult
from security.readonly import attach_readonly_guard

_DRIVERS = {
    "postgresql": "postgresql+psycopg2",
    "mysql": "mysql+pymysql",
    "mssql": "mssql+pyodbc",
    "sqlite": "sqlite",
}


class RDBMSConnector(BaseConnector):
    """
    config expects:
        dialect: "postgresql" | "mysql" | "mssql" | "sqlite"
        host, port, database, username, password  (sqlite only needs "database" = file path)
        ssl_mode: optional, e.g. "require"
    """

    def __init__(self, source_id: str, config: dict):
        super().__init__(source_id, config)
        # SQLite has no FULL/RIGHT OUTER JOIN support; MySQL has no FULL OUTER JOIN
        dialect = config["dialect"]
        if dialect == "sqlite":
            self.supported_join_types = ("INNER", "LEFT")
        elif dialect == "mysql":
            self.supported_join_types = ("INNER", "LEFT", "RIGHT")
        else:
            self.supported_join_types = ("INNER", "LEFT", "RIGHT", "FULL")

    def _build_url(self) -> URL | str:
        cfg = self.config
        dialect = cfg["dialect"]
        driver = _DRIVERS[dialect]

        if dialect == "sqlite":
            return f"sqlite:///{cfg['database']}"

        query = {}
        if cfg.get("ssl_mode"):
            query["sslmode"] = cfg["ssl_mode"] if dialect == "postgresql" else cfg["ssl_mode"]
        if dialect == "mssql":
            query.setdefault("driver", "ODBC Driver 18 for SQL Server")

        return URL.create(
            drivername=driver,
            username=cfg.get("username"),
            password=cfg.get("password"),
            host=cfg.get("host"),
            port=cfg.get("port"),
            database=cfg.get("database"),
            query=query,
        )

    def _build_engine(self):
        url = self._build_url()
        is_sqlite = self.config["dialect"] == "sqlite"

        # SQLite's default pool (SingletonThreadPool) doesn't accept
        # pool_size/max_overflow/pool_timeout at all — passing them, even as
        # None, breaks create_engine. Only pass the QueuePool-specific knobs
        # for real server-based dialects.
        pool_kwargs = {} if is_sqlite else {
            "pool_size": settings.POOL_SIZE,
            "max_overflow": settings.MAX_OVERFLOW,
            "pool_timeout": settings.POOL_TIMEOUT_SECONDS,
        }

        engine = create_engine(
            url,
            pool_recycle=settings.POOL_RECYCLE_SECONDS,
            pool_pre_ping=True,  # drop dead connections instead of erroring mid-query
            **pool_kwargs,
        )
        # Spec §1.3 layer 2: block mutating SQL at the connection level, not
        # just in the compiler (see security/readonly.py for the event hook)
        attach_readonly_guard(engine)
        return engine

    def test_connection(self) -> ConnectionTestResult:
        start = time.perf_counter()
        try:
            # Deliberately build a throwaway engine here rather than calling
            # get_engine() — a test must never touch or warm the cached pool.
            probe_engine = self._build_engine()
            with probe_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            probe_engine.dispose()
            latency_ms = (time.perf_counter() - start) * 1000
            return ConnectionTestResult(ok=True, message="Connection successful.", latency_ms=latency_ms)
        except SQLAlchemyError as exc:
            # Spec §6: no raw stack traces to the end user
            return ConnectionTestResult(ok=False, message=f"Connection failed: {exc.__class__.__name__}")
