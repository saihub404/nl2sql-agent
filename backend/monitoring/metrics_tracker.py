"""
Metrics tracker & query log persistence.
Uses an async SQLite DB (aiosqlite) to store every query event
and compute rolling analytics.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func, case, delete

from backend.config import settings
from backend.models.db_models import Base, QueryLog
from backend.models.schemas import (
    MetricsResponse, ConfidenceBucket, FailureBreakdown, QueryHistoryItem, HistoryResponse
)


# ── Database engine for the log store ────────────────────────
_log_engine = create_async_engine(settings.log_database_url, echo=False)
_SessionLocal = async_sessionmaker(_log_engine, expire_on_commit=False)


async def init_log_db() -> None:
    """Create all log tables. Call once at startup."""
    async with _log_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def persist_query_log(
    nl_query: str,
    generated_sql: str | None,
    final_sql: str | None,
    confidence_score: float | None,
    tables_used: list[str],
    validation_passed: bool,
    validation_error: str | None,
    correction_attempts: int,
    correction_triggered: bool,
    execution_success: bool,
    execution_error: str | None,
    row_count: int | None,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> int:
    """Inserts a query log record and returns the new record ID."""
    log = QueryLog(
        timestamp=datetime.utcnow(),
        nl_query=nl_query,
        generated_sql=generated_sql,
        final_sql=final_sql,
        confidence_score=confidence_score,
        tables_used=",".join(tables_used) if tables_used else None,
        validation_passed=validation_passed,
        validation_error=validation_error,
        correction_attempts=correction_attempts,
        correction_triggered=correction_triggered,
        execution_success=execution_success,
        execution_error=execution_error,
        row_count=row_count,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    async with _SessionLocal() as session:
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log.id


async def get_history(limit: int = 50, offset: int = 0) -> HistoryResponse:
    """Returns paginated query history, newest first."""
    async with _SessionLocal() as session:
        total_result = await session.execute(select(func.count()).select_from(QueryLog))
        total = total_result.scalar() or 0

        rows_result = await session.execute(
            select(QueryLog)
            .order_by(QueryLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = rows_result.scalars().all()
        items = [QueryHistoryItem.model_validate(r) for r in rows]
        return HistoryResponse(items=items, total=total)


async def delete_history_items(item_ids: list[int]) -> int:
    """Deletes specific query history records by ID. Returns number deleted."""
    if not item_ids:
        return 0
    async with _SessionLocal() as session:
        result = await session.execute(
            delete(QueryLog).where(QueryLog.id.in_(item_ids))
        )
        await session.commit()
        return result.rowcount

async def clear_all_history() -> int:
    """Deletes all query history records. Returns number deleted."""
    async with _SessionLocal() as session:
        result = await session.execute(delete(QueryLog))
        await session.commit()
        return result.rowcount


async def get_metrics() -> MetricsResponse:
    """Computes aggregate metrics from the log store."""
    async with _SessionLocal() as session:
        result = await session.execute(
            select(
                func.count().label("total"),
                func.sum(case((QueryLog.execution_success.is_(True), 1), else_=0)).label("successes"),
                func.sum(case((QueryLog.correction_triggered.is_(True), 1), else_=0)).label("corrections"),
                func.avg(QueryLog.latency_ms).label("avg_latency"),
                func.avg(QueryLog.confidence_score).label("avg_confidence"),
                func.sum(case((QueryLog.validation_passed.is_(False), 1), else_=0)).label("val_failures"),
                func.sum(
                    case(
                        (
                            (QueryLog.validation_passed.is_(True)) &
                            (QueryLog.execution_success.is_(False)),
                            1
                        ),
                        else_=0
                    )
                ).label("exec_failures"),
            )
        )
        row = result.first()

        total = row.total or 0
        successes = row.successes or 0
        corrections = row.corrections or 0
        avg_latency = float(row.avg_latency or 0)
        avg_confidence = float(row.avg_confidence or 0)
        val_failures = row.val_failures or 0
        exec_failures = row.exec_failures or 0

        # Confidence distribution
        buckets_raw = await session.execute(
            select(
                case(
                    (QueryLog.confidence_score >= 0.9, "0.9–1.0"),
                    (QueryLog.confidence_score >= 0.8, "0.8–0.9"),
                    (QueryLog.confidence_score >= 0.7, "0.7–0.8"),
                    (QueryLog.confidence_score >= 0.6, "0.6–0.7"),
                    else_="< 0.6"
                ).label("bucket"),
                func.count().label("cnt"),
            )
            .where(QueryLog.confidence_score.is_not(None))
            .group_by("bucket")
        )
        confidence_dist = [
            ConfidenceBucket(bucket=r.bucket, count=r.cnt)
            for r in buckets_raw.fetchall()
        ]

        return MetricsResponse(
            total_queries=total,
            success_rate_pct=round(100.0 * successes / total, 1) if total else 0.0,
            correction_loop_rate_pct=round(100.0 * corrections / total, 1) if total else 0.0,
            avg_latency_ms=round(avg_latency, 1),
            avg_confidence_score=round(avg_confidence, 3),
            confidence_distribution=confidence_dist,
            failure_breakdown=FailureBreakdown(
                validation_failures=val_failures,
                execution_failures=exec_failures,
                low_confidence_rejections=0,  # tracked separately
            ),
        )
