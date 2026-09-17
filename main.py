import yaml
from pathlib import Path

from src.sql_agent import SQLAgent
from src.dashboard_generator import DashboardGenerator
from src.summary_generator import SummaryGenerator


class AutonomousBIAgent:
    """
    Central orchestration layer for the
    Autonomous BI Agent.
    """

    def __init__(self):
        self.sql_agent = SQLAgent()
        self.summary_generator = SummaryGenerator()
        config = yaml.safe_load(
            (
                Path(__file__).resolve().parent
                / "config" / "config.yaml"
            ).read_text(encoding="utf-8")
        )["dashboard"]

        self.dashboard_generator = DashboardGenerator(
            max_chart_rows=config.get("max_chart_rows", 20),
            color_mode=config.get("color_mode", "categorical"),
        )

    def analyze(self, question: str, on_step=None):
        """
        Complete BI analysis pipeline:

        Question
            ↓
        RAG + Groq SQL Agent
            ↓
        SQL Validation
            ↓
        SQLite Execution
            ↓
        Dashboard Generation
            ↓
        Executive Summary

        `on_step` is an optional callable invoked with a short
        label before each stage, so a caller can report
        progress. Orchestration stays here; the UI only
        observes.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        def report(label):
            if on_step is not None:
                on_step(label)

        # --------------------------------------------------
        # STEP 1: Generate SQL and execute query
        # --------------------------------------------------
        report("Retrieving schema and writing SQL")

        result = self.sql_agent.run(question)

        sql = result["sql"]
        dataframe = result["data"]

        # --------------------------------------------------
        # STEP 2: Generate executive summary
        # --------------------------------------------------
        report("Summarising the result")

        summary = self.summary_generator.generate(
            question=question,
            sql=sql,
            dataframe=dataframe
        )

        # --------------------------------------------------
        # STEP 3: Generate visualization
        # --------------------------------------------------
        report("Building the visualisation")

        chart = self.dashboard_generator.create_chart(
            dataframe
        )

        # --------------------------------------------------
        # STEP 4: Return complete analysis
        # --------------------------------------------------
        return {
            "question": question,
            "sql": sql,
            "data": dataframe,
            "summary": summary,
            "chart": chart
        }


if __name__ == "__main__":

    print("=" * 70)
    print("AUTONOMOUS BI AGENT")
    print("=" * 70)

    agent = AutonomousBIAgent()

    question = input(
        "\nAsk a BI question: "
    )

    try:
        result = agent.analyze(question)

        print("\n" + "=" * 70)
        print("EXECUTIVE SUMMARY")
        print("=" * 70)
        print(result["summary"])

        print("\n" + "=" * 70)
        print("GENERATED SQL")
        print("=" * 70)
        print(result["sql"])

        print("\n" + "=" * 70)
        print("QUERY RESULTS")
        print("=" * 70)
        print(result["data"])

        print("\n" + "=" * 70)
        print("DASHBOARD")
        print("=" * 70)

        if result["chart"] is not None:
            print("✅ Chart generated successfully.")
        else:
            print("ℹ️ No chart generated.")

        print("\n" + "=" * 70)
        print("✅ ANALYSIS COMPLETED")
        print("=" * 70)

    except Exception as error:
        print("\n❌ AGENT ERROR")
        print(error)