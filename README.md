# 🤖 NL2SQL Agent

Hey there! 👋 Welcome to the **NL2SQL Agent** repository. 

Ever wished you could just *talk* to your database instead of writing complex SQL queries? That's exactly what this project does! It's a production-grade AI system that takes your natural language questions and magically (well, programmatically) converts them into validated, optimized SQL. 

What's cool is that it actually understands your database schema, has built-in self-correction loops (so if the LLM makes a mistake, it tries to fix it!), and even comes with a slick real-time analytics dashboard. 📊

---

## ✨ Why this is awesome (Features)

- **🧠 Schema Intelligence**: It doesn't just guess; it dynamically loads your DB schema and uses `sentence-transformers` + FAISS to pick out the most relevant tables for your specific question.
- **🗣️ Smart LLM Generation**: Powered by OpenAI (`gpt-4o`) or Google Gemini (`gemini-1.5-pro`). It uses few-shot examples, enforces JSON output, and keeps temperatures deterministic for reliable results.
- **🛡️ Rock-Solid Validation Loop**: We don't just blindly run AI-generated SQL. There's a 4-stage validation process:
  1. Empty check
  2. Keyword blocklist
  3. Multi-statement guard
  4. AST parsing via `sqlglot`
  *Plus, it automatically retries up to 2 times if something looks fishy!*
- **🔒 Security First**: It enforces SELECT-only queries both at the keyword and AST level. We combine this with a read-only DB user, row limit injections, and strict query timeouts. Your DB is safe!
- **📈 Analytics Dashboard**: A beautiful Streamlit UI where you can play with queries, check the transparency panel to see *how* it arrived at the SQL, and view performance metrics and history.
- **🧪 Built-in Evaluation Suite**: Comes with a 20 NL/SQL pair dataset to measure exact match, correction rate, and latency.

---

## 🏗️ How it works (Architecture)

Here's the journey of a single question:

```text
🗣️ NL Query → 🔍 FAISS Schema Selector → 🧠 LLM Generator → 🛠️ Validator → 🔄 Correction Loop → ⚡ Executor → 📊 Dashboard
```

---

## 🚀 Let's get it running! (Quick Start)

### 1️⃣ Clone & Configure

First things first, grab the code and set up your environment variables:

```bash
git clone git@github.com:saihub404/nl2sql-agent.git
cd nl2sql-agent
cp .env.example .env
```
*(Don't forget to open up `.env` and drop in your `OPENAI_API_KEY` and `DATABASE_URL`!)*

### 2️⃣ Run with Docker Compose (Recommended 🐳)

The easiest way to get everything spinning is with Docker:

```bash
docker-compose up --build
```

Once that's running, you can hit up:
- 🎨 **Dashboard**: [http://localhost:8501](http://localhost:8501)
- 📖 **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 3️⃣ Run locally (If you prefer doing things by hand 🛠️)

```bash
# Install all the Python goodies
pip install -r requirements.txt

# Start the FastAPI backend
python -m backend.main

# In a new terminal, launch the Streamlit frontend
BACKEND_URL=http://localhost:8000 streamlit run frontend/app.py
```

---

## 📁 What's inside? (Project Structure)

Here's a quick tour of the codebase so you know where everything lives:

```text
nl2sql-agent/
├── backend/                   # 🧠 The brain of the operation
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Settings manager (pydantic-settings)
│   ├── api/routes/            # API Endpoints (query, analytics)
│   ├── core/                  # Core logic! 
│   │   ├── schema_loader.py   # Reads your DB schema
│   │   ├── embedder.py        # FAISS table selector magic
│   │   ├── llm_generator.py   # Talks to OpenAI/Gemini
│   │   ├── validator.py       # Keeps the SQL safe & sound
│   │   ├── correction_loop.py # "Let's try that SQL again"
│   │   └── executor.py        # Runs the final SQL safely
│   ├── models/                # DB Models and Pydantic schemas
│   ├── monitoring/            # Tracks metrics and logs
│   └── evaluation/            # Scripts to test how smart it is
├── frontend/                  # 🎨 The pretty face
│   └── app.py                 # Streamlit 4-tab dashboard
├── docker/                    # 🐳 Dockerfiles and DB initialization scripts
├── tests/                     # 🧪 Unit tests ensuring things don't break
├── docker-compose.yml         # Container orchestration
├── requirements.txt           # Python dependencies
└── .env.example               # Template for your secrets
```

---

## 🧪 Testing

Want to make sure everything works or run the evaluation suite?

```bash
# Run the unit tests
pytest tests/ -v

# Run the evaluation suite (Note: needs a DB connection!)
python -m backend.evaluation.eval_runner
```

---

## ⚙️ Configuration Knobs

You can tweak the agent's behavior by changing these in your `.env` file:

| Variable | Default | What does it do? 🤔 |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Choose between `openai` or `gemini` |
| `OPENAI_API_KEY` | — | Your secret OpenAI API key |
| `DATABASE_URL` | — | Where does your PostgreSQL live? (asyncpg format) |
| `LOG_DATABASE_URL` | `sqlite...` | Where to store query history and logs |
| `TOP_K_TABLES` | `5` | How many relevant tables to give the LLM |
| `QUERY_ROW_LIMIT` | `1000` | Max number of rows a query can return |
| `QUERY_TIMEOUT_SECONDS` | `10` | How long to wait before killing a slow query |
| `MAX_CORRECTION_RETRIES` | `2` | How many times the LLM can try fixing a bad query |
| `CONFIDENCE_THRESHOLD` | `0.6` | The minimum confidence score needed to accept a query |

---

## 🔒 Serious about Security

We don't play around with your data. Here is our 5-layer security model:

1. **🚫 Keyword Blocklist**: Sneaky words like `DROP`, `DELETE`, `UPDATE`, and `ALTER` are blocked via regex.
2. **🌳 AST Enforcement**: We use `sqlglot` to parse the Abstract Syntax Tree (AST) to guarantee it's strictly a `SELECT` query.
3. **👤 Read-Only DB User**: The system connects using a PostgreSQL role that physically cannot write to the database.
4. **🛑 Row Limit Injection**: We actively modify the query's AST to enforce a `LIMIT` so you don't accidentally dump 10 million rows.
5. **⏱️ Query Timeout**: If a query takes too long, `asyncio.wait_for` kills it without mercy.

---

## � Let's talk to the API (Reference)

If you're building on top of this or just want to use the endpoints directly:

### 📥 Ask a question `POST /api/query`
```json
{ "query": "Which customers placed orders last month?" }
```

### 📊 Get stats `GET /api/metrics`
Tells you the success rate, average latency, correction rate, and confidence distribution.

### 📜 See the past `GET /api/history?limit=50&offset=0`
Retrieves a paginated list of your query history.

### 🩺 Check the pulse `GET /health`
Verifies the DB connection status, how many tables are loaded, and if FAISS is ready to go.

---

### 🎉 Happy Querying!
If you find this project useful, feel free to give it a ⭐ or open a PR if you have improvements!
