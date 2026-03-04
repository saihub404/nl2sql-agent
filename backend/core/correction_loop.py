"""
Correction Loop — orchestrates the full NL → SQL pipeline with retry logic.
Combines: schema selection → LLM generation → validation → execution feedback.
"""
import time
from dataclasses import dataclass, field
from typing import Optional

from backend.config import settings
from backend.core.schema_loader import TableSchema, schema_loader
from backend.core.embedder import schema_embedder
from backend.core.llm_generator import llm_generator, LLMSQLOutput
from backend.core.validator import sql_validator
from backend.models.schemas import ValidationResult


class MaxRetriesExceeded(Exception):
    pass


@dataclass
class PipelineResult:
    """Full result from the correction loop pipeline."""
    nl_query: str
    generated_sql: str              # first LLM attempt
    final_sql: str                  # last SQL (possibly corrected)
    llm_output: LLMSQLOutput
    raw_llm_json: str
    validation_result: ValidationResult
    correction_attempts: int
    correction_triggered: bool
    selected_tables: list[str]
    similarity_scores: dict[str, float]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: list[str] = field(default_factory=list)


async def run_pipeline(nl_query: str) -> PipelineResult:
    """
    Full NL → SQL pipeline:
    1. Embed query → select top-K relevant tables
    2. LLM generates SQL
    3. Validate SQL
    4. If validation fails → re-inject error → retry (max 2 times)
    5. Return PipelineResult regardless of outcome

    Execution happens in the executor layer (not here).
    """
    max_retries = settings.max_correction_retries
    schema = schema_loader.get_cached()

    # ── Step 1: Schema selection ─────────────────────────────
    top_k_names, similarity_scores = schema_embedder.get_top_k_tables(nl_query)
    relevant_tables: dict[str, TableSchema] = {
        name: schema[name] for name in top_k_names if name in schema
    }

    # ── Step 2–4: Generation + validation loop ───────────────
    attempt = 0
    correction_triggered = False
    error_context: Optional[str] = None
    first_sql: Optional[str] = None
    last_result: Optional[PipelineResult] = None
    total_pt = 0
    total_ct = 0
    errors: list[str] = []

    while attempt <= max_retries:
        llm_out, raw_json, pt, ct = await llm_generator.generate(
            nl_query=nl_query,
            relevant_tables=relevant_tables,
            error_context=error_context,
        )
        total_pt += pt
        total_ct += ct
        sql = llm_out.sql_query

        if first_sql is None:
            first_sql = sql

        # Inject LIMIT for safety
        safe_sql = sql_validator.sanitize_limit(sql, settings.query_row_limit)

        # Validate
        validation = sql_validator.validate(safe_sql)

        if validation.passed:
            return PipelineResult(
                nl_query=nl_query,
                generated_sql=first_sql,
                final_sql=safe_sql,
                llm_output=llm_out,
                raw_llm_json=raw_json,
                validation_result=validation,
                correction_attempts=attempt,
                correction_triggered=correction_triggered,
                selected_tables=top_k_names,
                similarity_scores=similarity_scores,
                prompt_tokens=total_pt,
                completion_tokens=total_ct,
                errors=errors,
            )

        # Validation failed — prepare for retry
        errors.append(validation.error or "Unknown validation error")
        error_context = (
            f"SQL: {safe_sql}\n"
            f"Error: {validation.error}\n"
            "Please fix the SQL to address this error."
        )
        correction_triggered = True
        attempt += 1

    # All retries exhausted
    raise MaxRetriesExceeded(
        f"Could not generate valid SQL after {max_retries} correction attempts. "
        f"Last error: {errors[-1] if errors else 'unknown'}"
    )
