from src.sql_agent import SQLAgent
from src.summary_generator import (
    SummaryGenerator
)


print("=" * 70)
print("EXECUTIVE SUMMARY TEST")
print("=" * 70)


# ============================================================
# CREATE COMPONENTS
# ============================================================

sql_agent = SQLAgent()

summary_generator = (
    SummaryGenerator()
)


# ============================================================
# QUESTION
# ============================================================

question = (
    "What are the top 10 products by total sales?"
)


print("\nQUESTION:")
print(question)


# ============================================================
# SQL AGENT
# ============================================================

result = sql_agent.run(
    question
)


# ============================================================
# SUMMARY
# ============================================================

summary = (
    summary_generator.generate(

        question=question,

        sql=result["sql"],

        dataframe=result["data"]
    )
)


print("\nEXECUTIVE SUMMARY:")
print("-" * 70)

print(summary)


print("\n" + "=" * 70)
print("✅ SUMMARY TEST COMPLETED")
print("=" * 70)