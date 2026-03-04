"""
NL2SQL Intelligence — Premium SaaS Dashboard
Streamlit frontend with full SaaS UI/UX: dark glassmorphism,
animated sidebar, metric cards, query console, and history.
"""
import json
import os
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="NL2SQL Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# PREMIUM SaaS THEME
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    color: #e2e8f0;
}

/* ── App background ── */
.stApp {
    background: linear-gradient(135deg, #0a0d1a 0%, #0d1117 50%, #070b14 100%);
    min-height: 100vh;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1420 0%, #0b0f1a 100%) !important;
    border-right: 1px solid rgba(99, 120, 255, 0.12) !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ── Sidebar radio items ── */
div[data-testid="stRadio"] > label { display: none; }
div[data-testid="stRadio"] > div {
    gap: 2px !important;
    display: flex !important;
    flex-direction: column !important;
}
div[data-testid="stRadio"] > div > label {
    background: transparent !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #94a3b8 !important;
    border: none !important;
}
div[data-testid="stRadio"] > div > label:hover {
    background: rgba(99,120,255,0.08) !important;
    color: #c7d2fe !important;
}
div[data-testid="stRadio"] > div > label[data-baseweb="radio"] {
    background: rgba(99,120,255,0.15) !important;
    color: #818cf8 !important;
}

/* ── Metric cards ── */
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 14px !important;
    padding: 1.1rem 1.2rem !important;
    backdrop-filter: blur(16px) !important;
    transition: border-color 0.25s ease !important;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(99,120,255,0.25) !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    color: #64748b !important;
}
div[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #e2e8f0 !important;
    letter-spacing: -0.02em !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.01em !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important;
    background: linear-gradient(135deg, #7c7ff0 0%, #9d6ef5 100%) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Text area ── */
.stTextArea textarea {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.92rem !important;
    padding: 14px !important;
    transition: border-color 0.2s ease !important;
    resize: none !important;
}
.stTextArea textarea:focus {
    border-color: rgba(99,102,241,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.05) !important; margin: 1.5rem 0 !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #6366f1 !important; }

/* ── Alerts ── */
.stAlert { border-radius: 10px !important; border-width: 1px !important; }

/* ── Selectbox / slider ── */
.stSelectbox > div > div,
.stSlider > div {
    background: rgba(255,255,255,0.03) !important;
    border-color: rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
}

/* ── Code blocks ── */
.stCodeBlock { border-radius: 10px !important; }
code { font-family: 'JetBrains Mono', 'Courier New', monospace !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def api_post(path, **kwargs):
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", timeout=60, **kwargs)
        return r.json() if r.status_code == 200 else None, r.status_code
    except httpx.ConnectError:
        return None, 0

def api_get(path, **kwargs):
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=15, **kwargs)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def badge(text, color):
    return (
        f'<span style="background:{color}22;color:{color};'
        f'border:1px solid {color}44;border-radius:20px;'
        f'padding:3px 12px;font-size:0.73rem;font-weight:600;'
        f'letter-spacing:0.03em;">{text}</span>'
    )

def status_badge(passed):
    return badge("● PASSED", "#22c55e") if passed else badge("● FAILED", "#ef4444")

def plotly_config():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter"),
        margin=dict(l=10, r=10, t=30, b=10),
    )


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    # Logo + Brand
    st.markdown("""
    <div style="
        padding: 1.4rem 1.2rem 1rem;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 0.8rem;
    ">
        <div style="
            display:flex; align-items:center; gap:10px;
        ">
            <div style="
                width:36px;height:36px;border-radius:10px;
                background:linear-gradient(135deg,#6366f1,#8b5cf6);
                display:flex;align-items:center;justify-content:center;
                font-size:1.1rem;box-shadow:0 4px 12px rgba(99,102,241,0.35);
            ">⚡</div>
            <div>
                <div style="font-weight:700;font-size:0.95rem;color:#e2e8f0;letter-spacing:-0.01em;">NL2SQL</div>
                <div style="font-size:0.7rem;color:#4b5563;font-weight:500;letter-spacing:0.05em;">INTELLIGENCE</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="padding:0 0.5rem;">', unsafe_allow_html=True)
    st.markdown('<p style="color:#374151;font-size:0.7rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;padding-left:8px;margin-bottom:6px;">MAIN MENU</p>', unsafe_allow_html=True)

    page = st.radio(
        label="nav",
        label_visibility="collapsed",
        options=[
            "⚡  Query Console",
            "🔬  Transparency",
            "📊  Analytics",
            "📜  History",
            "📂  Data Upload",
        ],
        key="nav_radio",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Health badge in sidebar footer
    st.markdown("<br>" * 6, unsafe_allow_html=True)
    health = api_get("/health")
    if health:
        db_status = "🟢 Connected" if health.get("db_connected") else "🔴 Disconnected"
        faiss_status = "🟢 Ready" if health.get("faiss_ready") else "🟡 Not Ready"
        tables = health.get("schema_loaded", 0)
        st.markdown(f"""
        <div style="
            margin: 0 0.5rem;
            background:rgba(255,255,255,0.02);
            border:1px solid rgba(255,255,255,0.05);
            border-radius:10px;padding:12px 14px;
        ">
            <p style="font-size:0.7rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">SYSTEM</p>
            <div style="font-size:0.78rem;color:#6b7280;line-height:1.7;">
                <div>{db_status}</div>
                <div>{faiss_status}</div>
                <div>📋 {tables} tables indexed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

page_name = page.split("  ")[1]


# ══════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════

PAGE_META = {
    "Query Console":  ("Query Console",  "Ask any business question in plain English"),
    "Transparency":   ("Transparency",   "Inspect LLM reasoning, schema selection, and correction steps"),
    "Analytics":      ("Analytics",      "Real-time performance and accuracy metrics"),
    "History":        ("History",        "Audit log of all past queries"),
    "Data Upload":    ("Data Upload",    "Upload CSV / Parquet files and query them instantly with AI"),
}
title, subtitle = PAGE_META[page_name]

st.markdown(f"""
<div style="
    display:flex; align-items:flex-start; justify-content:space-between;
    padding: 1.8rem 0 1.4rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 1.8rem;
">
    <div>
        <h1 style="
            font-size:1.7rem; font-weight:800; color:#e2e8f0;
            letter-spacing:-0.03em; margin:0 0 4px;
        ">{title}</h1>
        <p style="font-size:0.83rem;color:#4b5563;margin:0;font-weight:400;">{subtitle}</p>
    </div>
    <div style="
        background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);
        border-radius:8px;padding:6px 14px;font-size:0.75rem;
        color:#818cf8;font-weight:600;letter-spacing:0.03em;
        white-space:nowrap;margin-top:6px;
    ">v1.0  ·  Gemini Powered</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE: QUERY CONSOLE
# ══════════════════════════════════════════════════════════════
if page_name == "Query Console":

    # Session state
    if "last_response" not in st.session_state:
        st.session_state.last_response = None

    # Starter prompts
    STARTERS = [
        "Top 5 customers by revenue",
        "Orders placed last month",
        "Out-of-stock products",
        "Average order value by region",
        "Employees per department",
    ]

    st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">QUICK PROMPTS</p>', unsafe_allow_html=True)
    cols_s = st.columns(len(STARTERS))
    chosen_prompt = None
    for i, s in enumerate(STARTERS):
        with cols_s[i]:
            if st.button(s, key=f"starter_{i}", use_container_width=True):
                chosen_prompt = s

    st.markdown("<br>", unsafe_allow_html=True)

    # Input area
    col_input, col_action = st.columns([5, 1])
    with col_input:
        nl_query = st.text_area(
            label="nl_input",
            label_visibility="collapsed",
            placeholder="Ask a business question in plain English — e.g. 'What are the top 10 customers by total revenue this year?'",
            height=100,
            key="nl_input",
            value=chosen_prompt or st.session_state.get("last_query", ""),
        )

    with col_action:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("⚡ Run", use_container_width=True, type="primary")
        st.markdown('<p style="font-size:0.68rem;color:#374151;text-align:center;margin-top:6px;">Shift+Enter to submit</p>', unsafe_allow_html=True)

    if chosen_prompt:
        st.session_state["last_query"] = chosen_prompt

    # Execute
    if run and nl_query.strip():
        with st.spinner("🧠 Reasoning about your schema and generating SQL…"):
            data, status = api_post("/api/query", json={"query": nl_query})
            if status == 200 and data:
                st.session_state.last_response = data
            elif status == 422:
                st.error(f"⚠️ Query rejected — confidence too low or validation failed.")
                st.session_state.last_response = None
            else:
                st.error("❌ Cannot reach backend. Is the service running?")
                st.session_state.last_response = None

    data = st.session_state.last_response
    if data:
        st.markdown("<br>", unsafe_allow_html=True)

        # ── KPI strip ──────────────────────────────────────────
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Validation", "✓ Passed" if data["validation_status"] == "passed" else "✗ Failed")
        k2.metric("Confidence", f"{data['confidence_score']:.0%}")
        k3.metric("Latency", f"{data['latency_ms']:.0f} ms")
        k4.metric("Corrections", data["correction_attempts"])
        k5.metric("Rows Returned", data["results"]["row_count"] if data.get("results") else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── SQL + Results split ────────────────────────────────
        col_sql, col_res = st.columns([1, 1], gap="large")

        with col_sql:
            st.markdown(f"""
            <div style="
                display:flex;align-items:center;justify-content:space-between;
                margin-bottom:8px;
            ">
                <p style="font-size:0.75rem;color:#374151;font-weight:600;
                letter-spacing:0.07em;text-transform:uppercase;margin:0;">
                GENERATED SQL</p>
                {status_badge(data['validation_status'] == 'passed')}
            </div>
            """, unsafe_allow_html=True)
            st.code(data["final_sql"], language="sql")

            # Tables used chips
            if data.get("tables_used"):
                chips = " ".join([
                    f'<span style="background:rgba(99,102,241,0.1);color:#818cf8;'
                    f'border:1px solid rgba(99,102,241,0.2);border-radius:6px;'
                    f'padding:2px 10px;font-size:0.72rem;font-weight:600;">{t}</span>'
                    for t in data["tables_used"]
                ])
                st.markdown(f'<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">{chips}</div>', unsafe_allow_html=True)

        with col_res:
            if data["execution_success"] and data.get("results"):
                results = data["results"]
                st.markdown(f'<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">RESULTS — {results["row_count"]} rows</p>', unsafe_allow_html=True)
                df = pd.DataFrame(results["rows"], columns=results["columns"])
                st.dataframe(df, use_container_width=True, height=240)

                # CSV download
                st.download_button(
                    label="⬇ Download CSV",
                    data=df.to_csv(index=False),
                    file_name="nl2sql_result.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            elif not data["execution_success"]:
                st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">EXECUTION ERROR</p>', unsafe_allow_html=True)
                st.error(data.get("execution_error", "Unknown error"))

        # ── Auto visualization ─────────────────────────────────
        if data["execution_success"] and data.get("results"):
            df = pd.DataFrame(data["results"]["rows"], columns=data["results"]["columns"])
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            cat_cols = df.select_dtypes(exclude="number").columns.tolist()

            if numeric_cols and cat_cols and len(df) > 1:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">AUTO VISUALIZATION</p>', unsafe_allow_html=True)

                # Choose chart type based on shape
                if len(df) <= 6:
                    fig = px.pie(df, names=cat_cols[0], values=numeric_cols[0],
                                 color_discrete_sequence=px.colors.sequential.Purples_r)
                elif any(c in cat_cols[0].lower() for c in ["date", "month", "year", "week", "day"]):
                    fig = px.line(df, x=cat_cols[0], y=numeric_cols[0],
                                  color_discrete_sequence=["#6366f1"])
                    fig.update_traces(mode="lines+markers")
                else:
                    fig = px.bar(
                        df.sort_values(numeric_cols[0], ascending=False).head(20),
                        x=cat_cols[0], y=numeric_cols[0],
                        color=numeric_cols[0],
                        color_continuous_scale="Purples",
                    )
                    fig.update_coloraxes(showscale=False)

                fig.update_layout(**plotly_config())
                fig.update_xaxes(showgrid=False, tickfont=dict(size=11))
                fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", tickfont=dict(size=11))
                st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# PAGE: TRANSPARENCY
# ══════════════════════════════════════════════════════════════
elif page_name == "Transparency":
    data = st.session_state.get("last_response")
    if not data:
        st.markdown("""
        <div style="
            text-align:center;padding:80px 40px;
            background:rgba(255,255,255,0.02);
            border:1px dashed rgba(255,255,255,0.07);
            border-radius:16px;color:#374151;
        ">
            <div style="font-size:2.5rem;margin-bottom:12px;">🔬</div>
            <div style="font-weight:600;font-size:1rem;color:#6b7280;">No query ran yet</div>
            <div style="font-size:0.82rem;margin-top:6px;">Run a query in the Query Console first</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">RAW LLM OUTPUT</p>', unsafe_allow_html=True)
            try:
                raw = json.loads(data.get("raw_llm_output", "{}"))
                st.json(raw)
            except Exception:
                st.code(data.get("raw_llm_output", "N/A"))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">INITIAL SQL</p>', unsafe_allow_html=True)
            st.code(data["generated_sql"], language="sql")

            if data["generated_sql"] != data["final_sql"]:
                st.markdown('<p style="font-size:0.75rem;color:#f97316;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">🔧 CORRECTED SQL</p>', unsafe_allow_html=True)
                st.code(data["final_sql"], language="sql")

        with col_b:
            st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">SCHEMA SIMILARITY SCORES</p>', unsafe_allow_html=True)
            scores = data.get("similarity_scores", {})
            if scores:
                score_df = pd.DataFrame(
                    [(t, round(s * 100, 1)) for t, s in sorted(scores.items(), key=lambda x: -x[1])],
                    columns=["Table", "Score (%)"],
                )
                fig = px.bar(
                    score_df, x="Score (%)", y="Table", orientation="h",
                    color="Score (%)", color_continuous_scale=["#1e1b4b", "#6366f1", "#a5b4fc"],
                )
                fig.update_coloraxes(showscale=False)
                fig.update_layout(**plotly_config(), height=250)
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(showgrid=False, autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

            st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">PIPELINE STATS</p>', unsafe_allow_html=True)
            rows = [
                ("NL Query", data["nl_query"]),
                ("Confidence", f"{data['confidence_score']:.2f}"),
                ("Correction Attempts", str(data["correction_attempts"])),
                ("Correction Triggered", "Yes" if data["correction_attempts"] > 0 else "No"),
                ("Tables Used", ", ".join(data.get("tables_used", []))),
                ("Latency", f"{data['latency_ms']:.1f} ms"),
            ]
            for label, value in rows:
                st.markdown(f"""
                <div style="
                    display:flex;justify-content:space-between;align-items:flex-start;
                    padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.04);
                    font-size:0.82rem;
                ">
                    <span style="color:#4b5563;font-weight:500;">{label}</span>
                    <span style="color:#e2e8f0;font-weight:500;text-align:right;max-width:55%;word-break:break-all;">{value}</span>
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE: ANALYTICS
# ══════════════════════════════════════════════════════════════
elif page_name == "Analytics":
    m = api_get("/api/metrics")

    if not m:
        st.warning("⚠️ Could not reach backend metrics endpoint.")
    else:
        # KPI row
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Queries", f"{m['total_queries']:,}")
        k2.metric("Success Rate", f"{m['success_rate_pct']}%")
        k3.metric("Correction Rate", f"{m['correction_loop_rate_pct']}%")
        k4.metric("Avg Latency", f"{m['avg_latency_ms']:.0f} ms")
        k5.metric("Avg Confidence", f"{m['avg_confidence_score']:.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        col_pie, col_dist = st.columns(2, gap="large")

        with col_pie:
            st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">FAILURE BREAKDOWN</p>', unsafe_allow_html=True)
            fb = m["failure_breakdown"]
            vals = [fb["validation_failures"], fb["execution_failures"], fb["low_confidence_rejections"]]
            if sum(vals) > 0:
                fig_pie = go.Figure(go.Pie(
                    labels=["Validation", "Execution", "Low Confidence"],
                    values=vals,
                    hole=0.55,
                    marker_colors=["#6366f1", "#8b5cf6", "#a78bfa"],
                    textfont_size=11,
                ))
                fig_pie.update_traces(hovertemplate="%{label}: %{value}<extra></extra>")
                fig_pie.update_layout(**plotly_config(), height=260, showlegend=True,
                                       legend=dict(orientation="v", x=1, y=0.5, font=dict(size=11)))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.markdown("""
                <div style="
                    text-align:center;padding:50px;
                    background:rgba(34,197,94,0.05);
                    border:1px solid rgba(34,197,94,0.15);
                    border-radius:12px;
                ">
                    <div style="font-size:1.8rem;margin-bottom:8px;">🎉</div>
                    <div style="color:#22c55e;font-weight:600;">Zero failures recorded</div>
                </div>
                """, unsafe_allow_html=True)

        with col_dist:
            st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">CONFIDENCE DISTRIBUTION</p>', unsafe_allow_html=True)
            cd = m.get("confidence_distribution", [])
            if cd:
                df_cd = pd.DataFrame(cd)
                fig_bar = px.bar(
                    df_cd, x="bucket", y="count",
                    color="count",
                    color_continuous_scale=["#1e1b4b", "#4f46e5", "#a5b4fc"],
                )
                fig_bar.update_coloraxes(showscale=False)
                fig_bar.update_layout(**plotly_config(), height=260)
                fig_bar.update_xaxes(showgrid=False)
                fig_bar.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Run some queries to populate the confidence distribution.")


# ══════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ══════════════════════════════════════════════════════════════
elif page_name == "History":
    col_ctrl, col_search = st.columns([1, 3])
    with col_ctrl:
        page_size = st.selectbox("Rows", [10, 25, 50, 100], index=1, label_visibility="collapsed")
    with col_search:
        st.markdown('<p style="color:#4b5563;font-size:0.8rem;padding-top:8px;">Showing most recent queries first</p>', unsafe_allow_html=True)

    hist = api_get("/api/history", params={"limit": page_size, "offset": 0})

    if not hist:
        st.warning("⚠️ Could not load history.")
    elif not hist["items"]:
        st.info("No queries yet — try the Query Console!")
    else:
        total = hist["total"]
        items = hist["items"]
        st.caption(f"{total} total queries · showing latest {len(items)}")

        rows = []
        for item in items:
            rows.append({
                "Time": item["timestamp"][:19].replace("T", " "),
                "Query": item["nl_query"][:90] + ("…" if len(item["nl_query"]) > 90 else ""),
                "Status": "✅ Success" if item["execution_success"] else "❌ Failed",
                "Confidence": f"{item['confidence_score']:.0%}" if item.get("confidence_score") else "—",
                "Corrections": item["correction_attempts"],
                "Latency ms": f"{item['latency_ms']:.0f}" if item.get("latency_ms") else "—",
                "Rows": item.get("row_count") or "—",
            })

        df_hist = pd.DataFrame(rows)
        st.dataframe(
            df_hist,
            use_container_width=True,
            height=min(60 + len(df_hist) * 38, 600),
            column_config={
                "Status": st.column_config.TextColumn(width="small"),
                "Confidence": st.column_config.TextColumn(width="small"),
                "Latency ms": st.column_config.TextColumn(width="small"),
                "Rows": st.column_config.TextColumn(width="small"),
            }
        )

        st.download_button(
            "⬇ Export History CSV",
            data=df_hist.to_csv(index=False),
            file_name="nl2sql_history.csv",
            mime="text/csv",
        )


# ══════════════════════════════════════════════════════════════
# PAGE: DATA UPLOAD
# ══════════════════════════════════════════════════════════════
elif page_name == "Data Upload":
    import time

    # ── Section: Upload a new file ─────────────────────────────
    st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:16px;">UPLOAD NEW DATASET</p>', unsafe_allow_html=True)

    col_up, col_hints = st.columns([3, 1], gap="large")

    with col_up:
        uploaded_file = st.file_uploader(
            label="Upload file",
            label_visibility="collapsed",
            type=["csv", "tsv", "parquet"],
            help="CSV, TSV, or Parquet files up to 2 GB. For 1M+ rows use Parquet for best performance.",
        )

    with col_hints:
        st.markdown("""
        <div style="
            background:rgba(99,102,241,0.05);
            border:1px solid rgba(99,102,241,0.15);
            border-radius:12px;padding:14px 16px;
            font-size:0.78rem;color:#64748b;line-height:1.8;
        ">
            <b style="color:#818cf8;">Supported formats</b><br>
            📄 CSV / TSV<br>
            🗜 Parquet<br><br>
            <b style="color:#818cf8;">Limits</b><br>
            Max size: 2 GB<br>
            Target throughput: ~300K rows/s<br><br>
            <b style="color:#818cf8;">Tip</b><br>
            Use Parquet for 1M+ rows — 5-10× faster than CSV.
        </div>
        """, unsafe_allow_html=True)

    if uploaded_file is not None:
        st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin:20px 0 10px;">INFERRED SCHEMA PREVIEW</p>', unsafe_allow_html=True)

        with st.spinner("Analyzing file structure…"):
            try:
                response = httpx.post(
                    f"{BACKEND_URL}/api/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/octet-stream")},
                    timeout=120,
                )
                if response.status_code != 200:
                    st.error(f"Upload failed: {response.text}")
                    upload_data = None
                else:
                    upload_data = response.json()
                    st.session_state["upload_data"] = upload_data
            except Exception as e:
                st.error(f"Could not reach backend: {e}")
                upload_data = None

        if upload_data := st.session_state.get("upload_data"):
            col_info1, col_info2, col_info3 = st.columns(3)
            col_info1.metric("Table Name", upload_data["table_name"])
            col_info2.metric("File Size", f"{upload_data['file_size_mb']:.1f} MB")
            col_info3.metric("Sample Rows", f"{upload_data['row_estimate']:,}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Schema preview table
            cols_data = upload_data["inferred_columns"]
            schema_rows = []
            for c in cols_data:
                warning = "⚠️ May need override" if c["date_detected"] else ""
                schema_rows.append({
                    "Column": c["original_name"],
                    "→ Sanitized": c["name"],
                    "PostgreSQL Type": c["pg_type"],
                    "Nullable": "✓" if c["nullable"] else "✗",
                    "Note": "📅 Date detected" if c["date_detected"] else "",
                })
            st.dataframe(
                pd.DataFrame(schema_rows),
                use_container_width=True,
                height=min(60 + len(schema_rows) * 38, 400),
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # Progress tracking
            dataset_id = upload_data["dataset_id"]
            progress_placeholder = st.empty()
            status_placeholder = st.empty()

            # Poll until done
            poll_limit = 300  # max 300 polls (~5 min)
            for _ in range(poll_limit):
                prog = api_get(f"/api/upload/progress/{dataset_id}")
                if not prog:
                    status_placeholder.error("Lost contact with backend during ingestion.")
                    break

                pct = prog["pct"]
                rows_done = prog["rows_ingested"]
                status = prog["status"]

                with progress_placeholder.container():
                    st.progress(pct / 100, text=f"{pct:.1f}% — {rows_done:,} rows ingested")
                    if status == "ready":
                        total_rows = prog["row_count"] or rows_done
                        st.success(f"✅ Ingestion complete! **{total_rows:,} rows** loaded into `{upload_data['table_name']}`. Switch to **Query Console** to start querying.")
                        # Clear upload session so the widget resets
                        st.session_state.pop("upload_data", None)
                        break
                    elif status == "error":
                        st.error(f"Ingestion failed: {prog.get('error_message', 'Unknown error')}")
                        st.session_state.pop("upload_data", None)
                        break

                time.sleep(1)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.75rem;color:#374151;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:12px;">UPLOADED DATASETS</p>', unsafe_allow_html=True)

    datasets_resp = api_get("/api/datasets")
    if not datasets_resp or not datasets_resp["datasets"]:
        st.markdown("""
        <div style="
            text-align:center;padding:40px;
            background:rgba(255,255,255,0.02);
            border:1px dashed rgba(255,255,255,0.06);
            border-radius:12px;color:#374151;
        ">
            <div style="font-size:2rem;margin-bottom:8px;">📂</div>
            <div style="font-weight:600;color:#4b5563;">No datasets uploaded yet</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for ds in datasets_resp["datasets"]:
            status_color = {"ready": "#22c55e", "ingesting": "#f59e0b", "error": "#ef4444"}.get(ds["status"], "#94a3b8")
            status_icon  = {"ready": "✅", "ingesting": "⏳", "error": "❌"}.get(ds["status"], "○")
            row_display = f"{ds['row_count']:,}" if ds.get("row_count") else f"{ds['rows_ingested']:,} ingested…"

            col_ds, col_del = st.columns([6, 1])
            with col_ds:
                st.markdown(f"""
                <div style="
                    background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
                    border-radius:12px;padding:14px 18px;margin-bottom:10px;
                    display:flex;align-items:center;justify-content:space-between;
                ">
                    <div>
                        <div style="font-weight:600;font-size:0.88rem;color:#e2e8f0;margin-bottom:3px;">
                            {status_icon} {ds['table_name']}
                        </div>
                        <div style="font-size:0.76rem;color:#4b5563;">
                            {ds['original_filename']} · {ds.get('file_size_mb', 0):.1f} MB · {row_display} rows · {ds.get('column_count', '?')} cols
                        </div>
                    </div>
                    <span style="
                        background:{status_color}22;color:{status_color};
                        border:1px solid {status_color}44;border-radius:6px;
                        padding:2px 10px;font-size:0.72rem;font-weight:600;
                    ">{ds['status'].upper()}</span>
                </div>
                """, unsafe_allow_html=True)

            with col_del:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑", key=f"del_{ds['table_name']}", help=f"Delete {ds['table_name']}"):
                    del_resp = httpx.delete(f"{BACKEND_URL}/api/datasets/{ds['table_name']}", timeout=30)
                    if del_resp.status_code == 200:
                        st.success(f"Deleted `{ds['table_name']}`")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {del_resp.text}")