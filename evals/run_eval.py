"""
Evaluation harness for the Autonomous BI Agent.

Runs every case in cases.yaml through the full pipeline and
grades four things:

  1. Execution    - did the generated SQL run at all?
  2. Accuracy     - do the results match hand-written
                    reference SQL, compared on VALUES rather
                    than query text?
  3. Grounding    - is every number in the executive summary
                    traceable to the returned data? (catches
                    invented figures)
  4. Chart form   - does the visualisation suit the shape of
                    the result?

Cost and latency are recorded per case, and the number of LLM
calls reveals when the repair loop fired.

    py -3 evals/run_eval.py             # all cases
    py -3 evals/run_eval.py --case top5_products_revenue
    py -3 evals/run_eval.py --json out.json
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import AutonomousBIAgent                    # noqa: E402
from src.dashboard_generator import DashboardGenerator  # noqa: E402
from src.db_utils import execute_query                # noqa: E402

CASES_PATH = Path(__file__).parent / "cases.yaml"

# Revenue sums differ in the last cents between equivalent
# formulations, so values compare on relative tolerance.
TOLERANCE = 0.005

# Seconds to wait between cases; --pace 0 to disable.
PACE_SECONDS = 8

# A 429 is the free tier's tokens-per-minute cap, not a defect
# in the agent. Wait out the window and try the case again so
# the score measures the agent rather than the quota.
RATE_LIMIT_PAUSE = 30


# ============================================================
# TOKEN ACCOUNTING
# ============================================================

class UsageMeter:
    """Wraps the Groq client to record usage per case."""

    def __init__(self):
        self.calls = []
        self._original = None

    def install(self):
        from groq.resources.chat import completions

        self._original = completions.Completions.create
        meter = self

        def create(inner_self, *args, **kwargs):
            response = meter._original(inner_self, *args, **kwargs)
            usage = response.usage
            meter.calls.append({
                "prompt": usage.prompt_tokens,
                "completion": usage.completion_tokens,
                "total": usage.total_tokens,
            })
            return response

        completions.Completions.create = create

    def reset(self):
        self.calls = []

    @property
    def totals(self):
        return {
            "llm_calls": len(self.calls),
            "prompt_tokens": sum(c["prompt"] for c in self.calls),
            "completion_tokens": sum(
                c["completion"] for c in self.calls
            ),
            "total_tokens": sum(c["total"] for c in self.calls),
        }


# ============================================================
# FRAME HELPERS
# ============================================================

def numeric_columns(frame):
    return frame.select_dtypes(include="number").columns.tolist()


def measure_series(frame):
    """
    The column carrying the answer's magnitude, chosen with the
    same rules the charts use so eval and product agree.
    """

    numbers = numeric_columns(frame)

    if not numbers:
        return None

    return frame[DashboardGenerator.pick_measure(numbers)]


def row_labels(frame, index):
    """
    Every text cell in a row, lowercased.

    Compared loosely because a correct answer may name an
    employee as LastName, as FirstName, or as both - all of
    which identify the same row.
    """

    labels = set()

    for column in frame.columns:

        if pd.api.types.is_numeric_dtype(frame[column]):
            continue

        value = str(frame.iloc[index][column]).strip().lower()

        if value and value != "nan":
            labels.add(value)

    return labels


def label_matches(expected, candidates):
    """True when the expected label names one of the cells."""

    expected = expected.strip().lower()

    return any(
        expected == candidate
        or expected in candidate
        or candidate in expected
        for candidate in candidates
    )


def close(a, b):
    if a is None or b is None:
        return False

    a, b = float(a), float(b)

    if a == b:
        return True

    scale = max(abs(a), abs(b), 1e-9)

    return abs(a - b) / scale <= TOLERANCE


# ============================================================
# GRADERS
# ============================================================

def grade_accuracy(case, actual, expected):
    """Compare results by value; returns (passed, detail)."""

    mode = case["mode"]

    if actual is None or actual.empty:
        return False, "no rows returned"

    actual_measure = measure_series(actual)
    expected_measure = measure_series(expected)

    # --------------------------------------------------------
    # SCALAR - one number
    # --------------------------------------------------------

    if mode == "scalar":

        if actual_measure is None:
            return False, "no numeric column"

        if len(actual) != 1:
            return False, f"expected 1 row, got {len(actual)}"

        got = actual_measure.iloc[0]
        want = expected_measure.iloc[0]

        if close(got, want):
            return True, f"{got:g}"

        return False, f"got {got:g}, expected {want:g}"

    # --------------------------------------------------------
    # RANKED - order is part of the answer
    # --------------------------------------------------------

    if mode == "ranked":

        limit = case.get("limit", len(expected))

        if len(actual) < limit:
            return False, (
                f"expected >= {limit} rows, got {len(actual)}"
            )

        for position in range(limit):

            expected_labels = row_labels(expected, position)

            if expected_labels:

                if not any(
                    label_matches(label, row_labels(actual, position))
                    for label in expected_labels
                ):
                    return False, (
                        f"rank {position + 1}: expected "
                        f"{sorted(expected_labels)}, got "
                        f"{sorted(row_labels(actual, position))}"
                    )

            if actual_measure is not None:

                if not close(
                    actual_measure.iloc[position],
                    expected_measure.iloc[position],
                ):
                    return False, (
                        f"rank {position + 1} value: got "
                        f"{actual_measure.iloc[position]:,.2f}, "
                        f"expected "
                        f"{expected_measure.iloc[position]:,.2f}"
                    )

        return True, f"top {limit} match"

    # --------------------------------------------------------
    # SET - same rows, any order
    # --------------------------------------------------------

    if mode == "set":

        if len(actual) != len(expected):
            return False, (
                f"expected {len(expected)} rows, "
                f"got {len(actual)}"
            )

        if actual_measure is None:
            return False, "no numeric column"

        got = sorted(actual_measure.dropna().tolist())
        want = sorted(expected_measure.dropna().tolist())

        for a, b in zip(got, want):
            if not close(a, b):
                return False, (
                    f"value mismatch: {a:,.2f} vs {b:,.2f}"
                )

        return True, f"{len(actual)} rows match"

    return False, f"unknown mode: {mode}"


NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def grade_grounding(summary, frame):
    """
    Every number the summary states should be findable in the
    data. Unmatched figures are reported rather than failed:
    a legitimately derived number (a percentage, a difference)
    will not appear verbatim, so this is a signal to read, not
    a hard gate.
    """

    if frame is None or frame.empty or not summary:
        return 1.0, []

    known = set()

    for column in numeric_columns(frame):

        for value in frame[column].dropna():

            value = float(value)

            known.add(round(value, 2))
            known.add(round(value))
            # Compact renderings: 6,154,115.34 -> "6.2" or
            # "6.15"; both name the same figure.
            for unit in (1e3, 1e6, 1e9):
                if abs(value) >= unit:
                    known.add(round(value / unit, 1))
                    known.add(round(value / unit, 2))

            known.add(round(value / 100, 2))  # percent-of-1

    known.add(float(len(frame)))

    for column in numeric_columns(frame):
        total = float(frame[column].sum())
        known.add(round(total, 2))
        known.add(round(total))
        for unit in (1e3, 1e6, 1e9):
            if abs(total) >= unit:
                known.add(round(total / unit, 1))

    # Summaries legitimately state figures DERIVED from the
    # rows - "the gap between first and fifth is $27.6M",
    # "Beverages is 41% of the three". Those are correct
    # analysis, so they must not read as invention. Derivations
    # are only enumerated for small results, otherwise the
    # candidate set grows until it matches anything.
    measure = measure_series(frame)

    if measure is not None and len(frame) <= 25:

        values = [float(v) for v in measure.dropna()]

        total = sum(values)

        for i, a in enumerate(values):

            if total:
                share = a / total * 100
                known.add(round(share, 1))
                known.add(round(share))

            for b in values[i + 1:]:

                gap = abs(a - b)

                known.add(round(gap, 2))
                known.add(round(gap))

                for unit in (1e3, 1e6, 1e9):
                    if gap >= unit:
                        known.add(round(gap / unit, 1))
                        known.add(round(gap / unit, 2))

                # "X is N% higher than Y" - a gap expressed
                # against either side. Kept to small results:
                # every extra derived family makes the
                # candidate set more permissive, and past ~10
                # rows this one would start matching anything.
                if len(values) <= 10:

                    for base in (a, b):

                        if base:
                            relative = gap / abs(base) * 100
                            known.add(round(relative, 1))
                            known.add(round(relative))

    stated = []
    unmatched = []

    for raw in NUMBER_PATTERN.findall(summary):

        cleaned = raw.replace(",", "").rstrip(".")

        if not cleaned or cleaned in {"-", "."}:
            continue

        try:
            number = float(cleaned)
        except ValueError:
            continue

        # Small integers are ordinals and counts ("the top 5"),
        # not claims about the data.
        if abs(number) <= 12 and number == int(number):
            continue

        stated.append(number)

        if any(
            close(number, candidate)
            for candidate in known
        ):
            continue

        unmatched.append(raw)

    if not stated:
        return 1.0, []

    rate = 1.0 - (len(unmatched) / len(stated))

    return rate, unmatched


COMPARISON_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*"
    r"(higher|more|greater|larger|lower|less|smaller|below|above)"
    r"\s+than",
    re.IGNORECASE,
)


def grade_comparisons(summary, frame):
    """
    Check the BASE of "A is N% higher than B" claims.

    Numeric grounding cannot catch this: the agent once wrote
    "53.8% higher than second" for a gap that is 53.8% of the
    FIRST value and 116% of the second. The figure is perfectly
    traceable to the data - it is the sentence that is wrong.

    A relative comparison divides by the value being compared
    against. So a percentage that matches gap/larger but not
    gap/smaller is a mis-based claim, not a coincidence.
    """

    if frame is None or len(frame) < 2 or not summary:
        return True, []

    measure = measure_series(frame)

    if measure is None:
        return True, []

    values = [float(v) for v in measure.dropna()]

    if len(values) < 2:
        return True, []

    correct = set()
    mis_based = set()

    for i, a in enumerate(values):

        for b in values[i + 1:]:

            gap = abs(a - b)
            smaller, larger = min(a, b), max(a, b)

            # Dividing by the compared-against value.
            if smaller:
                correct.add(round(gap / smaller * 100, 1))

            # Dividing by the larger value instead: the gap as
            # a share of the bigger number, which is not what
            # "N% higher than" means.
            if larger:
                mis_based.add(round(gap / larger * 100, 1))

    problems = []

    for raw, _direction in COMPARISON_PATTERN.findall(summary):

        stated = float(raw)

        if any(close(stated, c) for c in correct):
            continue

        if any(close(stated, m) for m in mis_based):
            problems.append(
                f"{raw}% stated as a relative comparison but "
                f"equals the gap over the LARGER value"
            )

    return not problems, problems


def grade_chart(chart, frame):
    """The form should suit the shape of the result."""

    if frame is None or frame.empty:
        return chart is None, "empty result -> no chart"

    if len(frame) == 1:

        if chart is None:
            return True, "single row -> figure"

        return False, "single row drew a chart"

    if chart is None:
        return False, "multi-row result drew no chart"

    return True, f"{chart.data[0].type} chart"


# ============================================================
# RUNNER
# ============================================================

def run(selected=None):

    cases = yaml.safe_load(
        CASES_PATH.read_text(encoding="utf-8")
    )

    if selected:
        cases = [c for c in cases if c["id"] in selected]

        if not cases:
            raise SystemExit(f"no case matching {selected}")

    meter = UsageMeter()
    meter.install()

    agent = AutonomousBIAgent()

    results = []

    for position, case in enumerate(cases):

        # Groq's free tier caps tokens-per-minute. Running 12
        # cases back to back trips it, and a 429 then looks
        # exactly like an agent failure in the report. Pacing
        # keeps the numbers about the agent.
        if position and PACE_SECONDS:
            time.sleep(PACE_SECONDS)

        meter.reset()

        started = time.perf_counter()

        record = {
            "id": case["id"],
            "question": case["question"],
            "mode": case["mode"],
        }

        # The pipeline reports each stage before entering it,
        # so a failure can be attributed to the stage that
        # actually broke. Without this a summary failure was
        # reported as "did not execute", which pointed at the
        # SQL and was simply wrong.
        stage = {"name": "startup"}

        try:
            try:
                output = agent.analyze(
                    case["question"],
                    on_step=lambda label: stage.update(name=label),
                )

            except Exception as error:

                message = str(error).lower()

                if "rate_limit" not in message:
                    raise

                # A per-minute cap clears in seconds; a daily
                # quota does not. Retrying a TPD limit just
                # burns wall-clock and reports zeros, so stop
                # and say plainly that the run is unusable.
                if "per day" in message or "tpd" in message:
                    raise SystemExit(
                        "\nDaily API token quota exhausted - "
                        "the eval cannot run.\nThis is a "
                        "billing limit, not an agent failure. "
                        "Re-run after the quota resets."
                    )

                record["rate_limited"] = True

                time.sleep(RATE_LIMIT_PAUSE)

                meter.reset()

                started = time.perf_counter()

                output = agent.analyze(
                    case["question"],
                    on_step=lambda label: stage.update(name=label),
                )

            frame = output["data"]

            record["executed"] = True
            record["sql"] = " ".join(output["sql"].split())

        except Exception as error:

            record.update({
                "executed": False,
                "failed_stage": stage["name"],
                "error": f"{type(error).__name__}: {error}",
                "correct": False,
                "accuracy_detail": "pipeline error",
                "grounding": 0.0,
                "unmatched_numbers": [],
                "chart_ok": False,
                "chart_detail": "n/a",
                "comparisons_ok": False,
                "comparison_problems": [],
                "elapsed": time.perf_counter() - started,
                **meter.totals,
            })

            results.append(record)
            continue

        expected = execute_query(case["sql"])

        correct, detail = grade_accuracy(case, frame, expected)

        grounding, unmatched = grade_grounding(
            output["summary"], frame
        )

        chart_ok, chart_detail = grade_chart(
            output["chart"], frame
        )

        comparisons_ok, comparison_problems = grade_comparisons(
            output["summary"], frame
        )

        record.update({
            "correct": correct,
            "comparisons_ok": comparisons_ok,
            "comparison_problems": comparison_problems,
            "accuracy_detail": detail,
            "grounding": round(grounding, 3),
            "unmatched_numbers": unmatched,
            "chart_ok": chart_ok,
            "chart_detail": chart_detail,
            "rows": len(frame),
            "elapsed": round(time.perf_counter() - started, 2),
            **meter.totals,
        })

        results.append(record)

    return results


def report(results):

    total = len(results)

    executed = sum(r["executed"] for r in results)
    correct = sum(r["correct"] for r in results)
    charts = sum(r["chart_ok"] for r in results)
    repairs = sum(r["llm_calls"] > 2 for r in results)

    grounding = (
        sum(r["grounding"] for r in results) / total
        if total else 0.0
    )

    tokens = sum(r["total_tokens"] for r in results)
    elapsed = sum(r["elapsed"] for r in results)

    print()
    print("=" * 78)
    print("AUTONOMOUS BI AGENT - EVALUATION")
    print("=" * 78)
    print(f"{'CASE':<26}{'EXEC':<6}{'CORRECT':<9}"
          f"{'GROUND':<8}{'CMP':<5}{'CHART':<7}"
          f"{'TOK':<7}{'SEC':<6}")
    print("-" * 78)

    for r in results:

        print(
            f"{r['id']:<26}"
            f"{'ok' if r['executed'] else 'FAIL':<6}"
            f"{'ok' if r['correct'] else 'FAIL':<9}"
            f"{r['grounding']:<8.0%}"
            f"{'ok' if r.get('comparisons_ok') else 'FAIL':<5}"
            f"{'ok' if r['chart_ok'] else 'FAIL':<7}"
            f"{r['total_tokens']:<7}"
            f"{r['elapsed']:<6.1f}"
        )

        if not r["executed"]:
            print(
                f"    -> failed during: {r.get('failed_stage')}"
            )
            print(f"    -> {r.get('error', '')}")

        elif not r["correct"]:
            print(f"    -> {r.get('accuracy_detail', '')}")

        if not r["chart_ok"]:
            print(f"    -> chart: {r.get('chart_detail', '')}")

        for problem in r.get("comparison_problems", []):
            print(f"    -> comparison: {problem}")

        if r["unmatched_numbers"]:
            print(
                "    -> unverified figures: "
                + ", ".join(r["unmatched_numbers"][:6])
            )

    print("-" * 78)
    print(f"Execution   {executed}/{total} "
          f"({executed / total:.0%})")
    print(f"Accuracy    {correct}/{total} "
          f"({correct / total:.0%})")
    print(f"Grounding   {grounding:.0%} of stated figures "
          f"traceable to the data")
    comparisons = sum(
        r.get("comparisons_ok", False) for r in results
    )

    print(f"Comparisons {comparisons}/{total} "
          f"({comparisons / total:.0%}) correctly based")
    print(f"Chart form  {charts}/{total} "
          f"({charts / total:.0%})")
    throttled = sum(
        r.get("rate_limited", False) for r in results
    )

    print(f"Repairs     {repairs} case(s) needed a retry")

    if throttled:
        print(f"Throttled   {throttled} case(s) hit the API "
              f"rate limit and were retried")
    print(f"Cost        {tokens:,} tokens "
          f"({tokens / total:,.0f}/question)")
    print(f"Latency     {elapsed:.1f}s total "
          f"({elapsed / total:.1f}s/question)")
    print("=" * 78)

    return correct == total and executed == total


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append")
    parser.add_argument(
        "--pace",
        type=float,
        help="seconds between cases (default 6, 0 to disable)",
    )
    parser.add_argument("--json")
    args = parser.parse_args()

    if args.pace is not None:
        PACE_SECONDS = args.pace

    results = run(selected=args.case)

    passed = report(results)

    if args.json:

        payload = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }

        Path(args.json).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        print(f"\nWrote {args.json}")

    sys.exit(0 if passed else 1)
