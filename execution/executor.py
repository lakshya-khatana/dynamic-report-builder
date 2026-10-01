"""Spec §6 'Data Execution Service': pooling, timeouts, error handling."""

import time
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.sql import Select

from config import settings
from errors.exceptions import ConnectionTimeoutError, CompileError


@dataclass
class ExecutionResult:
    columns: list[str]
    rows: list[tuple]
    latency_ms: float
    row_count_estimate: int | None = None


def execute_statement(engine: Engine, stmt: Select, count_stmt: Select | None = None) -> ExecutionResult:
    start = time.perf_counter()
    try:
        with engine.connect().execution_options(
            timeout=settings.QUERY_TIMEOUT_SECONDS
        ) as conn:
            result = conn.execute(stmt)
            columns = list(result.keys())
            rows = result.fetchall()

            row_count_estimate = None
            if count_stmt is not None:
                row_count_estimate = conn.execute(count_stmt).scalar()

        latency_ms = (time.perf_counter() - start) * 1000
        return ExecutionResult(columns=columns, rows=rows, latency_ms=latency_ms, row_count_estimate=row_count_estimate)

    except OperationalError as exc:
        if "timeout" in str(exc).lower():
            raise ConnectionTimeoutError("Query exceeded the configured timeout.") from None
        raise CompileError(f"Database error: {exc.__class__.__name__}") from None
    except SQLAlchemyError as exc:
        # Spec §6 — never leak the raw exception/stack trace to the caller
        raise CompileError(f"Query execution failed: {exc.__class__.__name__}") from None
