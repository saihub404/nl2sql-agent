# NL2SQL Agent 🤖

A production-grade AI system that converts natural language questions into validated, optimized SQL — with schema-aware reasoning, self-correction loops, and a real-time analytics dashboard.

## ✨ Features

- **Schema Intelligence** — Dynamically loads DB schema, uses sentence-transformers + FAISS to select the top-K most relevant tables per query
- **LLM SQL Generation** — OpenAI GPT-4o or Gemini 1.5 Pro with few-shot examples, forced JSON output, and deterministic temperature
- **Validation Loop** — 4-stage validation (empty check → keyword blocklist → multi-statement guard → sqlglot AST parse) with automatic retry (max 2 attempts)
- **Security** — SELECT-only enforcement at both keyword and AST level, read-only DB user, row limit injection, query timeout
- **Analytics Dashboard** — Streamlit UI with Query Playground, Transparency Panel, Performance metrics, and Query History
- **Evaluation Suite** — 20 NL/SQL pairs measuring exact match, correction rate, and latency

## 🏗️ Architecture

```
NL Query → FAISS Schema Selector → LLM Generator → Validator → Correction Loop → Executor → Dashboard
```

## 🚀 Quick Start

### 1. Clone & configure

```bash
cd nl2sql-agent
cp .env.example .env
# Edit .env — set OPENAI_API_KEY and DATABASE_URL
```

### 2. Run with Docker Compose (recommended)

```bash
docker-compose up --build
```

- **Dashboard**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### 3. Run locally (development)

```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI backend
python -m backend.main

# Start Streamlit frontend (new terminal)
BACKEND_URL=http://localhost:8000 streamlit run frontend/app.py
```

## 📁 Project Structure

```
nl2sql-agent/
├── backend/
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Settings (pydantic-settings)
│   ├── api/routes/
│   │   ├── query.py              # POST /api/query
│   │   └── analytics.py         # GET /api/history, /api/metrics
│   ├── core/
│   │   ├── schema_loader.py      # DB schema introspection
│   │   ├── embedder.py           # FAISS table selector
│   │   ├── llm_generator.py      # OpenAI/Gemini SQL generation
│   │   ├── validator.py          # Syntax + security validation
│   │   ├── correction_loop.py    # Retry orchestration
│   │   └── executor.py           # Safe async SQL execution
│   ├── models/
│   │   ├── db_models.py          # SQLAlchemy ORM (query logs)
│   │   └── schemas.py            # Pydantic I/O schemas
│   ├── monitoring/
│   │   └── metrics_tracker.py    # Log persistence + metrics
│   └── evaluation/
│       ├── eval_dataset.json     # 20 NL/SQL test pairs
│       └── eval_runner.py        # Evaluation script
├── frontend/
│   └── app.py                    # Streamlit 4-tab dashboard
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── init.sql                  # Sample schema + read-only user
├── tests/
│   └── test_validator.py
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/ -v

# Evaluation suite (requires DB connection)
python -m backend.evaluation.eval_runner
```

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` or `gemini` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `DATABASE_URL` | — | Target PostgreSQL URL (asyncpg) |
| `LOG_DATABASE_URL` | SQLite | Log store URL |
| `TOP_K_TABLES` | `5` | Tables selected per query |
| `QUERY_ROW_LIMIT` | `1000` | Max rows returned |
| `QUERY_TIMEOUT_SECONDS` | `10` | Execution timeout |
| `MAX_CORRECTION_RETRIES` | `2` | Max LLM retry attempts |
| `CONFIDENCE_THRESHOLD` | `0.6` | Minimum accepted confidence |

## 🔒 Security Model

1. **Keyword blocklist** — Regex blocks DROP, DELETE, UPDATE, ALTER, etc.
2. **AST enforcement** — sqlglot parses and confirms SELECT-only AST
3. **Read-only DB user** — Enforced at PostgreSQL role level
4. **Row limit injection** — LIMIT injected via AST rewrite
5. **Query timeout** — `asyncio.wait_for` with configurable timeout

## 📊 API Reference

### `POST /api/query`
```json
{ "query": "Which customers placed orders last month?" }
```

### `GET /api/metrics`
Returns success rate, avg latency, correction rate, confidence distribution.

### `GET /api/history?limit=50&offset=0`
Returns paginated query history.

### `GET /health`
Returns DB connection status, schema table count, FAISS readiness.
