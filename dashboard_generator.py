import pandas as pd
import plotly.express as px


class DashboardGenerator:
    """
    Automatically selects and creates a suitable
    Plotly visualization from a query result.
    """

    def __init__(self, max_chart_rows=20):

        self.max_chart_rows = max_chart_rows


    # ========================================================
    # COLUMN DETECTION
    # ========================================================

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


        # ----------------------------------------------------
        # BAR CHART
        # ----------------------------------------------------

        if chart_type == "bar":

            x_column = categorical_columns[0]

            y_column = numeric_columns[0]


            chart_df = (
                df
                .head(self.max_chart_rows)
                .copy()
            )


            chart = px.bar(
                chart_df,
                x=x_column,
                y=y_column,
                title=(
                    f"{y_column} by "
                    f"{x_column}"
                ),
                text_auto=".2s"
            )


            chart.update_layout(
                xaxis_title=x_column,
                yaxis_title=y_column,
                xaxis_tickangle=-45
            )


            return chart


        # ----------------------------------------------------
        # SCATTER PLOT
        # ----------------------------------------------------

        if chart_type == "scatter":

            x_column = numeric_columns[0]

            y_column = numeric_columns[1]


            chart = px.scatter(
                df.head(
                    self.max_chart_rows
                ),
                x=x_column,
                y=y_column,
                title=(
                    f"{y_column} vs "
                    f"{x_column}"
                )
            )


            return chart


        # ----------------------------------------------------
        # HISTOGRAM
        # ----------------------------------------------------

        if chart_type == "histogram":

            x_column = numeric_columns[0]


            chart = px.histogram(
                df,
                x=x_column,
                title=(
                    f"Distribution of "
                    f"{x_column}"
                )
            )


            return chart


        # ----------------------------------------------------
        # NO CHART
        # ----------------------------------------------------

        return None