from src.sql_agent import SQLAgent
from src.dashboard_generator import (
    DashboardGenerator
)


print("=" * 70)
print("NORTHWIND DASHBOARD INTEGRATION TEST")
print("=" * 70)


# ============================================================
# CREATE AGENTS
# ============================================================

sql_agent = SQLAgent()

dashboard = DashboardGenerator()


# ============================================================
# BUSINESS QUESTION
# ============================================================

question = (
    "What are the top 10 products by total sales?"
)


print("\nQUESTION:")
print(question)


# ============================================================
# RUN SQL AGENT
# ============================================================

result = sql_agent.run(
    question
)


dataframe = result["data"]


print("\nGENERATED SQL:")
print("-" * 70)

print(
    result["sql"]
)


print("\nQUERY RESULT:")
print("-" * 70)

print(
    dataframe
)


# ============================================================
# CREATE CHART
# ============================================================

chart = (
    dashboard.create_chart(
        dataframe
    )
)


print("\nCHART:")
print("-" * 70)


if chart is not None:

    print(
        "✅ Dashboard chart created successfully."
    )

    print(
        "Chart type:",
        type(chart).__name__
    )

else:

    print(
        "❌ No chart generated."
    )


print("\n" + "=" * 70)
print("✅ DASHBOARD INTEGRATION TEST COMPLETED")
print("=" * 70)