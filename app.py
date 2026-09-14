import sys
from pathlib import Path

import streamlit as st


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from main import AutonomousBIAgent


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Autonomous BI Agent",
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

    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
    }

    .pipeline-box {
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        background-color: #f8fafc;
        text-align: center;
        margin-bottom: 1rem;
    }

    .small-text {
        font-size: 0.85rem;
        color: #6b7280;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">📊 Autonomous BI Agent</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="subtitle">
    Ask business questions in natural language and let the AI
    generate SQL, analyze the Northwind database, create
    visualizations, and provide executive insights.
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🤖 AI BI Agent")

    st.markdown(
        """
        This agent automatically performs:

        **Natural Language**
        ↓

        **Hybrid RAG**
        ↓

        **Groq SQL Generation**
        ↓

        **SQL Validation**
        ↓

        **SQLite Analysis**
        ↓

        **Visualization**
        ↓

        **Executive Summary**
        """
    )

    st.divider()

    st.subheader("💡 Example Questions")

    example_questions = [
        "How many customers are there?",
        "What are the top 10 products by total sales?",
        "Which employees handled the most orders?",
        "What are the top 5 customers by total sales?",
        "Which countries have the most customers?"
    ]

    for example in example_questions:
        st.markdown(f"• {example}")

    st.divider()

    st.caption("Database: Northwind SQLite")
    st.caption("LLM: Groq")
    st.caption("Framework: Streamlit")


# ============================================================
# LOAD AGENT
# ============================================================

@st.cache_resource
def load_agent():
    return AutonomousBIAgent()


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

question = st.text_input(
    "Business question",
    placeholder=(
        "Example: What are the top 10 products by total sales?"
    ),
    label_visibility="collapsed"
)


analyze_button = st.button(
    "🚀 Analyze",
    type="primary",
    use_container_width=False
)


# ============================================================
# ANALYSIS
# ============================================================

if analyze_button:

    if not question.strip():

        st.warning(
            "Please enter a business question."
        )

        st.stop()

    with st.spinner(
        "🤖 Agent is analyzing your question..."
    ):

        try:

            result = agent.analyze(question)

        except Exception as error:

            st.error(
                f"❌ Agent error:\n\n{error}"
            )

            st.stop()


    dataframe = result["data"]
    summary = result["summary"]
    sql = result["sql"]
    chart = result["chart"]


    # ========================================================
    # SUCCESS MESSAGE
    # ========================================================

    st.success(
        "✅ Analysis completed successfully."
    )


    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================

    st.markdown(
        '<div class="section-title">📌 Executive Summary</div>',
        unsafe_allow_html=True
    )

    st.markdown(summary)


    # ========================================================
    # KPI METRICS
    # ========================================================

    st.markdown(
        '<div class="section-title">📈 Query Overview</div>',
        unsafe_allow_html=True
    )

    metric1, metric2, metric3 = st.columns(3)

    with metric1:

        st.metric(
            "Rows Returned",
            len(dataframe)
        )

    with metric2:

        st.metric(
            "Columns Returned",
            len(dataframe.columns)
        )

    with metric3:

        if dataframe.empty:
            status = "No Data"
        else:
            status = "Success"

        st.metric(
            "Analysis Status",
            status
        )


    # ========================================================
    # VISUALIZATION
    # ========================================================

    st.markdown(
        '<div class="section-title">📊 Visualization</div>',
        unsafe_allow_html=True
    )

    if chart is not None:

        st.plotly_chart(
            chart,
            use_container_width=True
        )

    else:

        st.info(
            "No suitable visualization could be generated "
            "for this query."
        )


    # ========================================================
    # QUERY RESULTS
    # ========================================================

    st.markdown(
        '<div class="section-title">📋 Query Results</div>',
        unsafe_allow_html=True
    )

    if dataframe.empty:

        st.info(
            "The query returned no records."
        )

    else:

        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    if not dataframe.empty:

        csv_data = dataframe.to_csv(
            index=False
        )

        st.download_button(
            label="⬇️ Download Results as CSV",
            data=csv_data,
            file_name="bi_results.csv",
            mime="text/csv"
        )


    # ========================================================
    # GENERATED SQL
    # ========================================================

    st.markdown(
        '<div class="section-title">🔍 Generated SQL</div>',
        unsafe_allow_html=True
    )

    with st.expander(
        "View SQL generated by the AI agent"
    ):

        st.code(
            sql,
            language="sql"
        )


    # ========================================================
    # AGENT PIPELINE
    # ========================================================

    st.markdown(
        '<div class="section-title">⚙️ Agent Pipeline</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.markdown(
            '<div class="pipeline-box">🧑‍💼<br>'
            '<b>Question</b></div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            '<div class="pipeline-box">🔎<br>'
            '<b>RAG</b></div>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            '<div class="pipeline-box">🤖<br>'
            '<b>Groq</b></div>',
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            '<div class="pipeline-box">🗄️<br>'
            '<b>SQLite</b></div>',
            unsafe_allow_html=True
        )

    with col5:
        st.markdown(
            '<div class="pipeline-box">📊<br>'
            '<b>Dashboard</b></div>',
            unsafe_allow_html=True
        )

    with col6:
        st.markdown(
            '<div class="pipeline-box">💡<br>'
            '<b>Insight</b></div>',
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
        """
        ### What can you ask?

        Try questions such as:

        - **How many customers are there?**
        - **What are the top 10 products by total sales?**
        - **Which employees handled the most orders?**
        - **What are the top 5 customers by sales?**
        - **Which countries have the most customers?**

        The agent converts your natural-language question into
        a read-only SQL query and analyzes the Northwind database.
        """
    )