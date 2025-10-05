# dashboard.py — AI SQL Analytics Dashboard (modern, clean, English-only)

import json
import time
import requests
import pandas as pd
import plotly.express as px
import streamlit as st



# top of dashboard.py
import streamlit as st

API_URL = st.secrets.get("API_URL", "http://127.0.0.1:8000/ask")  # fallback for local dev


# API_URL = "http://127.0.0.1:8000/ask"

# ---------- Page Setup ----------
st.set_page_config(page_title="AI SQL Analytics", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# Custom minimal styling
st.markdown("""
<style>
:root { --bg: #0e1117; --panel:#161a23; --text:#e6e6e6; --muted:#9aa0a6; }
html, body, [class*="css"]  { background-color: var(--bg) !important; color: var(--text) !important; }
.block-container { padding-top: 1.5rem; }
div[data-testid="stSidebar"] { background-color: var(--panel); }
.stTextInput>div>div>input, .stTextArea textarea { background:#1d2230; color:#fff; border-radius:12px; }
.stButton>button { background:#3a63f3; color:white; border-radius:10px; padding:0.6rem 1rem; border:0; }
.stSelectbox>div>div>div { color:#fff; }
hr { border: 1px solid #232a3a; }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar (history, examples) ----------
st.sidebar.title("🧠 Query History")
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {q, sql, rows}

with st.sidebar:
    if st.session_state.history:
        for i, h in enumerate(reversed(st.session_state.history[-10:]), start=1):
            with st.expander(f"{i}. {h['q'][:50]}"):
                st.code(h.get("sql") or "--", language="sql")
                st.text(f"Rows: {h.get('rows', 0)}")
    st.markdown("---")
    st.caption("💡 Examples")
    examples = [
        "Top 5 artists by number of albums (bar chart)",
        "Total invoice amount by country (pie chart)",
        "Monthly sales trend for 2010-2013 (line chart)",
        "Tracks per genre (bar chart)",
        "Top customers by total spend (bar chart)"
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}"):

            st.session_state["prefill"] = ex

# ---------- Header ----------
left, right = st.columns([0.75, 0.25])
with left:
    st.title("📊 AI SQL Analytics Dashboard")
    st.caption("Ask in plain English. Add chart hints like ‘bar chart’ or ‘line chart’.")
with right:
    chart_pref = st.selectbox(
        "Chart preference (optional)",
        ["Auto", "Bar", "Line", "Pie", "Area", "Table"],
        index=0
    )

# ---------- Input ----------
default_q = st.session_state.pop("prefill", "Top 5 artists by number of albums (bar chart)")
query = st.text_input("💬 Your question", value=default_q, key="nlq")

go = st.button("Run Query")

# ---------- Helper ----------
def infer_chart_type(q: str, override: str) -> str:
    if override and override != "Auto":
        return override.lower()
    ql = q.lower()
    if "bar" in ql: return "bar"
    if "line" in ql: return "line"
    if "pie" in ql: return "pie"
    if "area" in ql: return "area"
    return "table"

# ---------- Action ----------
if go and query.strip():
    placeholder = st.empty()
    with placeholder.container():
        with st.spinner("🧠 Thinking & fetching data... please wait"):
            try:
                resp = requests.post(API_URL, json={"query": query}, timeout=60)

                if resp.status_code != 200:
                    st.error(f"Server error: {resp.status_code}")
                else:
                    payload = resp.json()
                    raw = payload.get("answer", "[]")
                    sql = payload.get("sql", None)

                    # Show SQL
                    with st.expander("Generated SQL", expanded=False):
                        st.code(sql or "--", language="sql")

                    # Parse rows
                    try:
                        data = json.loads(raw) if isinstance(raw, str) else raw
                    except Exception:
                        data = []
                    df = pd.DataFrame(data)

                    if df.empty:
                        st.warning("No results found.")
                    else:
                        # ---- Draw Chart (Top) ----
                        ctype = infer_chart_type(query, chart_pref)
                        st.subheader("Visualization")

                        x_col, y_col = None, None
                        if len(df.columns) >= 2:
                            cat_candidates = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
                            num_candidates = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                            x_col = cat_candidates[0] if cat_candidates else df.columns[0]
                            y_col = num_candidates[0] if num_candidates else (df.columns[1] if len(df.columns) > 1 else None)

                        fig = None
                        if y_col is not None:
                            if ctype == "bar":
                                fig = px.bar(df, x=x_col, y=y_col, text=y_col)
                            elif ctype == "line":
                                fig = px.line(df, x=x_col, y=y_col, markers=True)
                            elif ctype == "pie":
                                fig = px.pie(df, names=x_col, values=y_col, hole=0.3)
                            elif ctype == "area":
                                fig = px.area(df, x=x_col, y=y_col)

                        if fig:
                            fig.update_layout(template="plotly_dark", height=520, margin=dict(l=10, r=10, t=40, b=10))
                            st.plotly_chart(fig, width='stretch')

                        # ---- Table (Below) ----
                        st.markdown("---")
                        st.subheader("Data Table")
                        st.dataframe(df, width='stretch')

                        # ---- Download ----
                        st.markdown("### ⬇️ Download Results")
                        st.download_button("Download CSV", data=df.to_csv(index=False), file_name="result.csv", mime="text/csv")

                        # Save to history
                        st.session_state.history.append({
                            "q": query, "sql": sql, "rows": len(df)
                        })

                        st.success("✅ Query completed successfully!")

            except requests.exceptions.ConnectionError:
                st.error("⚠️ Backend not running on port 8000. Please start FastAPI with `uvicorn main:app --reload`.")
            except requests.exceptions.Timeout:
                st.error("⚠️ Request timed out. Try a simpler question or check the server.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    # Footer
    st.markdown("---")
    st.caption("⚙️ Built by Umesh Kumawat | Powered by OpenAI GPT-4o-mini + FastAPI + Streamlit")
