"""
FastAPI route — POST /api/query
Full pipeline: embed → generate → validate → correct → execute → log.
"""
import asyncio
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.models.schemas import NLQueryRequest, QueryResponse, ExecutionResult
from backend.core.correction_loop import run_pipeline, MaxRetriesExceeded
from backend.core.executor import query_executor
from backend.config import settings
from backend.monitoring.metrics_tracker import persist_query_log

router = APIRouter()


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
