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
from src.dashboard_generator import compact_number, headline


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="BI Assistant",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ============================================================
# DESIGN TOKENS
#
# Mirrors .streamlit/config.toml and dashboard_generator.py so
# the chart surface matches the message it sits in.
# ============================================================

TOKENS = {
    "bg":             "#0f1115",
    "surface":        "#161a21",
    "surface_raised": "#1c212a",
    "border":         "#252b36",
    "border_strong":  "#323a49",
    "text_primary":   "#e8eaed",
    "text_secondary": "#9aa3b2",
    "text_muted":     "#6b7482",
    "accent":         "#3987e5",
    "accent_soft":    "#6da7ec",
    "violet":         "#9085e9",
    "aqua":           "#199e70",
    "orange":         "#d95926",
    "good":           "#199e70",
}

# Chrome accents only - the chart keeps a single hue, because
# there colour encodes data. Validated against surface #161a21.
CARD_ACCENTS = [
    TOKENS["accent"],
    TOKENS["orange"],
    TOKENS["aqua"],
    TOKENS["violet"],
]

FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, '
    'Roboto, Helvetica, Arial, sans-serif'
)

MONO_STACK = (
    '"Cascadia Code", "SF Mono", "JetBrains Mono", '
    'Consolas, "Liberation Mono", monospace'
)


st.markdown(
    f"""
    <style>

    /* ---------- Base ---------- */

    html, body, [class*="css"] {{
        font-family: {FONT_STACK};
        -webkit-font-smoothing: antialiased;
    }}

    /* A soft wash keeps the page from reading as a flat slab
       without putting colour anywhere near the data. */
    [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(
                900px 520px at 12% -8%,
                {TOKENS["accent"]}1c,
                transparent 62%
            ),
            radial-gradient(
                760px 460px at 96% 4%,
                {TOKENS["violet"]}16,
                transparent 60%
            ),
            {TOKENS["bg"]};
    }}

    /* A conversation reads at a book measure, not a dashboard
       one. Bottom padding clears the pinned composer. */
    .block-container {{
        max-width: 820px;
        padding-top: 3.2rem;
        padding-bottom: 8rem;
    }}

    /* ---------- Conversation turns ---------- */

    [data-testid="stChatMessage"] {{
        background: transparent;
        padding: 0.15rem 0 1.5rem 0;
        gap: 0.85rem;
    }}

    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li {{
        font-size: 0.95rem;
        line-height: 1.68;
        color: {TOKENS["text_primary"]};
    }}

    /* The user's turn is a compact bubble; the agent's answer
       runs full width like a document. */
    /* Keys are per-turn (turn_user_0, turn_user_1, ...), so
       match on the prefix rather than an exact class. */
    [class*="st-key-turn_user"]
        [data-testid="stChatMessageContent"] {{
        background: linear-gradient(
            135deg,
            {TOKENS["accent"]}22 0%,
            {TOKENS["surface_raised"]} 70%
        );
        border: 1px solid {TOKENS["accent"]}33;
        border-radius: 14px 14px 14px 4px;
        padding: 0.7rem 1rem;
        /* Hug the text: as a flex child it would otherwise
           stretch to the full column width. */
        width: fit-content;
        max-width: 100%;
        flex: 0 1 auto;
        /* Streamlit sets both margins to auto, which centres a
           fit-content box. Zero the left one so the bubble sits
           against the avatar. */
        margin-left: 0 !important;
        margin-right: auto !important;
    }}

    [class*="st-key-turn_user"] p {{
        margin: 0 !important;
        color: {TOKENS["text_primary"]};
    }}

    /* ---------- Headings inside an answer ---------- */

    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] h4 {{
        font-size: 0.73rem !important;
        font-weight: 650 !important;
        letter-spacing: 0.085em;
        text-transform: uppercase;
        color: {TOKENS["text_muted"]} !important;
        margin: 1.45rem 0 0.5rem 0 !important;
        padding: 0 !important;
    }}

    [data-testid="stChatMessage"] table {{
        font-size: 0.87rem;
        border-collapse: collapse;
        margin: 0.45rem 0 1rem 0;
    }}

    [data-testid="stChatMessage"] th {{
        text-align: left;
        font-weight: 600;
        font-size: 0.7rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: {TOKENS["text_muted"]};
        border-bottom: 1px solid {TOKENS["border_strong"]};
        padding: 0.38rem 1.3rem 0.38rem 0;
        background: transparent;
    }}

    [data-testid="stChatMessage"] td {{
        padding: 0.4rem 1.3rem 0.4rem 0;
        border-bottom: 1px solid {TOKENS["border"]};
        color: {TOKENS["text_primary"]};
        font-variant-numeric: tabular-nums;
        background: transparent;
    }}

    /* ---------- Composer, pinned ---------- */

    [data-testid="stBottomBlockContainer"] {{
        background: linear-gradient(
            to bottom,
            rgba(15, 17, 21, 0) 0%,
            {TOKENS["bg"]} 22%
        );
        padding-bottom: 1.4rem;
        max-width: 820px;
    }}

    [data-testid="stChatInput"] {{
        background: {TOKENS["surface"]};
        border: 1px solid {TOKENS["border_strong"]};
        border-radius: 14px;
    }}

    [data-testid="stChatInput"]:focus-within {{
        border-color: {TOKENS["accent"]};
        box-shadow: 0 0 0 3px {TOKENS["accent"]}22;
    }}

    [data-testid="stChatInput"] textarea {{
        font-size: 0.95rem;
        color: {TOKENS["text_primary"]};
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        color: {TOKENS["text_muted"]};
    }}

    .composer-hint {{
        text-align: center;
        font-size: 0.72rem;
        color: {TOKENS["text_muted"]};
        margin-top: 0.5rem;
    }}

    /* ---------- Landing ---------- */

    .landing {{
        padding: 3.5rem 0 1.6rem 0;
        text-align: center;
    }}

    .landing-mark {{
        width: 46px;
        height: 46px;
        margin: 0 auto 1.25rem auto;
        border-radius: 13px;
        background: linear-gradient(
            145deg,
            {TOKENS["accent"]} 0%,
            {TOKENS["violet"]} 100%
        );
        box-shadow:
            0 8px 26px -6px {TOKENS["accent"]}80,
            0 0 0 1px {TOKENS["accent_soft"]}40;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    }}

    .landing-title {{
        font-size: 1.72rem;
        font-weight: 620;
        letter-spacing: -0.025em;
        margin-bottom: 0.5rem;
        background: linear-gradient(
            96deg,
            {TOKENS["text_primary"]} 18%,
            {TOKENS["accent_soft"]} 62%,
            {TOKENS["violet"]} 100%
        );
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: {TOKENS["text_primary"]};
    }}

    .landing-sub {{
        font-size: 0.92rem;
        color: {TOKENS["text_secondary"]};
        line-height: 1.6;
        max-width: 46ch;
        margin: 0 auto;
    }}

    .suggest-label {{
        font-size: 0.68rem;
        font-weight: 650;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: {TOKENS["text_muted"]};
        margin: 2.2rem 0 0.75rem 0;
    }}

    /* Suggestion buttons read as cards, not CTAs. */
    .st-key-suggestions .stButton button {{
        width: 100%;
        height: 100%;
        min-height: 4.1rem;
        text-align: left;
        justify-content: flex-start;
        align-items: flex-start;
        background: {TOKENS["surface"]};
        border: 1px solid {TOKENS["border"]};
        border-radius: 10px;
        color: {TOKENS["text_secondary"]};
        font-size: 0.85rem;
        font-weight: 400;
        line-height: 1.45;
        padding: 0.85rem 0.95rem;
        white-space: normal;
    }}

    .st-key-suggestions .stButton button:hover {{
        background: {TOKENS["surface_raised"]};
        border-color: {TOKENS["border_strong"]};
        color: {TOKENS["text_primary"]};
        transform: translateY(-2px);
        box-shadow: 0 10px 22px -14px #000;
    }}

    .st-key-suggestions .stButton button {{
        transition: transform .16s ease, box-shadow .16s ease,
                    border-color .16s ease, background .16s ease;
    }}

    /* Each card carries its own accent on the left edge and
       brightens it on hover. Four validated hues, fixed order -
       decoration in the chrome, never on a data mark. */
    .st-key-sugg_0 .stButton button {{
        border-left: 3px solid {CARD_ACCENTS[0]}66;
    }}
    .st-key-sugg_1 .stButton button {{
        border-left: 3px solid {CARD_ACCENTS[1]}66;
    }}
    .st-key-sugg_2 .stButton button {{
        border-left: 3px solid {CARD_ACCENTS[2]}66;
    }}
    .st-key-sugg_3 .stButton button {{
        border-left: 3px solid {CARD_ACCENTS[3]}66;
    }}
    .st-key-sugg_0 .stButton button:hover {{
        border-left-color: {CARD_ACCENTS[0]};
    }}
    .st-key-sugg_1 .stButton button:hover {{
        border-left-color: {CARD_ACCENTS[1]};
    }}
    .st-key-sugg_2 .stButton button:hover {{
        border-left-color: {CARD_ACCENTS[2]};
    }}
    .st-key-sugg_3 .stButton button:hover {{
        border-left-color: {CARD_ACCENTS[3]};
    }}

    /* The label is centred by `justify-content: center` on two
       nested flex wrappers inside the button - not by
       text-align, which is already left. */
    .st-key-suggestions .stButton button > div,
    .st-key-suggestions .stButton button > div > span {{
        justify-content: flex-start !important;
        width: 100% !important;
        text-align: left !important;
        font-size: 0.85rem;
        line-height: 1.45;
    }}

    /* ---------- Evidence tabs inside an answer ---------- */

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.3rem;
        border-bottom: 1px solid {TOKENS["border"]};
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 2.3rem;
        font-size: 0.8rem;
        font-weight: 550;
        color: {TOKENS["text_muted"]};
        padding: 0 0.75rem;
    }}

    .stTabs [aria-selected="true"] {{
        color: {TOKENS["text_primary"]} !important;
    }}

    /* ---------- Avatars ---------- */

    [data-testid="stChatMessageAvatarAssistant"] {{
        background: linear-gradient(
            145deg,
            {TOKENS["accent"]} 0%,
            {TOKENS["violet"]} 100%
        ) !important;
        box-shadow: 0 3px 12px -3px {TOKENS["accent"]}70;
    }}

    [data-testid="stChatMessageAvatarUser"] {{
        background: {TOKENS["surface_raised"]} !important;
        border: 1px solid {TOKENS["border_strong"]};
    }}

    /* ---------- Status ---------- */

    [data-testid="stExpander"] summary {{
        color: {TOKENS["text_secondary"]};
    }}

    [data-testid="stStatusWidget"],
    div[data-testid="stExpander"] details[open] {{
        border-color: {TOKENS["border"]};
    }}

    /* ---------- Section headings get a colour cue ---------- */

    .section-label {{
        color: {TOKENS["accent_soft"]};
    }}

    /* ---------- Hero figure ---------- */

    .hero {{
        padding: 1.6rem 0 1.2rem 0;
    }}

    .hero-value {{
        font-size: 3.4rem;
        font-weight: 620;
        line-height: 1;
        letter-spacing: -0.03em;
        font-variant-numeric: proportional-nums;
        background: linear-gradient(
            120deg,
            {TOKENS["text_primary"]} 8%,
            {TOKENS["accent_soft"]} 88%
        );
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: {TOKENS["text_primary"]};
    }}

    .hero-label {{
        margin-top: 0.55rem;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {TOKENS["text_muted"]};
    }}

    /* ---------- Run footnote ---------- */

    .run-meta {{
        display: flex;
        gap: 1.4rem;
        font-size: 0.72rem;
        color: {TOKENS["text_muted"]};
        padding-top: 0.9rem;
        margin-top: 0.3rem;
        border-top: 1px solid {TOKENS["border"]};
        font-variant-numeric: tabular-nums;
    }}

    /* ---------- Sidebar ---------- */

    .sidebar-brand {{
        display: flex;
        align-items: center;
        gap: 0.55rem;
        font-size: 0.95rem;
        font-weight: 650;
        letter-spacing: -0.01em;
        color: {TOKENS["text_primary"]};
        margin: 0.1rem 0 1.1rem 0;
    }}

    .sidebar-brand-mark {{
        width: 24px;
        height: 24px;
        border-radius: 7px;
        background: linear-gradient(
            145deg,
            {TOKENS["accent"]} 0%,
            {TOKENS["violet"]} 100%
        );
        box-shadow: 0 4px 12px -4px {TOKENS["accent"]}90;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.72rem;
    }}

    .sidebar-label {{
        font-size: 0.66rem;
        font-weight: 650;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: {TOKENS["text_muted"]};
        margin: 1.3rem 0 0.55rem 0;
    }}

    .spec-row {{
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        padding: 0.22rem 0;
        color: {TOKENS["text_muted"]};
    }}

    .spec-row span:last-child {{
        color: {TOKENS["text_secondary"]};
        font-weight: 500;
    }}

    code, pre, .stCode {{
        font-family: {MONO_STACK} !important;
    }}

    #MainMenu, footer {{
        visibility: hidden;
    }}

    /* Deploy button in the top-right toolbar. */
    [data-testid="stAppDeployButton"] {{
        display: none !important;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# CONSTANTS
# ============================================================

AGENT_AVATAR = "📊"
USER_AVATAR = "🧑"

SUGGESTIONS = [
    "What are the top 10 products by total sales?",
    "Which 5 countries generate the most revenue?",
    "Which employees handled the most orders?",
    "What are the top 5 customers by total sales?",
]


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "queued" not in st.session_state:
    st.session_state.queued = None


def queue_question(text):
    """A suggestion card behaves exactly like typing it."""

    st.session_state.queued = text


def reset_conversation():
    st.session_state.messages = []
    st.session_state.queued = None


# ============================================================
# HELPERS
# ============================================================

def render_evidence(payload, turn_index):
    """Chart / Data / SQL for one answered turn."""

    dataframe = payload["data"]
    chart = payload["chart"]

    chart_tab, data_tab, sql_tab = st.tabs(
        ["Chart", "Data", "SQL"]
    )

    with chart_tab:

        if chart is not None:

            st.plotly_chart(
                chart,
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"chart_{turn_index}",
            )

        elif headline(dataframe) is not None:

            value, label = headline(dataframe)

            st.markdown(
                '<div class="hero">'
                f'<div class="hero-value">{value}</div>'
                f'<div class="hero-label">{label}</div>'
                '</div>',
                unsafe_allow_html=True
            )

        else:

            st.caption(
                "No chart fits this result shape — "
                "the table has the values."
            )

    with data_tab:

        if dataframe.empty:

            st.caption("The query returned no records.")

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
                key=f"data_{turn_index}",
            )

            st.download_button(
                label="Download CSV",
                data=dataframe.to_csv(index=False),
                file_name="bi_results.csv",
                mime="text/csv",
                key=f"csv_{turn_index}",
            )

    with sql_tab:

        st.code(payload["sql"], language="sql")


def render_answer(payload, turn_index):
    """One assistant turn: the finding, then the evidence."""

    st.markdown(payload["summary"])

    render_evidence(payload, turn_index)

    rows = len(payload["data"])

    columns = len(payload["data"].columns)

    elapsed = payload.get("elapsed")

    parts = [
        f'{rows:,} row{"" if rows == 1 else "s"}',
        f'{columns} column{"" if columns == 1 else "s"}',
    ]

    if elapsed is not None:
        parts.append(f"{elapsed:.1f}s")

    st.markdown(
        '<div class="run-meta">'
        + "".join(f"<span>{part}</span>" for part in parts)
        + "</div>",
        unsafe_allow_html=True
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-brand">'
        '<span class="sidebar-brand-mark">📊</span>'
        'BI Assistant</div>',
        unsafe_allow_html=True
    )

    st.button(
        "New conversation",
        on_click=reset_conversation,
        use_container_width=True,
    )

    st.markdown(
        '<div class="sidebar-label">Pipeline</div>'
        '<div class="spec-row"><span>1 Retrieval</span>'
        '<span>Schema RAG</span></div>'
        '<div class="spec-row"><span>2 Generation</span>'
        '<span>Groq</span></div>'
        '<div class="spec-row"><span>3 Validation</span>'
        '<span>Read-only</span></div>'
        '<div class="spec-row"><span>4 Execution</span>'
        '<span>SQLite</span></div>'
        '<div class="spec-row"><span>5 Synthesis</span>'
        '<span>Chart + summary</span></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-label">Data</div>'
        '<div class="spec-row"><span>Database</span>'
        '<span>Northwind</span></div>'
        '<div class="spec-row"><span>Tables</span>'
        '<span>13</span></div>',
        unsafe_allow_html=True
    )


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

        st.error(f"Failed to initialise the agent: {error}")

        st.stop()


# ============================================================
# COMPOSER
#
# Read first even though it renders pinned at the bottom: the
# landing screen must know whether a question is arriving this
# run, or it draws above the very first answer.
# ============================================================

typed = st.chat_input("Ask a business question…")

question = typed or st.session_state.queued

st.session_state.queued = None


# ============================================================
# LANDING (empty conversation)
# ============================================================

if not st.session_state.messages and not question:

    st.markdown(
        '<div class="landing">'
        '<div class="landing-mark">📊</div>'
        '<div class="landing-title">Ask the Northwind data '
        'anything</div>'
        '<div class="landing-sub">I write the SQL, run it, and '
        'come back with the finding, a chart, and the query I '
        'used.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="suggest-label">Try one of these</div>',
        unsafe_allow_html=True
    )

    with st.container(key="suggestions"):

        left, right = st.columns(2, gap="small")

        for index, suggestion in enumerate(SUGGESTIONS):

            column = left if index % 2 == 0 else right

            # Each card sits in its own keyed container so the
            # CSS above can give it a distinct accent edge.
            with column:

                with st.container(key=f"sugg_{index}"):

                    st.button(
                        suggestion,
                        key=f"suggest_{index}",
                        on_click=queue_question,
                        args=(suggestion,),
                        use_container_width=True,
                    )


# ============================================================
# TRANSCRIPT
# ============================================================

for turn_index, message in enumerate(st.session_state.messages):

    if message["role"] == "user":

        with st.container(key=f"turn_user_{turn_index}"):

            with st.chat_message("user", avatar=USER_AVATAR):
                st.markdown(message["content"])

    else:

        with st.chat_message(
            "assistant", avatar=AGENT_AVATAR
        ):

            if message.get("error"):
                st.error(message["error"])
            else:
                render_answer(message["payload"], turn_index)


# ============================================================
# NEW TURN
# ============================================================

if question:

    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    turn_index = len(st.session_state.messages) - 1

    with st.container(key=f"turn_user_{turn_index}"):

        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(question)

    with st.chat_message("assistant", avatar=AGENT_AVATAR):

        status = st.status("Working…", expanded=False)

        started = time.perf_counter()

        try:

            result = agent.analyze(
                question,
                on_step=lambda label: status.update(label=label),
            )

            result["elapsed"] = time.perf_counter() - started

            status.update(
                label=f"Done in {result['elapsed']:.1f}s",
                state="complete",
            )

            st.session_state.messages.append(
                {"role": "assistant", "payload": result}
            )

            render_answer(
                result,
                len(st.session_state.messages) - 1,
            )

        except Exception as error:

            status.update(label="Failed", state="error")

            st.session_state.messages.append(
                {"role": "assistant", "error": str(error)}
            )

            st.error(str(error))
