"""
FastAPI application entry point.
Handles startup lifecycle: init log DB, load schema, build FAISS index.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.monitoring.metrics_tracker import init_log_db
from backend.core.schema_loader import schema_loader
from backend.core.embedder import schema_embedder
from backend.core.executor import query_executor
from backend.api.routes.query import router as query_router
from backend.api.routes.analytics import history_router, metrics_router
from backend.api.routes.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print("🚀 Starting NL2SQL Agent...")

    # 1. Init log database
    print("  ↳ Initializing log database...")
    await init_log_db()

    # 2. Load schema from target DB
    print("  ↳ Loading database schema...")
    try:
        schema = await schema_loader.load()
        print(f"  ↳ Loaded {len(schema)} tables from database.")

        # 3. Build FAISS embedding index
        print("  ↳ Building FAISS embedding index...")
        schema_embedder.build_index(schema)
        print(f"  ↳ FAISS index ready with {len(schema)} table embeddings.")
    except Exception as e:
        print(f"  ⚠️  Could not connect to target database: {e}")
        print("     API will start, but /query will fail until DB is available.")

    # 4. DB health check
    db_ok = await query_executor.health_check()
    status = "✅ connected" if db_ok else "⚠️  unreachable"
    print(f"  ↳ Target database: {status}")

    print("✅ NL2SQL Agent ready.\n")
    yield

    print("🛑 Shutting down...")


app = FastAPI(
    title="NL2SQL Agent API",
    description="Production-grade Natural Language to SQL agent with schema-aware reasoning and validation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow Streamlit on port 8501) ──────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────
app.include_router(query_router, prefix="/api", tags=["Query"])
app.include_router(history_router, prefix="/api", tags=["Analytics"])
app.include_router(metrics_router, prefix="/api", tags=["Analytics"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])


@app.get("/health", tags=["Health"])
async def health():
    db_ok = await query_executor.health_check()
    return {
        "status": "ok",
        "db_connected": db_ok,
        "schema_loaded": len(schema_loader.get_cached()),
        "faiss_ready": schema_embedder.is_ready(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
