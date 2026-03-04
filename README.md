# NL2SQL Agent

I built this project because I was tired of switching between a SQL client and whatever tool was generating queries for me. The idea is simple: you ask a question in plain English, and the system figures out which tables are relevant, generates the SQL, validates it, and runs it — all in one shot.

It connects to your PostgreSQL database, reads the schema automatically, and uses Google Gemini to handle the actual natural language understanding. There's a self-correction loop built in, so if the generated SQL has an error, it'll try to fix itself up to two times before giving up.

---

## What it can do

- **Talk to your database in plain English** — Type something like "show me the top 10 customers by revenue last quarter" and get back actual results.
- **Smart table selection** — It doesn't dump the entire schema into the prompt. It uses FAISS + sentence embeddings to find the most relevant tables for your specific question, keeping things accurate and fast.
- **Validates every query before running it** — There's a 4-stage check: keyword blocklist → multi-statement guard → AST parsing → SELECT-only enforcement. Nothing destructive ever reaches the database.
- **Self-healing on errors** — If the SQL fails, the agent feeds the error back to Gemini and asks for a corrected version. It retries up to twice.
- **File uploads** — You can upload a CSV or Parquet file and it'll infer the schema, load it into PostgreSQL, and let you query it right away.
- **Dashboard with history and metrics** — There's a React frontend showing query history, success rates, latency stats, and a transparency panel that shows you exactly what SQL was generated and why.

---

## Architecture

Here's roughly what happens when you send a question:

```
Your question
    → FAISS picks the most relevant tables from the schema
    → Gemini generates SQL with a confidence score
    → Validator checks it's safe (keyword + AST level)
    → If it fails, the correction loop retries with the error context
    → Executor runs it against PostgreSQL with a row limit + timeout
    → Results come back to the frontend
```

**Backend** is FastAPI + SQLAlchemy (async). **Frontend** is React (Vite). They talk over a REST API.

```
nl2sql-agent/
├── backend/
│   ├── main.py                 # FastAPI entry point, lifespan startup hooks
│   ├── config.py               # All settings live here (pydantic-settings)
│   ├── core/
│   │   ├── schema_loader.py    # Reads table/column definitions from Postgres
│   │   ├── embedder.py         # FAISS index for table selection
│   │   ├── llm_generator.py    # Calls Gemini, parses JSON output
│   │   ├── validator.py        # 4-stage SQL safety checks
│   │   ├── correction_loop.py  # Retry-with-error-context loop
│   │   ├── executor.py         # Runs SQL, enforces row limits + timeouts
│   │   └── ingestion.py        # Handles file upload → Postgres ingestion
│   ├── api/routes/
│   │   ├── query.py            # POST /api/query
│   │   ├── analytics.py        # GET /api/history, GET /api/metrics
│   │   └── upload.py           # POST /api/upload
│   ├── models/                 # Pydantic schemas
│   ├── monitoring/             # Metrics tracking, log DB
│   └── evaluation/             # 20-pair NL/SQL eval suite
├── frontend/
│   └── src/pages/
│       ├── QueryConsole.jsx    # Main query interface
│       ├── DataUpload.jsx      # File upload page
│       ├── Analytics.jsx       # Charts and stats
│       ├── History.jsx         # Past queries
│       └── Transparency.jsx    # How the SQL was made
├── docker/                     # Dockerfiles + init.sql for Postgres
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Getting started

### What you'll need

- Python 3.10+
- Node.js 18+ (for the frontend)
- PostgreSQL (or just use Docker)
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone and configure

```bash
git clone git@github.com:saihub404/nl2sql-agent.git
cd nl2sql-agent
cp .env.example .env
```

Open `.env` and fill in your Gemini API key and database URL. That's the minimum you need.

### 2. Run with Docker (easiest)

```bash
docker-compose up --build
```

This starts PostgreSQL, the FastAPI backend, and the React frontend together.

Once it's up:
- **Frontend**: http://localhost:5173
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 3. Run locally without Docker

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the backend
python -m backend.main

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

---

## Environment variables

Everything is configured through `.env`. Here's what each variable does:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Your Google Gemini API key (required) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Which Gemini model to use |
| `DATABASE_URL` | — | Your PostgreSQL connection string (asyncpg format) |
| `LOG_DATABASE_URL` | `sqlite:///./nl2sql_logs.db` | Where to store query history |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model for table selection |
| `TOP_K_TABLES` | `5` | How many tables to pass to Gemini per query |
| `QUERY_ROW_LIMIT` | `1000` | Max rows returned per query |
| `QUERY_TIMEOUT_SECONDS` | `10` | Query timeout before it's killed |
| `MAX_CORRECTION_RETRIES` | `2` | How many times it'll try to fix a bad query |
| `CONFIDENCE_THRESHOLD` | `0.6` | Minimum confidence score to accept a result |
| `LLM_TEMPERATURE` | `0.1` | Low temperature keeps SQL generation deterministic |

---

## API endpoints

If you want to use the backend directly (e.g., build your own frontend or integrate into a pipeline):

**POST /api/query**
```json
{ "query": "Which regions had the most orders last month?" }
```

**GET /api/metrics**
Returns success rate, average latency, correction rate, confidence distribution.

**GET /api/history?limit=50&offset=0**
Paginated list of past queries and their results.

**POST /api/upload**
Upload a CSV or Parquet file. The backend infers the schema and loads it into Postgres automatically.

**GET /health**
Returns DB connection status, number of tables loaded, and FAISS index status.

---

## Security

The system is designed to be safe to point at a real database, even one with sensitive data. Here's what's in place:

1. **Keyword blocklist** — `DROP`, `DELETE`, `UPDATE`, `ALTER`, `INSERT`, `EXEC` are rejected immediately via regex.
2. **AST enforcement** — Uses `sqlglot` to parse the query and verify it's a pure `SELECT` statement at the syntax tree level, not just the text level.
3. **Read-only database user** — The `DATABASE_URL` should point to a Postgres role with only `SELECT` privileges. Even if validation failed somehow, the DB would reject it.
4. **Row limit injection** — The executor rewrites the query's AST to enforce a `LIMIT` clause so you won't accidentally pull millions of rows.
5. **Query timeout** — `asyncio.wait_for` kills any query that runs longer than `QUERY_TIMEOUT_SECONDS`.

---

## Running tests

```bash
# Unit tests
pytest tests/ -v

# Evaluation suite (needs a live DB connection)
python -m backend.evaluation.eval_runner
```

The eval suite runs 20 NL/SQL pairs and measures exact match accuracy, correction rate, and average latency.

---

## Notes

- The FAISS index is built in memory at startup. It takes a few seconds on large schemas but nothing is persisted to disk.
- Uploaded files (CSV/Parquet) are ingested into Postgres as new tables. The FAISS index is rebuilt after each upload.
- Gemini's JSON response mode is used wherever possible to avoid having to parse freeform text.

---

If you run into issues or want to extend this (e.g., add support for more databases or a different LLM), feel free to open an issue or a PR. The architecture is intentionally modular so swapping components should be straightforward.
