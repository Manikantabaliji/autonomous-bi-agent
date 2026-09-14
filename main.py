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
        self.dashboard_generator = DashboardGenerator(
            max_chart_rows=20
        )

    def analyze(self, question: str):
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
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        # --------------------------------------------------
        # STEP 1: Generate SQL and execute query
        # --------------------------------------------------
        result = self.sql_agent.run(question)

        sql = result["sql"]
        dataframe = result["data"]

        # --------------------------------------------------
        # STEP 2: Generate executive summary
        # --------------------------------------------------
        summary = self.summary_generator.generate(
            question=question,
            sql=sql,
            dataframe=dataframe
        )

        # --------------------------------------------------
        # STEP 3: Generate visualization
        # --------------------------------------------------
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