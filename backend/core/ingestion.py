"""
Ingestion Engine — bulk-loads CSV/Parquet data into PostgreSQL using
the COPY protocol via asyncpg for maximum throughput.

Strategy by file size:
  < 50 MB   → direct pandas load → COPY
  ≥ 50 MB   → chunked iterator (50K rows/batch) → streaming COPY
  Parquet   → pyarrow row-groups → COPY

Throughput target: 100K–500K rows/second.
"""
import asyncio
import io
import json
import csv
from pathlib import Path
from typing import AsyncGenerator, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from backend.config import settings
from backend.core.schema_inferrer import InferredSchema, ColDef

CHUNK_SIZE = 50_000   # rows per COPY batch


class IngestionEngine:
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None

    def _get_engine(self) -> AsyncEngine:
        """Uses the admin DATABASE_URL (needs CREATE TABLE + COPY permission)."""
        if self._engine is None:
            # Use admin URL — same host, admin user instead of readonly_user
            admin_url = settings.database_url.replace(
                "readonly_user:readonly_pass", "admin:admin_password"
            )
            self._engine = create_async_engine(admin_url, echo=False)
        return self._engine

    async def create_table(self, schema: InferredSchema) -> None:
        """Executes CREATE TABLE from inferred schema."""
        engine = self._get_engine()
        ddl = schema.create_table_sql(if_not_exists=True)
        async with engine.begin() as conn:
            await conn.execute(text(ddl))

    async def drop_table(self, table_name: str) -> None:
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

    async def copy_dataframe(
        self,
        df: pd.DataFrame,
        schema: InferredSchema,
        progress_callback=None,
    ) -> int:
        """
        Bulk-inserts a DataFrame into the target table using asyncpg COPY.
        Returns number of rows inserted.
        """
        import asyncpg

        # Parse the asyncpg DSN from SQLAlchemy URL
        # SQLAlchemy: postgresql+asyncpg://user:pass@host:port/db
        # asyncpg:    postgresql://user:pass@host:port/db
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        dsn = dsn.replace("readonly_user:readonly_pass", "admin:admin_password")

        conn = await asyncpg.connect(dsn)
        total_inserted = 0
        col_names = schema.column_names()

        try:
            for start in range(0, len(df), CHUNK_SIZE):
                chunk = df.iloc[start: start + CHUNK_SIZE]

                # Serialize chunk to CSV buffer for asyncpg COPY
                buf = io.StringIO()
                chunk_renamed = chunk.copy()
                chunk_renamed.columns = col_names
                chunk_renamed.to_csv(buf, index=False, header=False, na_rep="\\N")
                buf.seek(0)

                await conn.copy_to_table(
                    schema.table_name,
                    source=buf,
                    format="csv",
                    null="\\N",
                    columns=col_names,
                )
                total_inserted += len(chunk)
                if progress_callback:
                    await progress_callback(total_inserted)
        finally:
            await conn.close()

        return total_inserted

    async def ingest_file(
        self,
        file_bytes: bytes,
        filename: str,
        schema: InferredSchema,
        on_progress=None,
    ) -> int:
        """
        Main entry point — reads file in chunks and ingests via COPY.
        Calls on_progress(rows_done) after each chunk.
        Returns total rows ingested.
        """
        suffix = Path(filename).suffix.lower()
        file_size_mb = len(file_bytes) / 1_048_576

        if suffix == ".parquet":
            return await self._ingest_parquet(file_bytes, schema, on_progress)
        else:
            sep = "\t" if suffix == ".tsv" else ","
            if file_size_mb < 50:
                # Fast path: load all at once
                df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, low_memory=False)
                return await self.copy_dataframe(df, schema, on_progress)
            else:
                # Streaming path for large files
                return await self._ingest_large_csv(file_bytes, sep, schema, on_progress)

    async def _ingest_large_csv(self, file_bytes, sep, schema, on_progress) -> int:
        """Read CSV in 50K-row chunks, COPY each chunk."""
        import asyncpg
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        dsn = dsn.replace("readonly_user:readonly_pass", "admin:admin_password")
        conn = await asyncpg.connect(dsn)
        col_names = schema.column_names()
        total = 0

        try:
            reader = pd.read_csv(
                io.BytesIO(file_bytes),
                sep=sep,
                chunksize=CHUNK_SIZE,
                low_memory=False,
            )
            for chunk in reader:
                buf = io.StringIO()
                chunk.columns = col_names
                chunk.to_csv(buf, index=False, header=False, na_rep="\\N")
                buf.seek(0)
                await conn.copy_to_table(
                    schema.table_name,
                    source=buf,
                    format="csv",
                    null="\\N",
                    columns=col_names,
                )
                total += len(chunk)
                if on_progress:
                    await on_progress(total)
                # Yield control to the event loop between chunks
                await asyncio.sleep(0)
        finally:
            await conn.close()

        return total

    async def _ingest_parquet(self, file_bytes, schema, on_progress) -> int:
        """Stream Parquet row-groups via pyarrow."""
        import pyarrow.parquet as pq
        import asyncpg

        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        dsn = dsn.replace("readonly_user:readonly_pass", "admin:admin_password")
        conn = await asyncpg.connect(dsn)
        col_names = schema.column_names()
        total = 0

        try:
            pf = pq.ParquetFile(io.BytesIO(file_bytes))
            for batch in pf.iter_batches(batch_size=CHUNK_SIZE):
                chunk = batch.to_pandas()
                chunk.columns = col_names[:len(chunk.columns)]
                buf = io.StringIO()
                chunk.to_csv(buf, index=False, header=False, na_rep="\\N")
                buf.seek(0)
                await conn.copy_to_table(
                    schema.table_name,
                    source=buf,
                    format="csv",
                    null="\\N",
                    columns=col_names[:len(chunk.columns)],
                )
                total += len(chunk)
                if on_progress:
                    await on_progress(total)
                await asyncio.sleep(0)
        finally:
            await conn.close()

        return total


# Module-level singleton
ingestion_engine = IngestionEngine()
