#!/usr/bin/env python3
"""
Compare one false-trigger eval result record to a stored baseline record.

Exit codes:
- 0: no regressions found
- 1: regression found
- 2: invalid input or incompatible records
"""

from __future__ import annotations

import argparse
from pathlib import Path

from eval_harness import load_json, validate_false_trigger_record

OUTCOME_RANK = {
    "fail": 0,
    "partial": 1,
    "pass": 2,
}

TRIGGER_BEHAVIOR_RANK = {
    "primary_trigger": 0,
    "partial_trigger": 1,
    "secondary_only": 2,
    "not_triggered": 3,
}


def compare_unexpected_lists(
    field_name: str,
    baseline_values: list[str],
    result_values: list[str],
    regressions: list[str],
    mismatches: list[str],
    improvements: list[str],
) -> None:
    new_entries = sorted(set(result_values) - set(baseline_values))
    cleared_entries = sorted(set(baseline_values) - set(result_values))
    if new_entries:
        regressions.append(f"{field_name} has new entries: {new_entries}")
    if cleared_entries:
        improvements.append(f"{field_name} cleared baseline entries: {cleared_entries}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a new false-trigger result to a stored baseline.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    result_path = Path(args.result)
    baseline = load_json(baseline_path)
    result = load_json(result_path)

    errors = []
    errors.extend(validate_false_trigger_record(baseline))
    errors.extend(validate_false_trigger_record(result))
    if errors:
        print("Comparison: INVALID")
        for error in errors:
            print(f"- {error}")
        return 2

    regressions: list[str] = []
    mismatches: list[str] = []
    improvements: list[str] = []

    for key in ("case_id", "workflow", "expected_should_trigger"):
        if baseline[key] != result[key]:
            regressions.append(
                f"{key} mismatch: baseline={baseline[key]!r} result={result[key]!r}"
            )
    if baseline.get("fixture_ref") != result.get("fixture_ref"):
        regressions.append(
            f"fixture_ref mismatch: baseline={baseline.get('fixture_ref')!r} result={result.get('fixture_ref')!r}"
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

    baseline_behavior = TRIGGER_BEHAVIOR_RANK[baseline["actual_trigger_behavior"]]
    result_behavior = TRIGGER_BEHAVIOR_RANK[result["actual_trigger_behavior"]]
    if result_behavior < baseline_behavior:
        regressions.append(
            "actual_trigger_behavior regressed: "
            f"baseline={baseline['actual_trigger_behavior']} "
            f"result={result['actual_trigger_behavior']}"
        )
    elif result_behavior > baseline_behavior:
        improvements.append(
            "actual_trigger_behavior improved: "
            f"baseline={baseline['actual_trigger_behavior']} "
            f"result={result['actual_trigger_behavior']}"
        )

    compare_unexpected_lists(
        "unexpected_subagents",
        baseline["unexpected_subagents"],
        result["unexpected_subagents"],
        regressions,
        mismatches,
        improvements,
    )
    compare_unexpected_lists(
        "unexpected_validation",
        baseline["unexpected_validation"],
        result["unexpected_validation"],
        regressions,
        mismatches,
        improvements,
    )
    compare_unexpected_lists(
        "fail_signals",
        baseline["fail_signals"],
        result["fail_signals"],
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
