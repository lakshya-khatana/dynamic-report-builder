"""
Spec §1.2: uploaded CSV/Excel files must be queryable with the same SQL
machinery as a real database. We load them into DuckDB (or in-memory SQLite
as a fallback) as a real table, then hand back a normal SQLAlchemy Engine —
everything downstream (reflection, compiler, executor) treats it identically
to a Postgres/MySQL source.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from config import settings
from connectors.base import BaseConnector, ConnectionTestResult


class FlatFileConnector(BaseConnector):
    """
    config expects:
        file_path: str — path to the uploaded .csv / .xlsx / .xls
        table_name: str — name to expose the staged table as
    """

    # Flat-file staging is a single table with no FK graph, so joins across
    # two *different* uploaded files aren't meaningful until both are staged
    # into the same engine — see reflection/join_recommender.py.
    supported_join_types = ("INNER", "LEFT")

    def _staging_url(self) -> str:
        if settings.STAGING_ENGINE == "duckdb":
            db_path = Path(settings.UPLOAD_DIR) / f"{self.source_id}.duckdb"
            return f"duckdb:///{db_path}"
        return f"sqlite:///{Path(settings.UPLOAD_DIR) / (self.source_id + '.sqlite')}"

    def _load_dataframe(self) -> pd.DataFrame:
        path = self.config["file_path"]
        suffix = Path(path).suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(path)
        raise ValueError(f"Unsupported flat-file type: {suffix}")

    def _build_engine(self):
        engine = create_engine(self._staging_url())
        df = self._load_dataframe()
        table_name = self.config["table_name"]
        # if_exists="replace" — re-uploading the same source_id refreshes the
        # staged table rather than duplicating rows underneath it
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        return engine

    def test_connection(self) -> ConnectionTestResult:
        try:
            df = self._load_dataframe()
            return ConnectionTestResult(
                ok=True,
                message=f"File readable: {len(df)} rows, {len(df.columns)} columns.",
            )
        except Exception as exc:  # noqa: BLE001 — surfaced as a clean user message only
            return ConnectionTestResult(ok=False, message=f"File could not be read: {exc.__class__.__name__}")
