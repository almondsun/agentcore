#!/usr/bin/env python3
"""
Run the supported automated eval cases in batch using the existing harness scripts.

Exit codes:
- 0: all selected cases completed with no regressions
- 1: at least one comparison reported REGRESSION
- 2: invalid setup or invalid selected cases before execution
- 3: runtime failure while running or comparing one or more cases
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from eval_harness import (
    ROOT,
    baseline_path_for,
    find_case,
    load_automation_manifest,
    load_json,
    resolve_results_dir,
)

RUN_CASE_SCRIPT = ROOT / "scripts" / "run_automated_case.py"
COMPARE_RESULTS_SCRIPT = ROOT / "scripts" / "compare_results.py"
COMPARE_FALSE_TRIGGER_RESULTS_SCRIPT = ROOT / "scripts" / "compare_false_trigger_results.py"
SUMMARY_SCHEMA_VERSION = "1"


def default_summary_path(run_date: str, automation_scope: str, results_dir: Path) -> Path:
    if automation_scope == "negative":
        name = "batch-negative-summary.json"
    elif automation_scope == "all":
        name = "batch-all-summary.json"
    else:
        name = "batch-summary.json"
    root = results_dir.resolve()
    candidate = root.joinpath(run_date, name).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"summary path escapes results root: {candidate}")
    return candidate


def validate_run_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid --date {value!r}; expected YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"Invalid --date {value!r}; expected YYYY-MM-DD")
    return value


def unique_case_ids(case_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for case_id in case_ids:
        if case_id in seen:
            continue
        seen.add(case_id)
        ordered.append(case_id)
    return ordered


def resolve_selected_cases(
    requested_case_ids: list[str], automation_scope: str
) -> tuple[list[dict[str, Any]], list[str]]:
    _, automation_catalog = load_automation_manifest()
    _, negative_automation_catalog = load_automation_manifest(kind="negative")
    scoped_catalog: dict[str, str] = {}
    if automation_scope in {"positive", "all"}:
        for case_id in automation_catalog:
            scoped_catalog[case_id] = "positive"
    if automation_scope in {"negative", "all"}:
        for case_id in negative_automation_catalog:
            scoped_catalog[case_id] = "negative"

    supported_case_ids = list(scoped_catalog)
    selected_case_ids = unique_case_ids(requested_case_ids) if requested_case_ids else supported_case_ids

    errors: list[str] = []
    selected_cases: list[dict[str, Any]] = []
    for case_id in selected_case_ids:
        automation_kind = scoped_catalog.get(case_id)
        if automation_kind is None:
            errors.append(f"unsupported automated case for scope {automation_scope}: {case_id}")
            continue
        case = find_case(case_id)
        if case is None:
            errors.append(f"case metadata not found: {case_id}")
            continue
        selected_cases.append(
            {
                "case": case,
                "automation_kind": automation_kind,
            }
        )

    if not selected_cases and not errors:
        errors.append("automation manifest does not contain any supported cases")
    return selected_cases, errors


def preflight_errors(selected_cases: list[dict[str, Any]], compare: bool) -> list[str]:
    errors: list[str] = []
    if not RUN_CASE_SCRIPT.exists():
        errors.append(f"missing runner script: {RUN_CASE_SCRIPT}")
    if compare and any(item["automation_kind"] == "positive" for item in selected_cases):
        if not COMPARE_RESULTS_SCRIPT.exists():
            errors.append(f"missing comparison script: {COMPARE_RESULTS_SCRIPT}")
    if compare and any(item["automation_kind"] == "negative" for item in selected_cases):
        if not COMPARE_FALSE_TRIGGER_RESULTS_SCRIPT.exists():
            errors.append(
                f"missing comparison script: {COMPARE_FALSE_TRIGGER_RESULTS_SCRIPT}"
            )
    for item in selected_cases:
        case = item["case"]
        if compare:
            baseline_path = baseline_path_for(case)
            if not baseline_path.exists():
                errors.append(f"missing baseline for {case['id']}: {baseline_path}")
    return errors


def case_paths(run_date: str, case_id: str, results_dir: Path) -> dict[str, Path]:
    run_root = results_dir / run_date
    return {
        "run_root": run_root,
        "workspace_path": run_root / "workspaces" / case_id,
        "prompt_path": run_root / f"{case_id}.prompt.txt",
        "subject_output_path": run_root / f"{case_id}.subject.txt",
        "trace_path": run_root / f"{case_id}.trace.jsonl",
        "grader_prompt_path": run_root / f"{case_id}.grader.prompt.txt",
        "grader_raw_path": run_root / f"{case_id}.grader.raw.json",
        "result_path": run_root / f"{case_id}.json",
    }


def parse_comparison_status(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith("Comparison: "):
            return line.split(": ", 1)[1].strip()
    return None


def short_process_message(completed: subprocess.CompletedProcess[str], fallback: str) -> str:
    for stream in (completed.stderr, completed.stdout):
        lines = [line.strip() for line in stream.splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return fallback


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def compare_script_for_kind(automation_kind: str) -> Path:
    if automation_kind == "negative":
        return COMPARE_FALSE_TRIGGER_RESULTS_SCRIPT
    return COMPARE_RESULTS_SCRIPT


def run_case(
    case_entry: dict[str, Any],
    *,
    run_date: str,
    codex_bin: str,
    model: str | None,
    force: bool,
    dry_run: bool,
    compare: bool,
    results_dir: Path,
) -> dict[str, Any]:
    case = case_entry["case"]
    automation_kind = case_entry["automation_kind"]
    paths = case_paths(run_date, case["id"], results_dir)
    entry: dict[str, Any] = {
        "case_id": case["id"],
        "workflow": case["_workflow"],
        "automation_kind": automation_kind,
        "status": "ERROR",
        "runner_exit_code": None,
        "compare_exit_code": None,
        "result_path": str(paths["result_path"]),
        "subject_output_path": str(paths["subject_output_path"]),
        "trace_path": str(paths["trace_path"]),
        "grader_prompt_path": str(paths["grader_prompt_path"]),
        "grader_raw_path": str(paths["grader_raw_path"]),
        "prompt_path": str(paths["prompt_path"]),
        "workspace_path": str(paths["workspace_path"]),
        "baseline_path": str(baseline_path_for(case)) if compare else None,
        "outcome": None,
        "actual_trigger_behavior": None,
        "message": "",
    }

    command = [
        sys.executable,
        str(RUN_CASE_SCRIPT),
        case["id"],
        "--date",
        run_date,
        "--results-dir",
        str(results_dir),
        "--codex-bin",
        codex_bin,
    ]
    if model:
        command.extend(["--model", model])
    if force:
        command.append("--force")
    if dry_run:
        command.append("--dry-run")

    completed = subprocess.run(command, text=True, capture_output=True)
    entry["runner_exit_code"] = completed.returncode
    if completed.returncode != 0:
        entry["message"] = short_process_message(
            completed, f"run_automated_case.py exited with {completed.returncode}"
        )
        return entry

    if dry_run:
        entry["status"] = "DRY-RUN"
        entry["message"] = "blind prompt previewed; subject and grader not invoked"
        return entry

    result_path = paths["result_path"]
    if not result_path.exists():
        entry["message"] = f"missing result file: {result_path}"
        return entry

    try:
        result_payload = load_json(result_path)
    except Exception as exc:
        entry["message"] = f"failed to read result file: {exc}"
        return entry

    entry["outcome"] = result_payload.get("outcome")
    entry["actual_trigger_behavior"] = result_payload.get("actual_trigger_behavior")

    if not compare:
        entry["status"] = "RECORDED"
        if automation_kind == "negative":
            entry["message"] = (
                f"behavior={entry['actual_trigger_behavior']} outcome={entry['outcome']}"
            )
        else:
            entry["message"] = f"outcome={entry['outcome']}"
        return entry

    compare_command = [
        sys.executable,
        str(compare_script_for_kind(automation_kind)),
        "--baseline",
        str(baseline_path_for(case)),
        "--result",
        str(result_path),
    ]
    compared = subprocess.run(compare_command, text=True, capture_output=True)
    entry["compare_exit_code"] = compared.returncode

    status = parse_comparison_status(compared.stdout)
    if status is None or compared.returncode not in {0, 1}:
        entry["message"] = short_process_message(
            compared, f"compare_results.py exited with {compared.returncode}"
        )
        return entry

    entry["status"] = status
    if automation_kind == "negative":
        entry["message"] = (
            f"behavior={entry['actual_trigger_behavior']} outcome={entry['outcome']}"
        )
    else:
        entry["message"] = f"outcome={entry['outcome']}"
    return entry


def overall_exit_code(summary_entries: list[dict[str, Any]], *, dry_run: bool) -> int:
    if any(entry["status"] == "ERROR" for entry in summary_entries):
        return 3
    if any(entry["status"] == "REGRESSION" for entry in summary_entries):
        return 1
    if dry_run:
        return 0
    return 0


def build_summary(
    *,
    run_date: str,
    automation_scope: str,
    compare: bool,
    dry_run: bool,
    results_dir: Path,
    requested_case_ids: list[str],
    selected_case_ids: list[str],
    summary_entries: list[dict[str, Any]],
    exit_code: int,
    setup_errors: list[str] | None = None,
) -> dict[str, Any]:
    counts = Counter(entry["status"] for entry in summary_entries)
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "run_date": run_date,
        "automation_scope": automation_scope,
        "compare": compare,
        "dry_run": dry_run,
        "results_dir": str(results_dir),
        "requested_case_ids": requested_case_ids,
        "selected_case_ids": selected_case_ids,
        "exit_code": exit_code,
        "status_counts": dict(sorted(counts.items())),
        "setup_errors": setup_errors or [],
        "cases": summary_entries,
    }


def print_summary_lines(summary_entries: list[dict[str, Any]]) -> None:
    for entry in summary_entries:
        message = entry["message"]
        if message:
            print(f"{entry['case_id']} {entry['status']} {message}")
        else:
            print(f"{entry['case_id']} {entry['status']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supported automated eval cases in batch.")
    parser.add_argument(
        "case_ids",
        nargs="*",
        help="Optional subset of supported automated case ids. Default: run all supported cases.",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--negative",
        action="store_true",
        help="Run only the supported automated negative false-trigger cases.",
    )
    scope.add_argument(
        "--all",
        action="store_true",
        help="Run both the supported positive and supported negative automated cases.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        dest="run_date",
        help="Result directory date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--codex-bin",
        default="codex",
        help="Codex CLI binary to invoke.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override passed to codex exec.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing run artifacts for the same case/date.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stage prompts for each case without invoking codex exec.",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Skip baseline comparison after each successful case run.",
    )
    parser.add_argument(
        "--summary-file",
        default=None,
        help="Optional path for the machine-readable batch summary JSON.",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Optional override for the results root directory. Default: ~/.codex/evals/results",
    )
    args = parser.parse_args()
    try:
        args.run_date = validate_run_date(args.run_date)
    except ValueError as exc:
        parser.error(str(exc))

    automation_scope = "all" if args.all else "negative" if args.negative else "positive"
    compare = not args.no_compare and not args.dry_run
    results_dir = resolve_results_dir(args.results_dir)
    summary_path = (
        Path(args.summary_file).expanduser()
        if args.summary_file
        else default_summary_path(args.run_date, automation_scope, results_dir)
    )

    selected_cases, selection_errors = resolve_selected_cases(args.case_ids, automation_scope)
    setup_errors = selection_errors + preflight_errors(selected_cases, compare)
    if setup_errors:
        summary = build_summary(
            run_date=args.run_date,
            automation_scope=automation_scope,
            compare=compare,
            dry_run=args.dry_run,
            results_dir=results_dir,
            requested_case_ids=args.case_ids,
            selected_case_ids=[item["case"]["id"] for item in selected_cases],
            summary_entries=[],
            exit_code=2,
            setup_errors=setup_errors,
        )
        write_summary(summary_path, summary)
        for error in setup_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"summary_file={summary_path}")
        return 2

    summary_entries = [
        run_case(
            case,
            run_date=args.run_date,
            codex_bin=args.codex_bin,
            model=args.model,
            force=args.force,
            dry_run=args.dry_run,
            compare=compare,
            results_dir=results_dir,
        )
        for case in selected_cases
    ]
    exit_code = overall_exit_code(summary_entries, dry_run=args.dry_run)
    summary = build_summary(
        run_date=args.run_date,
        automation_scope=automation_scope,
        compare=compare,
        dry_run=args.dry_run,
        results_dir=results_dir,
        requested_case_ids=args.case_ids,
        selected_case_ids=[item["case"]["id"] for item in selected_cases],
        summary_entries=summary_entries,
        exit_code=exit_code,
    )
    write_summary(summary_path, summary)
    print_summary_lines(summary_entries)
    print(f"summary_file={summary_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
