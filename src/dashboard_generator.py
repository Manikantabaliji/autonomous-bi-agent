import pandas as pd
import plotly.express as px


# ============================================================
# CHART THEME
#
# Tokens mirror .streamlit/config.toml so charts sit on the
# card surface instead of punching a white hole through it.
# The categorical order is fixed (never cycled) and validated
# for colour-vision deficiency against surface #161a21.
# ============================================================

# Light theme, matching the interface.
SURFACE = "#FFFFFF"
PLOT_BG = "#F8FAFC"
GRID = "#E5E7EB"
AXIS_LINE = "#D1D5DB"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#4B5563"
TEXT_MUTED = "#6B7280"

# Palette carried over from the shared UI work. The hues are
# unchanged; the ORDER was adjusted because emerald sat next to
# cyan, a pair only 12.5 dE apart - below the 15 floor, so
# neighbouring bars were hard to tell apart even with normal
# colour vision. Swapping amber and emerald (and moving teal
# away from pink) clears every gate on the adjacent pairlist
# against surface #F8FAFC.
SERIES = [
    "#4F46E5",  # indigo
    "#06B6D4",  # cyan
    "#F59E0B",  # amber
    "#10B981",  # emerald
    "#EF4444",  # red
    "#14B8A6",  # teal
    "#8B5CF6",  # purple
    "#EC4899",  # pink
]

# Two ways to colour a ranked bar chart:
#
#   "categorical" - each bar takes the next hue from SERIES, in
#     fixed order. More colourful, and the eight slots are
#     validated for colour-vision deficiency on adjacent pairs.
#     The honest caveat: on a ranking, length already carries
#     the story, so hue here is decoration, not information.
#
#   "emphasis" - leader in the accent, the rest a lighter tint
#     of the same hue. Quieter, and hue means something.
#
# Beyond eight bars categorical falls back to emphasis: cycling
# the palette would give two different bars the same colour,
# which is worse than not colouring them at all.
SERIES_LEAD = "#4F46E5"
SERIES_REST = "#A5B4FC"

MAX_CATEGORICAL = len(SERIES)

FONT_STACK = (
    '-apple-system, "Segoe UI", Inter, Roboto, '
    "Helvetica, Arial, sans-serif"
)

# A bar chart with few enough bars gets direct labels and no
# value axis; past this it gets an axis and no labels, so the
# plot never carries a number on every mark.
DIRECT_LABEL_LIMIT = 10

# A ranked result reads as horizontal bars: no rotated ticks,
# and thickness is bounded by the band height rather than by
# however wide the container happens to be. Vertical columns are
# reserved for categories that are really a time axis.
TIME_HINTS = (
    "year", "month", "quarter", "date", "day", "week",
    "period", "time",
)

# Each horizontal bar gets this much vertical band; with the
# bargap below that puts the mark itself at ~21px, under the
# 24px cap.
BAND_HEIGHT = 38
BAR_GAP = 0.45


def compact_number(value):
    """
    Format a number the way an analyst reads it: 53.3M, 1.2K,
    240. Used for direct labels, where width is scarce.
    """

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    sign = "-" if number < 0 else ""
    number = abs(number)

    # Four-digit numbers read better with a separator than as
    # "1.9K", so compaction starts above 10,000.
    for threshold, suffix, floor in (
        (1_000_000_000, "B", 1_000_000_000),
        (1_000_000, "M", 1_000_000),
        (1_000, "K", 10_000),
    ):
        if number >= floor:
            scaled = number / threshold
            digits = 1 if scaled < 100 else 0
            return f"{sign}{scaled:.{digits}f}{suffix}"

    if number == int(number):
        return f"{sign}{int(number):,}"

    return f"{sign}{number:,.2f}"


def headline(df):
    """
    For a single-row result, the value worth showing large and
    the label that identifies it - e.g. (1,9xx, "Peacock") or
    (93, "COUNT(*)"). Returns None when the result is not a
    single row, so the caller can fall back to a chart.

    Lives here so the column-picking rules match the chart's.
    """

    if df is None or len(df) != 1:
        return None

    numeric_columns, categorical_columns = (
        DashboardGenerator.get_column_types(df)
    )

    if not numeric_columns:
        return None

    measure = DashboardGenerator.pick_measure(numeric_columns)

    value = compact_number(df.iloc[0][measure])

    if categorical_columns:

        category = DashboardGenerator.pick_category(
            categorical_columns
        )

        # Name who it is and what was measured, so the number
        # is not left floating without its unit.
        return value, f"{df.iloc[0][category]} · {measure}"

    return value, str(measure)


class DashboardGenerator:
    """
    Automatically selects and creates a suitable
    Plotly visualization from a query result.
    """

    def __init__(self, max_chart_rows=20, color_mode="categorical"):

        self.max_chart_rows = max_chart_rows

        self.color_mode = color_mode


    # ========================================================
    # BAR COLOURS
    # ========================================================

    def bar_colors(self, count, horizontal):
        """
        One colour per bar, top-ranked first.

        Horizontal bars are drawn bottom-up after the reversal,
        so the palette is flipped to keep the leader on slot 1
        either way - the top bar is always the same colour.
        """

        categorical = (
            self.color_mode == "categorical"
            and count <= MAX_CATEGORICAL
        )

        if categorical:
            colors = [SERIES[i] for i in range(count)]

        else:
            colors = [
                SERIES_LEAD if i == 0 else SERIES_REST
                for i in range(count)
            ]

        return colors[::-1] if horizontal else colors

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    @staticmethod
    def looks_like_identifier(column_name):
        """
        ProductID is numeric but it is not a measure. Charting
        it produces a plausible-looking chart of meaningless
        values, which is worse than no chart.
        """

        name = str(column_name).strip().lower().replace("_", "")

        return (
            name == "id"
            or name.endswith("id")
            or name.endswith("code")
            or name.endswith("no")
            or name.endswith("number")
        )

    @classmethod
    def pick_measure(cls, numeric_columns):
        """
        The measure is the value worth plotting. Identifier
        columns are excluded; of what remains the last is
        chosen, since aggregates trail the SELECT list
        (SELECT id, name, SUM(...) AS total).
        """

        candidates = [
            column
            for column in numeric_columns
            if not cls.looks_like_identifier(column)
        ]

        if not candidates:
            candidates = numeric_columns

        return candidates[-1]

    @classmethod
    def pick_category(cls, categorical_columns):
        """Prefer a real label over an identifier-ish column."""

        candidates = [
            column
            for column in categorical_columns
            if not cls.looks_like_identifier(column)
        ]

        if not candidates:
            candidates = categorical_columns

        return candidates[0]

    @staticmethod
    def get_column_types(df):

        numeric_columns = (
            df.select_dtypes(
                include="number"
            )
            .columns
            .tolist()
        )

        categorical_columns = (
            df.select_dtypes(
                exclude="number"
            )
            .columns
            .tolist()
        )

        return (
            numeric_columns,
            categorical_columns
        )

    # ========================================================
    # CHOOSE CHART
    # ========================================================

    def choose_chart_type(self, df):

        if df.empty:
            return "table"

        numeric_columns, categorical_columns = (
            self.get_column_types(df)
        )

        # A single row is a number, not a chart - whether it is
        # a bare scalar ("how many customers?") or a labelled
        # one ("who handled the most orders?"). A one-bar bar
        # chart is the classic way to miss that.
        if len(df) == 1 and numeric_columns:
            return "figure"

        # Category + numeric
        if (
            len(categorical_columns) >= 1
            and len(numeric_columns) >= 1
        ):
            return "bar"

        # Two or more numeric columns
        if len(numeric_columns) >= 2:
            return "scatter"

        # One numeric column
        if len(numeric_columns) == 1:
            return "histogram"

        return "table"

    # ========================================================
    # SHARED STYLING
    # ========================================================

    @staticmethod
    def _apply_theme(chart, title, show_value_axis=True):
        """
        Recessive chrome, transparent surface, text in text
        tokens rather than the data colour.
        """

        chart.update_layout(
            title=dict(
                text=title,
                font=dict(
                    size=15,
                    color=TEXT_PRIMARY,
                    family=FONT_STACK,
                ),
                x=0,
                xanchor="left",
                pad=dict(b=14),
            ),
            font=dict(
                family=FONT_STACK,
                size=12,
                color=TEXT_SECONDARY,
            ),
            paper_bgcolor=SURFACE,
            plot_bgcolor=PLOT_BG,
            margin=dict(l=8, r=24, t=52, b=8),
            showlegend=False,
            hoverlabel=dict(
                bgcolor=SURFACE,
                bordercolor=AXIS_LINE,
                font=dict(
                    family=FONT_STACK,
                    size=12,
                    color=TEXT_PRIMARY,
                ),
            ),
            bargap=BAR_GAP,
        )

        axis_common = dict(
            showline=False,
            zeroline=False,
            ticks="",
            title=None,
        )

        # Hairline, solid, one step off the surface - and only
        # on the value axis. A grid on the category axis is
        # ink that carries nothing.
        chart.update_xaxes(**axis_common)
        chart.update_yaxes(**axis_common)

        return chart

    # ========================================================
    # CREATE CHART
    # ========================================================

    def create_chart(self, df):

        if df.empty:
            return None

        chart_type = (
            self.choose_chart_type(df)
        )

        numeric_columns, categorical_columns = (
            self.get_column_types(df)
        )

        # The app renders this as a hero figure; returning a
        # chart here would draw a single meaningless mark.
        if chart_type == "figure":
            return None

        # ----------------------------------------------------
        # BAR CHART
        # ----------------------------------------------------

        if chart_type == "bar":

            category_column = self.pick_category(
                categorical_columns
            )

            value_column = self.pick_measure(numeric_columns)

            chart_df = (
                df
                .head(self.max_chart_rows)
                .copy()
            )

            # Vertical columns only when the category axis is
            # really time; everything else is a ranking and
            # reads better horizontally.
            looks_temporal = any(
                hint in category_column.lower()
                for hint in TIME_HINTS
            )

            horizontal = not looks_temporal

            direct_labels = (
                len(chart_df) <= DIRECT_LABEL_LIMIT
            )

            text_values = (
                [
                    compact_number(v)
                    for v in chart_df[value_column]
                ]
                if direct_labels
                else None
            )

            title = (
                f"{value_column} by {category_column}"
            )

            if horizontal:

                # Largest at the top reads as a ranking.
                chart_df = chart_df.iloc[::-1]

                if text_values is not None:
                    text_values = text_values[::-1]

                chart = px.bar(
                    chart_df,
                    x=value_column,
                    y=category_column,
                    orientation="h",
                    text=text_values,
                )

                chart.update_xaxes(
                    showgrid=not direct_labels,
                    gridcolor=GRID,
                    gridwidth=1,
                    visible=not direct_labels,
                    tickformat="~s",
                )

                chart.update_yaxes(
                    showgrid=False,
                    tickfont=dict(color=TEXT_SECONDARY),
                )

                chart.update_traces(
                    textposition="outside",
                    cliponaxis=False,
                )

            else:

                chart = px.bar(
                    chart_df,
                    x=category_column,
                    y=value_column,
                    text=text_values,
                )

                chart.update_yaxes(
                    showgrid=not direct_labels,
                    gridcolor=GRID,
                    gridwidth=1,
                    visible=not direct_labels,
                    tickformat="~s",
                )

                chart.update_xaxes(
                    showgrid=False,
                    tickfont=dict(color=TEXT_SECONDARY),
                )

                chart.update_traces(
                    textposition="outside",
                    cliponaxis=False,
                )

            bar_colors = self.bar_colors(
                len(chart_df),
                horizontal,
            )

            chart.update_traces(
                marker_color=bar_colors,
                marker_line_width=0,
                marker_cornerradius=4,
                textfont=dict(
                    color=TEXT_SECONDARY,
                    size=12,
                    family=FONT_STACK,
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{value_column}: "
                    "%{customdata[1]}<extra></extra>"
                ),
                customdata=list(
                    zip(
                        chart_df[category_column].astype(str),
                        [
                            f"{v:,.2f}"
                            if isinstance(v, float)
                            else f"{v:,}"
                            for v in chart_df[value_column]
                        ],
                    )
                ),
            )

            chart = self._apply_theme(chart, title)

            if horizontal:

                # Fix the band per bar so five rows and twenty
                # rows both get ~21px marks instead of slabs.
                chart.update_layout(
                    height=(
                        96 + len(chart_df) * BAND_HEIGHT
                    ),
                    margin=dict(l=8, r=72, t=52, b=16),
                )

            else:

                # A column's width is a fraction of its slot, so
                # cap it directly - with few categories the slot
                # is enormous.
                chart.update_traces(
                    width=min(0.62, 3.0 / len(chart_df))
                )

            return chart

        # ----------------------------------------------------
        # SCATTER PLOT
        # ----------------------------------------------------

        if chart_type == "scatter":

            measures = [
                column
                for column in numeric_columns
                if not self.looks_like_identifier(column)
            ]

            if len(measures) < 2:
                measures = numeric_columns

            x_column = measures[0]

            y_column = measures[1]

            chart = px.scatter(
                df.head(
                    self.max_chart_rows
                ),
                x=x_column,
                y=y_column,
            )

            chart.update_traces(
                marker=dict(
                    size=9,
                    color=SERIES[0],
                    line=dict(width=2, color=SURFACE),
                ),
                hovertemplate=(
                    f"{x_column}: %{{x:,}}<br>"
                    f"{y_column}: %{{y:,}}"
                    "<extra></extra>"
                ),
            )

            for axis in (chart.update_xaxes, chart.update_yaxes):
                axis(
                    showgrid=True,
                    gridcolor=GRID,
                    gridwidth=1,
                    tickformat="~s",
                )

            return self._apply_theme(
                chart,
                f"{y_column} vs {x_column}",
            )

        # ----------------------------------------------------
        # HISTOGRAM
        # ----------------------------------------------------

        if chart_type == "histogram":

            x_column = self.pick_measure(numeric_columns)

            chart = px.histogram(
                df,
                x=x_column,
            )

            chart.update_traces(
                marker_color=SERIES[0],
                marker_line_width=0,
                marker_cornerradius=4,
                hovertemplate=(
                    f"{x_column}: %{{x}}<br>"
                    "Count: %{y:,}<extra></extra>"
                ),
            )

            chart.update_xaxes(
                showgrid=False,
                tickformat="~s",
            )

            chart.update_yaxes(
                showgrid=True,
                gridcolor=GRID,
                gridwidth=1,
            )

            return self._apply_theme(
                chart,
                f"Distribution of {x_column}",
            )

        # ----------------------------------------------------
        # NO CHART
        # ----------------------------------------------------

        return None
