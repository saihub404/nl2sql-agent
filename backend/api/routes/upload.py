"""
Upload API routes:
  POST   /api/upload                    — infer schema + start ingestion (async background)
  GET    /api/upload/progress/{id}      — poll ingestion progress
  GET    /api/datasets                  — list all uploaded datasets
  DELETE /api/datasets/{table_name}     — drop table + remove from registry + FAISS
"""
import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, delete
from typing import Optional

from backend.monitoring.metrics_tracker import _SessionLocal, _log_engine
from backend.models.db_models import Base, UploadedDataset
from backend.models.schemas import (
    UploadInitResponse, UploadProgressResponse,
    DatasetResponse, DatasetListResponse, InferredColumnSchema,
)
from backend.core.schema_inferrer import infer_schema_from_bytes, InferredSchema
from backend.core.ingestion import ingestion_engine
from backend.core.schema_loader import schema_loader, TableSchema, ColumnInfo
from backend.core.embedder import schema_embedder

router = APIRouter()

MAX_FILE_SIZE_MB = 2048   # 2 GB hard limit


async def _ensure_dataset_table():
    """Ensure the uploaded_datasets table exists in the log DB."""
    async with _log_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _run_ingestion(
    dataset_id: int,
    file_bytes: bytes,
    filename: str,
    schema: InferredSchema,
):
    """
    Background task: create table → bulk ingest → update status → rebuild FAISS.
    """
    async def _update_progress(rows_done: int):
        async with _SessionLocal() as session:
            ds = await session.get(UploadedDataset, dataset_id)
            if ds:
                ds.rows_ingested = rows_done
                await session.commit()

    async with _SessionLocal() as session:
        ds = await session.get(UploadedDataset, dataset_id)
        if not ds:
            return
        ds.status = "ingesting"
        await session.commit()

    try:
        # Create the table
        await ingestion_engine.create_table(schema)

        # Stream data in
        total = await ingestion_engine.ingest_file(
            file_bytes, filename, schema, on_progress=_update_progress
        )

        # Mark ready
        async with _SessionLocal() as session:
            ds = await session.get(UploadedDataset, dataset_id)
            if ds:
                ds.status = "ready"
                ds.row_count = total
                ds.rows_ingested = total
                await session.commit()

        # Hot-reload FAISS: build TableSchema from inferred schema
        col_infos = [
            ColumnInfo(
                name=c.name,
                data_type=c.pg_type,
                is_nullable=c.nullable,
                is_primary_key=False,
            )
            for c in schema.columns
        ]
        ts = TableSchema(name=schema.table_name, columns=col_infos)
        ts.description = ts.to_embedding_text()

        # Add to schema cache + FAISS
        schema_loader.get_cached()[schema.table_name] = ts
        schema_embedder.add_table(schema.table_name, ts)

    except Exception as e:
        async with _SessionLocal() as session:
            ds = await session.get(UploadedDataset, dataset_id)
            if ds:
                ds.status = "error"
                ds.error_message = str(e)
                await session.commit()
        # Clean up partial table
        try:
            await ingestion_engine.drop_table(schema.table_name)
        except Exception:
            pass


@router.post("/upload", response_model=UploadInitResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    table_name_override: Optional[str] = Form(default=None),
):
    """Accepts a CSV/Parquet file, infers schema, starts background ingestion."""
    await _ensure_dataset_table()

    filename = file.filename or "upload.csv"
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / 1_048_576

    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB."
        )

    # Infer schema
    try:
        schema = infer_schema_from_bytes(file_bytes, filename, table_name_override)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Register dataset in log DB
    schema_json = json.dumps([
        {"name": c.name, "original_name": c.original_name, "pg_type": c.pg_type,
         "nullable": c.nullable, "date_detected": c.date_detected}
        for c in schema.columns
    ])

    async with _SessionLocal() as session:
        ds = UploadedDataset(
            table_name=schema.table_name,
            original_filename=filename,
            column_count=len(schema.columns),
            file_size_mb=round(file_size_mb, 2),
            schema_json=schema_json,
            created_at=datetime.utcnow(),
            status="inferring",
            rows_ingested=0,
        )
        session.add(ds)
        await session.commit()
        await session.refresh(ds)
        dataset_id = ds.id

    # Launch background ingestion
    background_tasks.add_task(_run_ingestion, dataset_id, file_bytes, filename, schema)

    return UploadInitResponse(
        dataset_id=dataset_id,
        table_name=schema.table_name,
        original_filename=filename,
        file_size_mb=round(file_size_mb, 2),
        inferred_columns=[
            InferredColumnSchema(
                name=c.name, original_name=c.original_name,
                pg_type=c.pg_type, nullable=c.nullable,
                date_detected=c.date_detected,
            )
            for c in schema.columns
        ],
        row_estimate=schema.row_estimate,
        status="ingesting",
    )


@router.get("/upload/progress/{dataset_id}", response_model=UploadProgressResponse)
async def get_upload_progress(dataset_id: int):
    """Poll ingestion progress for a given dataset."""
    await _ensure_dataset_table()
    async with _SessionLocal() as session:
        ds = await session.get(UploadedDataset, dataset_id)
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not found")

        total = ds.row_count or 0
        ingested = ds.rows_ingested or 0
        pct = (ingested / total * 100) if total > 0 else (100.0 if ds.status == "ready" else 0.0)

        return UploadProgressResponse(
            dataset_id=ds.id,
            table_name=ds.table_name,
            status=ds.status,
            rows_ingested=ingested,
            row_count=ds.row_count,
            pct=round(pct, 1),
            error_message=ds.error_message,
        )


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets():
    """List all registered uploaded datasets."""
    await _ensure_dataset_table()
    async with _SessionLocal() as session:
        result = await session.execute(
            select(UploadedDataset).order_by(UploadedDataset.created_at.desc())
        )
        datasets = result.scalars().all()
        count_result = await session.execute(select(func.count()).select_from(UploadedDataset))
        total = count_result.scalar() or 0

    return DatasetListResponse(
        datasets=[DatasetResponse.model_validate(d) for d in datasets],
        total=total,
    )


@router.get("/schema")
async def get_schema():
    """Return schema columns for UI display."""
    schema_map = schema_loader.get_cached()
    return {
        table_name: [{"name": col.name, "type": col.data_type} for col in ts.columns]
        for table_name, ts in schema_map.items()
    }


@router.delete("/datasets/{table_name}")
async def delete_dataset(table_name: str):
    """Drop table from DB, remove from FAISS index, delete registry record."""
    await _ensure_dataset_table()

    # Drop from target DB
    try:
        await ingestion_engine.drop_table(table_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to drop table: {e}")

    # Remove from FAISS + schema cache
    schema_loader.get_cached().pop(table_name, None)
    schema_embedder.remove_table(table_name)

    # Remove from log DB
    async with _SessionLocal() as session:
        await session.execute(
            delete(UploadedDataset).where(UploadedDataset.table_name == table_name)
        )
        await session.commit()

    return {"status": "deleted", "table_name": table_name}
