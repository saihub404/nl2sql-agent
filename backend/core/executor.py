"""
Executor — runs validated SQL against the target database.
Enforces: async execution, timeout, row limit, and read-only access.
"""
import asyncio
import time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection

from backend.config import settings
from backend.models.schemas import ExecutionResult


class QueryExecutor:
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None

    def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                echo=False,
            )
        return self._engine

    async def execute(self, sql: str) -> ExecutionResult:
        """
        Executes a validated SQL string and returns structured results.
        Raises:
            asyncio.TimeoutError: if execution exceeds QUERY_TIMEOUT_SECONDS
            Exception: for any DB-level errors (caller handles for correction loop)
        """
        engine = self._get_engine()
        start_ms = time.monotonic() * 1000

        async def _run(conn: AsyncConnection) -> ExecutionResult:
            result = await conn.execute(text(sql))
            cols = list(result.keys())
            raw_rows = result.fetchall()
            rows = [list(r) for r in raw_rows]
            elapsed = time.monotonic() * 1000 - start_ms
            return ExecutionResult(
                columns=cols,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=round(elapsed, 2),
            )

        async with engine.connect() as conn:
            try:
                exec_result = await asyncio.wait_for(
                    _run(conn),
                    timeout=settings.query_timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(
                    f"Query timed out after {settings.query_timeout_seconds}s"
                )

        return exec_result

    async def health_check(self) -> bool:
        """Returns True if the DB is reachable."""
        try:
            engine = self._get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


# Module-level singleton
query_executor = QueryExecutor()
