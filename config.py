"""
Centralized configuration. Everything that could plausibly change between
dev / staging / a client's server lives here — never hardcode a limit or a
path inline in compiler/execution code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- App -----------------------------------------------------------
    ENV: str = "development"
    APP_DB_URL: str = "sqlite:///./storage/app.db"  # stores sources + templates metadata

    # --- Security --------------------------------------------------------
    # Fernet key for encrypting stored data-source credentials at rest.
    # Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = ""

    # --- Connection pooling (per data source, applied in connectors/rdbms.py) ---
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 5
    POOL_TIMEOUT_SECONDS: int = 30
    POOL_RECYCLE_SECONDS: int = 1800  # recycle idle conns before DB/firewall kills them

    # --- Query execution guards -------------------------------------------
    QUERY_TIMEOUT_SECONDS: int = 30
    PREVIEW_ROW_LIMIT: int = 100          # hard cap for interactive preview (Spec §5.1)
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500
    EXPORT_CHUNK_SIZE: int = 5000         # rows per fetchmany() chunk when streaming exports

    # --- Schema reflection cache --------------------------------------------
    SCHEMA_CACHE_TTL_SECONDS: int = 600   # re-reflect after this even if session is alive

    # --- File ingestion ------------------------------------------------------
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 200
    STAGING_ENGINE: str = "duckdb"        # "duckdb" or "sqlite" — see connectors/flatfile.py

    # --- Allowed SQL keywords guard (security/readonly.py) -----------------
    BLOCKED_KEYWORDS: tuple[str, ...] = (
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "EXEC",
        "TRUNCATE", "CREATE", "GRANT", "REVOKE",
    )


settings = Settings()
