import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from groq import Groq

from src.db_utils import execute_query
from src.rag_index import SchemaRAG


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOAD CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


with open(
    CONFIG_PATH,
    "r",
    encoding="utf-8"
) as file:

    CONFIG = yaml.safe_load(file)


# ============================================================
# SQL AGENT
# ============================================================

class SQLAgent:

    def __init__(self):

        # ----------------------------------------------------
        # Get Groq API key
        # ----------------------------------------------------

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:

            raise ValueError(
                "GROQ_API_KEY is not configured."
            )


        # ----------------------------------------------------
        # Initialize Groq
        # ----------------------------------------------------

        self.client = Groq(
            api_key=api_key
        )


        # ----------------------------------------------------
        # Model configuration
        # ----------------------------------------------------

        self.model = CONFIG["groq"]["model"]

        self.temperature = CONFIG["groq"]["temperature"]

        self.max_tokens = CONFIG["groq"]["max_completion_tokens"]

        self.max_rows = CONFIG["agent"]["max_rows"]


        # ----------------------------------------------------
        # Initialize RAG
        # ----------------------------------------------------

        self.rag = SchemaRAG(
            top_k=CONFIG["rag"]["top_k"]
        )


    # ========================================================
    # GENERATE SQL
    # ========================================================

    def generate_sql(
        self,
        question: str
    ):

        # ----------------------------------------------------
        # Retrieve relevant schema
        # ----------------------------------------------------

        schema_context = self.rag.get_context(
            question
        )


        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        prompt = f"""
You are an expert Business Intelligence
SQL analyst.

You work with a SQLite Northwind database.

Your job is to convert the user's business
question into ONE valid SQLite SQL query.

RELEVANT DATABASE SCHEMA:

{schema_context}


USER QUESTION:

{question}


STRICT RULES:

1. Return ONLY SQL.
2. Do not use markdown.
3. Generate exactly one SQL statement.
4. Only SELECT or WITH queries are allowed.
5. Never modify the database.
6. Never use INSERT.
7. Never use UPDATE.
8. Never use DELETE.
9. Never use DROP.
10. Never use ALTER.
11. Never use CREATE.
12. Never use PRAGMA.
13. Use only tables and columns provided
    in the database schema.
14. Use SQLite-compatible SQL.
15. Use JOIN when information comes
    from multiple tables.
16. Use GROUP BY when required.
17. Use ORDER BY for ranking.
18. Use LIMIT for top-N questions.
19. Never invent columns.
20. Do not explain the SQL.
21. Return only the SQL query.

Return ONLY the SQL.
"""


        # ----------------------------------------------------
        # Call Groq
        # ----------------------------------------------------

        response = (
            self.client
            .chat
            .completions
            .create(

                model=self.model,

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise "
                            "SQLite SQL generator."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=self.temperature,

                max_completion_tokens=self.max_tokens
            )
        )


        # ----------------------------------------------------
        # Get response
        # ----------------------------------------------------

        content = (
            response
            .choices[0]
            .message
            .content
        )


        if not content:

            raise ValueError(
                "Groq returned an empty SQL response."
            )


        sql = content.strip()


        # ----------------------------------------------------
        # Clean markdown if model adds it
        # ----------------------------------------------------

        sql = self.clean_sql(
            sql
        )


        return sql


    # ========================================================
    # CLEAN SQL
    # ========================================================

    @staticmethod
    def clean_sql(sql: str):

        # Remove ```sql
        sql = re.sub(
            r"```sql",
            "",
            sql,
            flags=re.IGNORECASE
        )

        # Remove ```SQL
        sql = re.sub(
            r"```SQL",
            "",
            sql,
            flags=re.IGNORECASE
        )

        # Remove generic ```
        sql = sql.replace(
            "```",
            ""
        )

        return sql.strip()


    # ========================================================
    # VALIDATE SQL
    # ========================================================

    @staticmethod
    def validate_sql(sql: str):

        if not sql:

            raise ValueError(
                "SQL query is empty."
            )


        sql_clean = (
            sql
            .strip()
            .lower()
        )


        # ----------------------------------------------------
        # Must be SELECT or WITH
        # ----------------------------------------------------

        if not (
            sql_clean.startswith("select")
            or sql_clean.startswith("with")
        ):

            raise ValueError(
                "Only SELECT or WITH queries "
                "are allowed."
            )


        # ----------------------------------------------------
        # Dangerous SQL keywords
        # ----------------------------------------------------

        forbidden_keywords = [

            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "create",
            "replace",
            "attach",
            "detach",
            "pragma"

        ]


        for keyword in forbidden_keywords:

            if re.search(
                rf"\b{keyword}\b",
                sql_clean
            ):

                raise ValueError(
                    f"Unsafe SQL keyword detected: "
                    f"{keyword}"
                )


        return True


    # ========================================================
    # RUN COMPLETE SQL AGENT
    # ========================================================

    def run(
        self,
        question: str
    ):

        if not question or not question.strip():

            raise ValueError(
                "Question cannot be empty."
            )


        # ----------------------------------------------------
        # 1. Generate SQL
        # ----------------------------------------------------

        sql = self.generate_sql(
            question
        )


        # ----------------------------------------------------
        # 2. Validate SQL
        # ----------------------------------------------------

        self.validate_sql(
            sql
        )


        # ----------------------------------------------------
        # 3. Execute SQL
        # ----------------------------------------------------

        dataframe = execute_query(
            sql
        )


        # ----------------------------------------------------
        # 4. Limit result size
        # ----------------------------------------------------

        if len(dataframe) > self.max_rows:

            dataframe = dataframe.head(
                self.max_rows
            )


        # ----------------------------------------------------
        # 5. Return result
        # ----------------------------------------------------

        return {

            "question": question,

            "sql": sql,

            "data": dataframe

        }