"""
Central configuration using pydantic-settings.
All values are read from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.1
    confidence_threshold: float = 0.6

    # ── Database ─────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://readonly_user:password@localhost:5432/mydb"
    )
    log_database_url: str = Field(
        default="sqlite+aiosqlite:///./nl2sql_logs.db"
    )

    # ── Embeddings ───────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k_tables: int = 5

    # ── Execution Limits ─────────────────────────────────────
    query_row_limit: int = 1000
    query_timeout_seconds: int = 10
    max_correction_retries: int = 2

    # ── API ──────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000


# Singleton instance used throughout the app
settings = Settings()
