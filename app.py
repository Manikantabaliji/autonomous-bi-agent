import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from main import AutonomousBIAgent
from src.dashboard_generator import headline


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="BI Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- Global ---------- */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* ---------- Hero header ---------- */
    .hero {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #a855f7 100%);
        border-radius: 20px;
        padding: 2.2rem 2.5rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 30px rgba(79, 70, 229, 0.25);
    }

    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 0.4rem;
        letter-spacing: -0.5px;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        color: rgba(255, 255, 255, 0.9);
        line-height: 1.5;
        max-width: 700px;
    }

    .hero-badges {
        margin-top: 1rem;
    }

    .hero-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.18);
        color: #ffffff;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* ---------- Section titles ---------- */
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 1.6rem;
        margin-bottom: 0.9rem;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ---------- Cards ---------- */
    .card {
        background: #ffffff;
        border: 1px solid #eef0f3;
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        margin-bottom: 1.2rem;
    }

    /* The summary is markdown, so it goes into a keyed
       Streamlit container rather than a raw <div>: markdown
       nested inside raw HTML is not parsed, which would leave
       its headings and tables as literal text on screen. */
    .st-key-summary_card {
        background: linear-gradient(135deg, #f5f7ff 0%, #f0f4ff 100%);
        border: 1px solid #e0e7ff;
        border-radius: 16px;
        padding: 1.5rem 1.8rem;
    }

    .st-key-summary_card p,
    .st-key-summary_card li {
        font-size: 1.02rem;
        line-height: 1.65;
        color: #1e293b;
    }

    .st-key-summary_card h1,
    .st-key-summary_card h2,
    .st-key-summary_card h3,
    .st-key-summary_card h4 {
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #4338ca !important;
        margin: 1.2rem 0 0.4rem 0 !important;
    }

    .st-key-summary_card table {
        font-size: 0.92rem;
        border-collapse: collapse;
        margin: 0.4rem 0 0.8rem 0;
    }

    .st-key-summary_card th {
        text-align: left;
        font-size: 0.75rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #6b7280;
        border-bottom: 1px solid #c7d2fe;
        padding: 0.35rem 1.2rem 0.35rem 0;
        background: transparent;
    }

    .st-key-summary_card td {
        padding: 0.38rem 1.2rem 0.38rem 0;
        border-bottom: 1px solid #e0e7ff;
        color: #1e293b;
        font-variant-numeric: tabular-nums;
        background: transparent;
    }

    /* Chart and table cards - same treatment, for the same
       reason: a raw <div> cannot wrap a Streamlit element. */
    .st-key-chart_card,
    .st-key-table_card {
        background: #ffffff;
        border: 1px solid #eef0f3;
        border-radius: 16px;
        padding: 1.1rem 1.3rem;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        margin-bottom: 1.2rem;
    }

    /* ---------- Single-number answers ---------- */
    .figure-value {
        font-size: 3.4rem;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -1px;
        background: linear-gradient(135deg, #4f46e5 0%, #a855f7 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: #4f46e5;
    }

    .figure-label {
        margin-top: 0.5rem;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: #6b7280;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: #fafaff;
        border-right: 1px solid #eef0f3;
    }

    .flow-step {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.35rem;
        font-size: 0.85rem;
        font-weight: 600;
        color: #4338ca;
        text-align: center;
    }

    .flow-arrow {
        text-align: center;
        color: #a5b4fc;
        font-size: 1rem;
        margin: -0.15rem 0;
    }

    /* Example chips, made clickable so a question can be run
       in one tap instead of retyped. */
    section[data-testid="stSidebar"] .stButton button {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        background: #ffffff;
        border: 1px solid #e0e7ff;
        border-radius: 10px;
        padding: 0.5rem 0.7rem;
        font-size: 0.82rem;
        font-weight: 500;
        color: #4338ca;
        line-height: 1.35;
        min-height: 0;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        background: #f5f7ff;
        border-color: #a5b4fc;
        color: #3730a3;
    }

    /* The label is centred by flex wrappers inside the button,
       not by text-align, so the alignment is set on those. */
    section[data-testid="stSidebar"] .stButton button > div,
    section[data-testid="stSidebar"] .stButton button > div > span {
        justify-content: flex-start !important;
        text-align: left !important;
        width: 100% !important;
    }

    /* ---------- Pipeline boxes ---------- */
    .pipeline-box {
        padding: 1.1rem 0.6rem;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
        text-align: center;
        margin-bottom: 0.6rem;
        font-size: 1.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        transition: transform 0.15s ease;
    }

    .pipeline-box:hover {
        transform: translateY(-2px);
    }

    .pipeline-box b {
        display: block;
        font-size: 0.75rem;
        margin-top: 0.35rem;
        color: #374151;
        font-weight: 600;
    }

    /* ---------- Misc ---------- */
    .small-text {
        font-size: 0.85rem;
        color: #6b7280;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #eef0f3;
        border-radius: 14px;
        padding: 0.8rem 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }

    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.55rem 1.6rem;
    }

    div[data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid #eef0f3;
    }

    [data-testid="stAppDeployButton"] {
        display: none !important;
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CONSTANTS
# ============================================================

FLOW_STEPS = [
    "💬 Natural Language",
    "🔎 Hybrid RAG",
    "⚡ Groq SQL Generation",
    "✅ SQL Validation",
    "🗄️ SQLite Analysis",
    "📊 Visualization",
    "💡 Executive Summary",
]

EXAMPLE_QUESTIONS = [
    "How many customers are there?",
    "What are the top 10 products by total sales?",
    "Which employees handled the most orders?",
    "What are the top 5 customers by total sales?",
    "Which countries have the most customers?",
]

PIPELINE_BOXES = [
    ("🧑‍💼", "Question"),
    ("🔎", "RAG"),
    ("🤖", "Groq"),
    ("🗄️", "SQLite"),
    ("📊", "Dashboard"),
    ("💡", "Insight"),
]


# ============================================================
# SESSION STATE
#
# The analysis is kept here so that a later interaction -
# downloading the CSV, opening the SQL expander - re-renders
# the last result instead of clearing the screen.
# ============================================================

if "question" not in st.session_state:
    st.session_state.question = ""

if "result" not in st.session_state:
    st.session_state.result = None

if "pending" not in st.session_state:
    st.session_state.pending = False


def queue_run():
    """Pressing Enter in the input should analyze."""

    st.session_state.pending = True


def queue_example(text):
    """A sidebar example behaves exactly like typing it."""

    st.session_state.question = text
    st.session_state.pending = True


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">📊 Autonomous BI Agent</div>
        <div class="hero-subtitle">
            Ask business questions in natural language and let the AI
            generate SQL, analyze the Northwind database, create
            visualizations, and deliver executive-ready insights
            end to end, automatically.
        </div>
        <div class="hero-badges">
            <span class="hero-badge">🗄️ Northwind.db</span>
            <span class="hero-badge">⚡ Groq LLM</span>
            <span class="hero-badge">🔎 Hybrid RAG</span>
            <span class="hero-badge">📈 Auto Visualization</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("### 🤖 AI BI Agent")
    st.caption("How each question flows through the system")

    for index, step in enumerate(FLOW_STEPS):

        st.markdown(
            f'<div class="flow-step">{step}</div>',
            unsafe_allow_html=True
        )

        if index < len(FLOW_STEPS) - 1:
            st.markdown(
                '<div class="flow-arrow">↓</div>',
                unsafe_allow_html=True
            )

    st.divider()

    st.markdown("#### 💡 Example Questions")

    for index, example in enumerate(EXAMPLE_QUESTIONS):
        st.button(
            f"💬 {example}",
            key=f"example_{index}",
            on_click=queue_example,
            args=(example,),
        )

    st.divider()

    st.caption("🗄️ Database: Northwind.db")
    st.caption("⚡ LLM: Groq")
    st.caption("🖥️ Framework: Streamlit")


# ============================================================
# LOAD AGENT
# ============================================================

@st.cache_resource(show_spinner=False)
def load_agent():
    return AutonomousBIAgent()


with st.spinner("Building schema index…"):

    try:
        agent = load_agent()

    except Exception as error:

        st.error(
            f"❌ Failed to initialize Autonomous BI Agent:\n\n{error}"
        )

        st.stop()


# ============================================================
# QUESTION INPUT
# ============================================================

st.markdown(
    '<div class="section-title">🔎 Ask Your Business Question</div>',
    unsafe_allow_html=True
)

input_col, button_col = st.columns([5, 1])

with input_col:
    question = st.text_input(
        "Business question",
        key="question",
        placeholder=(
            "Example: What are the top 10 products by total sales?"
        ),
        label_visibility="collapsed",
        on_change=queue_run,
    )

with button_col:
    analyze_button = st.button(
        "🚀 Analyze",
        type="primary",
        use_container_width=True
    )


should_run = analyze_button or st.session_state.pending

st.session_state.pending = False


# ============================================================
# ANALYSIS
# ============================================================

if should_run:

    if not st.session_state.question.strip():

        st.warning("Please enter a business question.")

    else:

        status = st.status(
            "🤖 Agent is analyzing your question...",
            expanded=False,
        )

        started = time.perf_counter()

        try:

            result = agent.analyze(
                st.session_state.question,
                on_step=lambda label: status.update(label=label),
            )

            result["elapsed"] = time.perf_counter() - started

            status.update(
                label=f"✅ Analysis completed in "
                      f"{result['elapsed']:.1f}s",
                state="complete",
            )

            st.session_state.result = result

        except Exception as error:

            status.update(label="❌ Agent error", state="error")

            st.session_state.result = None

            st.error(f"❌ Agent error:\n\n{error}")


# ============================================================
# RESULTS
# ============================================================

result = st.session_state.result


if result is not None:

    dataframe = result["data"]
    summary = result["summary"]
    sql = result["sql"]
    chart = result["chart"]

    # --------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">📌 Executive Summary</div>',
        unsafe_allow_html=True
    )

    with st.container(key="summary_card"):
        st.markdown(summary)

    # --------------------------------------------------------
    # KPI METRICS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">📈 Query Overview</div>',
        unsafe_allow_html=True
    )

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:
        st.metric("Rows Returned", len(dataframe))

    with metric2:
        st.metric("Columns Returned", len(dataframe.columns))

    with metric3:
        st.metric(
            "Analysis Status",
            "No Data" if dataframe.empty else "Success",
        )

    with metric4:
        elapsed = result.get("elapsed")
        st.metric(
            "Runtime",
            f"{elapsed:.1f}s" if elapsed is not None else "—",
        )

    # --------------------------------------------------------
    # VISUALIZATION
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">📊 Visualization</div>',
        unsafe_allow_html=True
    )

    with st.container(key="chart_card"):

        if chart is not None:

            st.plotly_chart(
                chart,
                use_container_width=True,
                config={"displayModeBar": False},
            )

        elif headline(dataframe) is not None:

            # A single-row answer is a number, not a chart.
            value, label = headline(dataframe)

            st.markdown(
                '<div style="padding:1.6rem 0.4rem;">'
                f'<div class="figure-value">{value}</div>'
                f'<div class="figure-label">{label}</div>'
                '</div>',
                unsafe_allow_html=True
            )

        else:

            st.info(
                "No suitable visualization could be generated "
                "for this query."
            )

    # --------------------------------------------------------
    # QUERY RESULTS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">📋 Query Results</div>',
        unsafe_allow_html=True
    )

    with st.container(key="table_card"):

        if dataframe.empty:

            st.info("The query returned no records.")

        else:

            # Columns stay numeric so sorting still works;
            # only the display is formatted.
            column_config = {
                column: st.column_config.NumberColumn(
                    column,
                    format="%.2f",
                )
                for column in dataframe.columns
                if pd.api.types.is_float_dtype(dataframe[column])
            }

            st.dataframe(
                dataframe,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
            )

            st.download_button(
                label="⬇️ Download Results as CSV",
                data=dataframe.to_csv(index=False),
                file_name="bi_results.csv",
                mime="text/csv",
            )

    # --------------------------------------------------------
    # GENERATED SQL
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">🔍 Generated SQL</div>',
        unsafe_allow_html=True
    )

    with st.expander("View SQL generated by the AI agent"):
        st.code(sql, language="sql")

    # --------------------------------------------------------
    # AGENT PIPELINE
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">⚙️ Agent Pipeline</div>',
        unsafe_allow_html=True
    )

    columns = st.columns(len(PIPELINE_BOXES))

    for column, (icon, label) in zip(columns, PIPELINE_BOXES):
        with column:
            st.markdown(
                f'<div class="pipeline-box">{icon}<br>'
                f'<b>{label}</b></div>',
                unsafe_allow_html=True
            )


# ============================================================
# INITIAL SCREEN
# ============================================================

else:

    st.info(
        "👆 Enter a business question above and click "
        "**Analyze** to start the AI BI pipeline."
    )

    st.markdown(
        '<div class="section-title">💭 What can you ask?</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns(2)

    midpoint = (len(EXAMPLE_QUESTIONS) + 1) // 2

    for column, group in (
        (left, EXAMPLE_QUESTIONS[:midpoint]),
        (right, EXAMPLE_QUESTIONS[midpoint:]),
    ):
        with column:
            for example in group:
                st.markdown(
                    f'<div class="card">💬 {example}</div>',
                    unsafe_allow_html=True
                )

    st.caption(
        "The agent converts your natural-language question into "
        "a read-only SQL query and analyzes the Northwind database."
    )
