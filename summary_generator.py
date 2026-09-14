import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from groq import Groq


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "config.yaml"
)


with open(
    CONFIG_PATH,
    "r",
    encoding="utf-8"
) as file:

    CONFIG = yaml.safe_load(file)


# ============================================================
# SUMMARY GENERATOR
# ============================================================

class SummaryGenerator:
    """
    Converts SQL query results into
    an executive BI summary.
    """

    def __init__(self):

        api_key = os.getenv(
            "GROQ_API_KEY"
        )


        if not api_key:

            raise ValueError(
                "GROQ_API_KEY is not configured."
            )


        self.client = Groq(
            api_key=api_key
        )


        self.model = (
            CONFIG["groq"]["model"]
        )


    # ========================================================
    # GENERATE SUMMARY
    # ========================================================

    def generate(
        self,
        question,
        sql,
        dataframe
    ):

        # ----------------------------------------------------
        # Empty result
        # ----------------------------------------------------

        if dataframe.empty:

            return (
                "No records were returned "
                "for this question."
            )


        # ----------------------------------------------------
        # Convert result to text
        # ----------------------------------------------------

        data_preview = (
            dataframe
            .head(30)
            .to_string(
                index=False
            )
        )


        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        prompt = f"""
You are a senior Business Intelligence
analyst.

USER QUESTION:
{question}


SQL QUERY:
{sql}


QUERY RESULTS:
{data_preview}


Analyze the results and produce a concise
executive summary.

Structure your answer as:

### Key Finding
State the main result.

### Important Numbers
Mention the most important numbers
from the results.

### Business Insight
Explain what the result means
from a business perspective.

### Observation
Provide one useful observation
based only on the data.

STRICT RULES:

1. Do not invent data.
2. Do not make claims unsupported
   by the query results.
3. Do not repeat the SQL.
4. Keep the summary concise.
5. Use professional BI language.
"""


        # ----------------------------------------------------
        # Groq
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
                            "You are a senior "
                            "Business Intelligence "
                            "analyst."
                        )
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }

                ],

                temperature=0,

                max_completion_tokens=1500
            )
        )


        # ----------------------------------------------------
        # Extract result
        # ----------------------------------------------------

        summary = (
            response
            .choices[0]
            .message
            .content
        )


        if not summary:

            raise ValueError(
                "Groq returned an empty summary."
            )


        return summary.strip()