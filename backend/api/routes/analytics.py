"""
FastAPI routes — GET /api/history and GET /api/metrics.
"""
from fastapi import APIRouter, Query
from backend.monitoring.metrics_tracker import get_history, get_metrics
from backend.models.schemas import HistoryResponse, MetricsResponse

history_router = APIRouter()
metrics_router = APIRouter()


@history_router.get("/history", response_model=HistoryResponse)
async def query_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Returns paginated query history, newest first."""
    return await get_history(limit=limit, offset=offset)


@metrics_router.get("/metrics", response_model=MetricsResponse)
async def query_metrics():
    """Returns aggregate performance metrics."""
    return await get_metrics()
