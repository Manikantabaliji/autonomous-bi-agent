import os
import re
from collections import OrderedDict
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
# PROMPTS
#
# The old prompt carried 21 numbered rules. Eight of them
# ("never INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PRAGMA") are
# enforced deterministically by validate_sql() and by the
# read-only connection, and four more restated "return only
# SQL" in different words - roughly 180 tokens per call spent
# on instructions that either could not be trusted for safety
# anyway or were already said.
#
# What replaces them is guidance the code CANNOT enforce: the
# Northwind-specific traps that produce confidently wrong
# answers.
# ============================================================

SQL_PROMPT = """\
Convert the business question into ONE SQLite SELECT query.

SCHEMA:
{schema}

QUESTION:
{question}

RULES:
- Output the SQL only: no markdown, no commentary.
- Use only the tables and columns listed above.
- JOIN, GROUP BY and ORDER BY as the question requires;
  LIMIT for top-N.
- "Order Details" contains a space - always double-quote it.
- Revenue/sales = SUM(od.UnitPrice * od.Quantity *
  (1 - od.Discount)) from "Order Details" od. Use that table's
  UnitPrice (the price actually charged), never Products.UnitPrice.
- When ranking entities, select the entity's name, not only
  its ID, so the result is readable.
"""

REPAIR_PROMPT = """\
This SQLite query failed.

QUESTION IT MUST ANSWER:
{question}

QUERY:
{sql}

ERROR:
{error}

SCHEMA:
{schema}

Return the corrected SQL only. Use only the columns listed,
and make sure it still answers the question above.
"""


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
            api_key=api_key,
            max_retries=CONFIG["groq"].get("api_max_retries", 5),
        )


        # ----------------------------------------------------
        # Model configuration
        # ----------------------------------------------------

        self.model = CONFIG["groq"]["model"]

        self.temperature = CONFIG["groq"]["temperature"]

        self.max_tokens = CONFIG["groq"]["max_completion_tokens"]

        self.max_rows = CONFIG["agent"]["max_rows"]

        self.max_repairs = CONFIG["agent"].get(
            "max_repairs", 1
        )

        # question -> working SQL. Only the generation step is
        # cached; the query is always re-executed, so results
        # never go stale.
        self.cache_size = CONFIG["agent"].get(
            "cache_size", 128
        )

        self._sql_cache = OrderedDict()


        # ----------------------------------------------------
        # Initialize RAG
        # ----------------------------------------------------

        self.rag = SchemaRAG(
            top_k=CONFIG["rag"]["top_k"]
        )


    # ========================================================
    # GENERATE SQL
    # ========================================================

    def _complete(self, prompt: str):
        """
        One Groq round-trip returning cleaned SQL.
        Shared by first-pass generation and repair.
        """

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

        return self.clean_sql(content.strip())


    def generate_sql(
        self,
        question: str
    ):

        schema_context = self.rag.get_context(
            question
        )

        return self._complete(
            SQL_PROMPT.format(
                schema=schema_context,
                question=question,
            )
        )


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
    # SQL CACHE
    # ========================================================

    def _remember(self, key, sql):
        """Store working SQL, evicting the oldest entry."""

        self._sql_cache[key] = sql

        self._sql_cache.move_to_end(key)

        while len(self._sql_cache) > self.cache_size:
            self._sql_cache.popitem(last=False)


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
        # 1. Retrieve schema once and reuse it
        # ----------------------------------------------------

        schema_context = self.rag.get_context(
            question
        )


        # ----------------------------------------------------
        # 2. Generate, validate, execute - repairing once if
        #    the query fails.
        #
        #    A wrong column name used to surface to the user as
        #    a raw sqlite error. Feeding that error back with
        #    the schema recovers most of those, and costs extra
        #    tokens only on the runs that would have failed.
        # ----------------------------------------------------

        cache_key = question.strip().lower()

        cached = self._sql_cache.get(cache_key)

        if cached is not None:

            # Re-executed below, so the data is still fresh.
            self._sql_cache.move_to_end(cache_key)

            sql = cached

        else:

            sql = self._complete(
                SQL_PROMPT.format(
                    schema=schema_context,
                    question=question,
                )
            )

        attempts = self.max_repairs + 1

        for attempt in range(attempts):

            try:

                self.validate_sql(sql)

                dataframe = execute_query(sql)

                self._remember(cache_key, sql)

                break

            except Exception as error:

                if attempt == attempts - 1:
                    raise

                sql = self._complete(
                    REPAIR_PROMPT.format(
                        question=question,
                        sql=sql,
                        error=error,
                        schema=schema_context,
                    )
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