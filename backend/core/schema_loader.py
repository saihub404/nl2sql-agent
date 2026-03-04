"""
Schema Loader — introspects a PostgreSQL database to extract
tables, columns, data types, and foreign key relationships.
"""
from dataclasses import dataclass, field
from typing import Optional
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from backend.config import settings


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool = False


@dataclass
class ForeignKeyInfo:
    column: str
    references_table: str
    references_column: str


@dataclass
class TableSchema:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    description: str = ""          # human-readable summary for embeddings

    def to_embedding_text(self) -> str:
        """
        Produces a compact natural-language description of the table
        used as input to the sentence-transformer embedder.
        """
        col_summary = ", ".join(
            f"{c.name} ({c.data_type})" for c in self.columns
        )
        fk_summary = ""
        if self.foreign_keys:
            fk_parts = [
                f"{fk.column} -> {fk.references_table}.{fk.references_column}"
                for fk in self.foreign_keys
            ]
            fk_summary = f"; FK: {', '.join(fk_parts)}"
        return f"Table {self.name}: {col_summary}{fk_summary}"

    def to_prompt_text(self) -> str:
        """
        SQL CREATE-TABLE-style representation for injection into LLM prompt.
        Keeps tokens compact but expressive.
        """
        lines = [f"-- Table: {self.name}"]
        for col in self.columns:
            pk = " PRIMARY KEY" if col.is_primary_key else ""
            null = "" if col.is_nullable else " NOT NULL"
            lines.append(f"  {col.name}  {col.data_type}{pk}{null}")
        for fk in self.foreign_keys:
            lines.append(
                f"  -- FK: {fk.column} references "
                f"{fk.references_table}({fk.references_column})"
            )
        return "\n".join(lines)


class SchemaLoader:
    """
    Loads the full DB schema once at startup and caches it.
    Subsequent calls return the in-memory cache.
    """

    def __init__(self, engine: Optional[AsyncEngine] = None):
        self._engine = engine
        self._schema: dict[str, TableSchema] = {}

    async def _get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                settings.database_url,
                pool_pre_ping=True,
                echo=False,
            )
        return self._engine

    async def load(self) -> dict[str, TableSchema]:
        """
        Introspect the database and return a dict of table_name -> TableSchema.
        Caches result after first call.
        """
        if self._schema:
            return self._schema

        engine = await self._get_engine()

        async with engine.connect() as conn:
            # 1. Fetch all user tables
            table_rows = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [r[0] for r in table_rows.fetchall()]

            # 2. Fetch primary key info
            pk_rows = await conn.execute(text("""
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
            """))
            pk_map: dict[str, set[str]] = {}
            for row in pk_rows.fetchall():
                pk_map.setdefault(row[0], set()).add(row[1])

            # 3. Fetch foreign key info
            fk_rows = await conn.execute(text("""
                SELECT
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name AS references_table,
                    ccu.column_name AS references_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
            """))
            fk_map: dict[str, list[ForeignKeyInfo]] = {}
            for row in fk_rows.fetchall():
                fk_map.setdefault(row[0], []).append(
                    ForeignKeyInfo(
                        column=row[1],
                        references_table=row[2],
                        references_column=row[3],
                    )
                )

            # 4. Fetch columns for each table
            for table_name in tables:
                col_rows = await conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table
                    ORDER BY ordinal_position
                """), {"table": table_name})

                columns = [
                    ColumnInfo(
                        name=row[0],
                        data_type=row[1],
                        is_nullable=(row[2] == "YES"),
                        is_primary_key=row[0] in pk_map.get(table_name, set()),
                    )
                    for row in col_rows.fetchall()
                ]

                schema = TableSchema(
                    name=table_name,
                    columns=columns,
                    foreign_keys=fk_map.get(table_name, []),
                )
                self._schema[table_name] = schema

        return self._schema

    def get_cached(self) -> dict[str, TableSchema]:
        return self._schema


# Module-level singleton
schema_loader = SchemaLoader()
