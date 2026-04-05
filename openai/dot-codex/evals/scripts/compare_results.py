#!/usr/bin/env python3
"""
Compare one eval result record to a stored baseline record.

Exit codes:
- 0: no regressions found
- 1: regression found
- 2: invalid input or incompatible records
"""

from __future__ import annotations

import argparse
from pathlib import Path

from eval_harness import load_json, validate_result_record

OUTCOME_RANK = {
    "fail": 0,
    "partial": 1,
    "pass": 2,
}


def compare_lists(
    field_name: str,
    baseline_values: list[str],
    result_values: list[str],
    regressions: list[str],
    mismatches: list[str],
    improvements: list[str],
) -> None:
    missing = sorted(set(baseline_values) - set(result_values))
    extra = sorted(set(result_values) - set(baseline_values))
    if field_name == "observed_fail_signals":
        if extra:
            regressions.append(f"new fail signals observed: {extra}")
        if missing:
            improvements.append(f"baseline fail signals not observed now: {missing}")
        return
    if missing:
        regressions.append(f"{field_name} missing baseline entries: {missing}")
    if extra:
        mismatches.append(f"{field_name} has extra entries: {extra}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a new result to a stored baseline.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    result_path = Path(args.result)
    baseline = load_json(baseline_path)
    result = load_json(result_path)

    errors = []
    errors.extend(validate_result_record(baseline))
    errors.extend(validate_result_record(result))
    if errors:
        print("Comparison: INVALID")
        for error in errors:
            print(f"- {error}")
        return 2

    regressions: list[str] = []
    mismatches: list[str] = []
    improvements: list[str] = []

    for key in ("case_id", "workflow"):
        if baseline[key] != result[key]:
            regressions.append(
                f"{key} mismatch: baseline={baseline[key]!r} result={result[key]!r}"
            )

    baseline_outcome = OUTCOME_RANK[baseline["outcome"]]
    result_outcome = OUTCOME_RANK[result["outcome"]]
    if result_outcome < baseline_outcome:
        regressions.append(
            f"outcome regressed: baseline={baseline['outcome']} result={result['outcome']}"
        )
    elif result_outcome > baseline_outcome:
        improvements.append(
            f"outcome improved: baseline={baseline['outcome']} result={result['outcome']}"
        )

    compare_lists(
        "observed_subagents",
        baseline["observed_subagents"],
        result["observed_subagents"],
        regressions,
        mismatches,
        improvements,
    )
    compare_lists(
        "observed_validation",
        baseline["observed_validation"],
        result["observed_validation"],
        regressions,
        mismatches,
        improvements,
    )
    compare_lists(
        "observed_fail_signals",
        baseline["observed_fail_signals"],
        result["observed_fail_signals"],
        regressions,
        mismatches,
        improvements,
    )

    baseline_rubric = baseline.get("rubric", {})
    result_rubric = result.get("rubric", {})
    for key in sorted(set(baseline_rubric) | set(result_rubric)):
        baseline_value = baseline_rubric.get(key)
        result_value = result_rubric.get(key)
        if baseline_value is True and result_value is False:
            regressions.append(f"rubric.{key} regressed: baseline=true result=false")
        elif baseline_value is False and result_value is True:
            improvements.append(f"rubric.{key} improved: baseline=false result=true")
        elif baseline_value != result_value:
            mismatches.append(
                f"rubric.{key} changed: baseline={baseline_value} result={result_value}"
            )

    if regressions:
        status = "REGRESSION"
    elif mismatches:
        status = "MISMATCH"
    elif improvements:
        status = "IMPROVED"
    else:
        status = "MATCH"

    print(f"Comparison: {status}")
    print(f"Baseline: {baseline_path}")
    print(f"Result:   {result_path}")
    print(f"Case:     {baseline['case_id']} ({baseline['workflow']})")

    if regressions:
        print("Regressions:")
        for item in regressions:
            print(f"- {item}")
    if mismatches:
        print("Mismatches:")
        for item in mismatches:
            print(f"- {item}")
    if improvements:
        print("Improvements:")
        for item in improvements:
            print(f"- {item}")

    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
