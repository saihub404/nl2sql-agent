"""
FastAPI route — POST /api/query
Full pipeline: embed → generate → validate → correct → execute → log.
"""
import asyncio
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.models.schemas import NLQueryRequest, QueryResponse, ExecutionResult
from backend.core.llm_generator import llm_generator
from backend.core.schema_loader import schema_loader
from backend.core.correction_loop import run_pipeline, MaxRetriesExceeded
from backend.core.executor import query_executor
from backend.config import settings
from backend.monitoring.metrics_tracker import persist_query_log

router = APIRouter()

# Simple in-memory cache for dynamic prompts to avoid LLM spam on UI refresh
_prompts_cache = {}


@router.post("/query", response_model=QueryResponse)
async def handle_query(request: NLQueryRequest):
    start_ms = time.monotonic() * 1000
    nl_query = request.query.strip()

    # ── Run the generation + correction pipeline ─────────────
    correction_error: str | None = None
    exec_result: ExecutionResult | None = None
    exec_success = False
    exec_error: str | None = None

    try:
        pipeline = await run_pipeline(nl_query)
    except MaxRetriesExceeded as e:
        correction_error = str(e)
        latency_ms = round(time.monotonic() * 1000 - start_ms, 2)
        await persist_query_log(
            nl_query=nl_query,
            generated_sql=None,
            final_sql=None,
            confidence_score=None,
            tables_used=[],
            validation_passed=False,
            validation_error=correction_error,
            correction_attempts=settings.max_correction_retries,
            correction_triggered=True,
            execution_success=False,
            execution_error=correction_error,
            row_count=None,
            latency_ms=latency_ms,
        )
        raise HTTPException(status_code=422, detail=correction_error)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    # ── Reject low-confidence queries ────────────────────────
    if pipeline.llm_output.confidence_score < settings.confidence_threshold:
        latency_ms = round(time.monotonic() * 1000 - start_ms, 2)
        detail = (
            f"Confidence score {pipeline.llm_output.confidence_score:.2f} is below "
            f"threshold {settings.confidence_threshold}. Please rephrase your query "
            "or provide more specific information."
        )
        await persist_query_log(
            nl_query=nl_query,
            generated_sql=pipeline.generated_sql,
            final_sql=pipeline.final_sql,
            confidence_score=pipeline.llm_output.confidence_score,
            tables_used=pipeline.selected_tables,
            validation_passed=pipeline.validation_result.passed,
            validation_error=None,
            correction_attempts=pipeline.correction_attempts,
            correction_triggered=pipeline.correction_triggered,
            execution_success=False,
            execution_error="Low confidence rejection",
            row_count=None,
            latency_ms=latency_ms,
            prompt_tokens=pipeline.prompt_tokens,
            completion_tokens=pipeline.completion_tokens,
        )
        raise HTTPException(status_code=422, detail=detail)

    # ── Execute validated SQL ────────────────────────────────
    try:
        exec_result = await query_executor.execute(pipeline.final_sql)
        exec_success = True
    except asyncio.TimeoutError as e:
        exec_error = str(e)
    except Exception as e:
        exec_error = str(e)

    latency_ms = round(time.monotonic() * 1000 - start_ms, 2)

    # ── Persist log ──────────────────────────────────────────
    await persist_query_log(
        nl_query=nl_query,
        generated_sql=pipeline.generated_sql,
        final_sql=pipeline.final_sql,
        confidence_score=pipeline.llm_output.confidence_score,
        tables_used=pipeline.selected_tables,
        validation_passed=pipeline.validation_result.passed,
        validation_error=pipeline.validation_result.error,
        correction_attempts=pipeline.correction_attempts,
        correction_triggered=pipeline.correction_triggered,
        execution_success=exec_success,
        execution_error=exec_error,
        row_count=exec_result.row_count if exec_result else None,
        latency_ms=latency_ms,
        prompt_tokens=pipeline.prompt_tokens,
        completion_tokens=pipeline.completion_tokens,
    )

    return QueryResponse(
        nl_query=nl_query,
        generated_sql=pipeline.generated_sql,
        final_sql=pipeline.final_sql,
        confidence_score=pipeline.llm_output.confidence_score,
        tables_used=pipeline.selected_tables,
        similarity_scores=pipeline.similarity_scores,
        validation_status="passed" if pipeline.validation_result.passed else "failed",
        validation_error=pipeline.validation_result.error,
        correction_attempts=pipeline.correction_attempts,
        execution_success=exec_success,
        execution_error=exec_error,
        results=exec_result,
        latency_ms=latency_ms,
        raw_llm_output=pipeline.raw_llm_json,
    )


@router.get("/prompts")
async def get_dynamic_prompts():
    """Returns 4 dynamically generated business questions based on the current schema."""
    tables = await schema_loader.load()
    if not tables:
        return {"prompts": ["Upload a dataset to get started", "Show top 5 rows", "Count total records", "Show table summary"]}

    # Build schema-aware fallback prompts from the actual table/column names
    table_list = list(tables.values())
    first_table = table_list[0]
    table_name = first_table.name

    # Pick some column names for variety
    col_names = [c.name for c in first_table.columns]
    numeric_cols = [c.name for c in first_table.columns if c.data_type and any(t in c.data_type.lower() for t in ["int", "float", "numeric", "double", "decimal", "real"])]
    text_cols = [c.name for c in first_table.columns if c.data_type and any(t in c.data_type.lower() for t in ["varchar", "text", "char"])]

    def _schema_fallback():
        prompts = [f"Show top 5 rows from {table_name}"]
        if numeric_cols:
            prompts.append(f"What is the average {numeric_cols[0]} across all records?")
        elif col_names:
            prompts.append(f"Count total records grouped by {col_names[0]}")
        if text_cols:
            prompts.append(f"List distinct values in the {text_cols[0]} column")
        elif len(col_names) > 1:
            prompts.append(f"Group the data by {col_names[1]} and count records")
        prompts.append(f"Show me summary statistics for {table_name}")
        return prompts[:4]

    # Cache key based on table shape
    cache_key = "_".join(sorted(f"{t.name}:{len(t.columns)}" for t in tables.values()))
    if cache_key in _prompts_cache:
        return {"prompts": _prompts_cache[cache_key]}

    try:
        prompts = await llm_generator.generate_prompts(tables)
        safe_prompts = [p.strip() for p in prompts if isinstance(p, str) and len(p.strip()) > 3]

        # Pad with schema-aware fallbacks instead of generic defaults
        fallbacks = _schema_fallback()
        while len(safe_prompts) < 4:
            safe_prompts.append(fallbacks[len(safe_prompts) % len(fallbacks)])

        final_prompts = safe_prompts[:4]
        _prompts_cache[cache_key] = final_prompts
        return {"prompts": final_prompts}
    except Exception as e:
        print(f"Failed to generate dynamic prompts: {e}")
        # Use schema-aware fallback — not hardcoded generic strings
        fallback = _schema_fallback()
        _prompts_cache[cache_key] = fallback
        return {"prompts": fallback}


