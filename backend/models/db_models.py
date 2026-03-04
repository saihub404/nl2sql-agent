"""
SQLAlchemy ORM models for the internal logging database.
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, BigInteger
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class QueryLog(Base):
    """Persists every query attempt with full metadata."""
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    nl_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    final_sql = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    tables_used = Column(String(500), nullable=True)

    validation_passed = Column(Boolean, default=False)
    validation_error = Column(Text, nullable=True)

    correction_attempts = Column(Integer, default=0)
    correction_triggered = Column(Boolean, default=False)

    execution_success = Column(Boolean, default=False)
    execution_error = Column(Text, nullable=True)
    row_count = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)

    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)


class UploadedDataset(Base):
    """Tracks every user-uploaded CSV/Parquet file ingested into the target DB."""
    __tablename__ = "uploaded_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), unique=True, nullable=False)
    original_filename = Column(String(300), nullable=False)
    row_count = Column(BigInteger, nullable=True)
    column_count = Column(Integer, nullable=True)
    file_size_mb = Column(Float, nullable=True)
    schema_json = Column(Text, nullable=True)     # JSON list of {name, pg_type, nullable}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), default="inferring", nullable=False)  # inferring|ingesting|ready|error
    error_message = Column(Text, nullable=True)
    rows_ingested = Column(BigInteger, default=0)
