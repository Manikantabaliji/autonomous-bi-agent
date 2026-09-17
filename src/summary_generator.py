import os
from pathlib import Path

import pandas as pd
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
            api_key=api_key,
            max_retries=CONFIG["groq"].get("api_max_retries", 5),
        )


        self.model = (
            CONFIG["groq"]["model"]
        )

        self.max_tokens = CONFIG["groq"].get(
            "summary_max_tokens", 2000
        )

        self.reasoning_effort = CONFIG["groq"].get(
            "summary_reasoning_effort", "low"
        )


    # ========================================================
    # RESULT PREVIEW
    # ========================================================

    PREVIEW_ROWS = 15

    @classmethod
    def format_preview(cls, dataframe):
        """
        Compact CSV of the result.

        to_string() pads every cell to a common column width,
        so a wide result spent a large share of its tokens on
        alignment spaces the model never needed. Floats are
        rounded to 2dp for the same reason - fourteen digits of
        precision buys nothing in an executive summary.
        """

        preview = dataframe.head(cls.PREVIEW_ROWS).copy()

        for column in preview.columns:

            if pd.api.types.is_float_dtype(preview[column]):
                preview[column] = preview[column].round(2)

        text = preview.to_csv(index=False).strip()

        hidden = len(dataframe) - len(preview)

        if hidden > 0:

            # Truncation without the true totals made the model
            # compute shares against the rows it could see: a
            # 22-row result was described as "42.7% of the 82
            # customers shown" when the real total was 93.
            # Correct arithmetic, wrong denominator. The exact
            # totals cost a few tokens and remove the trap.
            totals = []

            for column in dataframe.columns:

                if pd.api.types.is_numeric_dtype(
                    dataframe[column]
                ):
                    total = dataframe[column].sum()
                    totals.append(f"{column}={total:,.2f}")

            text += (
                f"\n\nTRUNCATED: showing {len(preview)} of "
                f"{len(dataframe):,} rows. Totals across ALL "
                f"{len(dataframe):,} rows: "
                + "; ".join(totals)
                + ". Use these totals for any percentage or "
                "share - never sum the visible rows."
            )

        return text


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

        data_preview = self.format_preview(
            dataframe
        )


        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        # A single-row answer ("93 customers") does not support
        # four sections - demanding them forced the model to
        # pad, which cost output tokens and diluted the answer.
        # The shape of the result picks the shape of the
        # summary.
        if len(dataframe) == 1:

            structure = (
                "### Key Finding\n"
                "One or two sentences stating the result "
                "and its number.\n\n"
                "### Business Insight\n"
                "One or two sentences on what it means."
            )

        else:

            structure = (
                "### Key Finding\n"
                "The main result, in one or two sentences.\n\n"
                "### Important Numbers\n"
                "The few figures that carry the finding.\n\n"
                "### Business Insight\n"
                "What it means commercially.\n\n"
                "### Observation\n"
                "One further point supported by the data "
                "(a gap, a concentration, an outlier)."
            )

        prompt = f"""\
You are a senior Business Intelligence analyst.

QUESTION:
{question}

RESULTS (CSV):
{data_preview}

Write a concise executive summary in this structure:

{structure}

Use only the figures above - never invent or extrapolate
beyond them, and do not restate the SQL. Reference entities by
name. Be specific and brief; no filler.

Any percentage or difference you state must be computed
exactly from the figures above and given to one decimal place
(e.g. "42.1%", "$27.6 million") - never rounded to a vague
approximation such as "roughly 40%".

Percentages are always relative to a stated base, so name the
base and divide by it:
- "A is N% higher than B" means N = (A - B) / B x 100.
  Divide by B, the value being compared against - not by A.
- "A is N% of the total" means N = A / total x 100.
Where the base is ambiguous, write the share of the total
instead.
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

                max_completion_tokens=self.max_tokens,

                reasoning_effort=self.reasoning_effort,
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