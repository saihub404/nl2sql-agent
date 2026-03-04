"""
Pydantic schemas for all API request/response contracts.
"""
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


# ─── Request ────────────────────────────────────────────────

class NLQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language question")
    database_schema: Optional[dict] = Field(default=None)


# ─── LLM Output ─────────────────────────────────────────────

class LLMSQLOutput(BaseModel):
    sql_query: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    tables_used: list[str]


# ─── Validation ─────────────────────────────────────────────

class ValidationResult(BaseModel):
    passed: bool
    error: Optional[str] = None


# ─── Execution ──────────────────────────────────────────────

class ExecutionResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float


# ─── Full Query Response ─────────────────────────────────────

class QueryResponse(BaseModel):
    nl_query: str
    generated_sql: str
    final_sql: str
    confidence_score: float
    tables_used: list[str]
    similarity_scores: dict[str, float]
    validation_status: str
    validation_error: Optional[str]
    correction_attempts: int
    execution_success: bool
    execution_error: Optional[str]
    results: Optional[ExecutionResult]
    latency_ms: float
    raw_llm_output: Optional[str]


# ─── History ────────────────────────────────────────────────

class QueryHistoryItem(BaseModel):
    id: int
    timestamp: datetime
    nl_query: str
    final_sql: Optional[str]
    confidence_score: Optional[float]
    validation_passed: bool
    execution_success: bool
    correction_attempts: int
    latency_ms: Optional[float]
    row_count: Optional[int]

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: list[QueryHistoryItem]
    total: int


# ─── Metrics ────────────────────────────────────────────────

class ConfidenceBucket(BaseModel):
    bucket: str
    count: int


class FailureBreakdown(BaseModel):
    validation_failures: int
    execution_failures: int
    low_confidence_rejections: int


class MetricsResponse(BaseModel):
    total_queries: int
    success_rate_pct: float
    correction_loop_rate_pct: float
    avg_latency_ms: float
    avg_confidence_score: float
    confidence_distribution: list[ConfidenceBucket]
    failure_breakdown: FailureBreakdown


# ─── Upload / Dataset ────────────────────────────────────────

class InferredColumnSchema(BaseModel):
    name: str
    original_name: str
    pg_type: str
    nullable: bool
    date_detected: bool


class UploadInitResponse(BaseModel):
    dataset_id: int
    table_name: str
    original_filename: str
    file_size_mb: float
    inferred_columns: list[InferredColumnSchema]
    row_estimate: int
    status: str


class UploadProgressResponse(BaseModel):
    dataset_id: int
    table_name: str
    status: str
    rows_ingested: int
    row_count: Optional[int]
    pct: float
    error_message: Optional[str] = None


class DatasetResponse(BaseModel):
    id: int
    table_name: str
    original_filename: str
    row_count: Optional[int]
    column_count: Optional[int]
    file_size_mb: Optional[float]
    status: str
    created_at: datetime
    rows_ingested: int

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]
    total: int
