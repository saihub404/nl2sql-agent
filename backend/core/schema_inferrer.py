"""
Schema Inferrer — samples a CSV/Parquet file and maps dtypes to PostgreSQL types.
Returns an InferredSchema ready to drive CREATE TABLE + COPY ingestion.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import io

import pandas as pd

# ── dtype → PostgreSQL type mapping ─────────────────────────

DTYPE_MAP: dict[str, str] = {
    "int8":    "SMALLINT",
    "int16":   "SMALLINT",
    "int32":   "INTEGER",
    "int64":   "BIGINT",
    "uint8":   "SMALLINT",
    "uint16":  "INTEGER",
    "uint32":  "BIGINT",
    "uint64":  "BIGINT",
    "float16": "REAL",
    "float32": "REAL",
    "float64": "DOUBLE PRECISION",
    "bool":    "BOOLEAN",
    "object":  "TEXT",
    "string":  "TEXT",
    "category":"TEXT",
}

DATETIME_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}",          # 2024-01-01
    r"\d{2}/\d{2}/\d{4}",          # 01/01/2024
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}",  # ISO datetime
]

SAMPLE_ROWS = 10_000   # rows to sample for type inference


@dataclass
class ColDef:
    name: str              # sanitized column name (safe for SQL)
    original_name: str     # as it appeared in the file
    pg_type: str           # PostgreSQL type
    nullable: bool = True
    date_detected: bool = False

    def ddl_fragment(self) -> str:
        null = "" if self.nullable else " NOT NULL"
        return f'"{self.name}" {self.pg_type}{null}'


@dataclass
class InferredSchema:
    table_name: str
    columns: list[ColDef] = field(default_factory=list)
    row_estimate: int = 0
    file_size_mb: float = 0.0

    def create_table_sql(self, if_not_exists: bool = True) -> str:
        exists = "IF NOT EXISTS " if if_not_exists else ""
        cols = ",\n  ".join(c.ddl_fragment() for c in self.columns)
        return f'CREATE TABLE {exists}"{self.table_name}" (\n  {cols}\n);'

    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


def _sanitize_column(name: str) -> str:
    """Make a column name safe for PostgreSQL identifiers."""
    # Normalize unicode
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    # Replace non-alphanumeric with underscore
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    # Must not start with a digit
    if name and name[0].isdigit():
        name = "col_" + name
    # Lowercase
    name = name.lower()
    # Truncate to 60 chars (PG limit is 63)
    return name[:60] or "col"


def _sanitize_table(filename: str) -> str:
    """Generate a safe table name from a filename."""
    stem = Path(filename).stem
    return _sanitize_column(stem)[:40]


def _infer_col_type(series: pd.Series) -> tuple[str, bool]:
    """
    Returns (pg_type, date_detected).
    Tries datetime parsing on TEXT columns that look like dates.
    """
    dtype_str = str(series.dtype)

    # Already a datetime dtype
    if "datetime" in dtype_str:
        return "TIMESTAMPTZ", True

    pg_type = DTYPE_MAP.get(dtype_str, "TEXT")

    # Try to detect dates in object/string columns
    if pg_type == "TEXT":
        sample = series.dropna().astype(str).head(200)
        for pat in DATETIME_PATTERNS:
            if sample.str.match(pat).mean() > 0.8:
                return "TIMESTAMPTZ", True

    return pg_type, False


def infer_schema_from_bytes(
    file_bytes: bytes,
    filename: str,
    table_name_override: Optional[str] = None,
) -> InferredSchema:
    """
    Main entry point. Reads the first SAMPLE_ROWS rows from a
    CSV or Parquet file and returns an InferredSchema.
    """
    file_size_mb = round(len(file_bytes) / 1_048_576, 2)
    suffix = Path(filename).suffix.lower()
    buf = io.BytesIO(file_bytes)

    if suffix in (".parquet",):
        try:
            import pyarrow.parquet as pq
            table = pq.read_table(buf).slice(0, SAMPLE_ROWS)
            df = table.to_pandas()
        except ImportError:
            raise ValueError("pyarrow is required for Parquet files. Install it with: pip install pyarrow")
    elif suffix in (".csv", ".tsv", ".txt"):
        sep = "\t" if suffix == ".tsv" else ","
        df = pd.read_csv(buf, sep=sep, nrows=SAMPLE_ROWS, low_memory=False)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .csv, .tsv, or .parquet")

    # Build sanitized table name
    base_name = table_name_override or _sanitize_table(filename)
    import uuid
    short_id = uuid.uuid4().hex[:6]
    table_name = f"upload_{short_id}_{base_name}"

    # Build column definitions
    columns: list[ColDef] = []
    seen_names: set[str] = set()

    for orig_name in df.columns:
        safe = _sanitize_column(str(orig_name))
        # Deduplicate column names
        if safe in seen_names:
            safe = f"{safe}_{len(seen_names)}"
        seen_names.add(safe)

        series = df[orig_name]
        pg_type, date_detected = _infer_col_type(series)
        nullable = bool(series.isna().any())

        columns.append(ColDef(
            name=safe,
            original_name=str(orig_name),
            pg_type=pg_type,
            nullable=nullable,
            date_detected=date_detected,
        ))

    return InferredSchema(
        table_name=table_name,
        columns=columns,
        row_estimate=len(df),
        file_size_mb=file_size_mb,
    )
