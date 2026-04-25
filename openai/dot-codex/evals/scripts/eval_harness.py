#!/usr/bin/env python3
"""
Lightweight local harness for Codex workflow evals.

Features:
- validate case file structure
- validate fixture references and baseline result records
- validate automation support metadata
- list workflows and case ids
- list auto-runnable cases
- show one case in a readable form
- print a blank result template for one case
- scaffold a result record into results/
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "cases"
FIXTURE_MANIFEST_PATH = ROOT / "fixtures" / "manifest.json"
AUTOMATION_MANIFEST_PATH = ROOT / "automation" / "manifest.json"
BASELINES_DIR = ROOT / "baselines"
RESULTS_DIR = ROOT / "results"

REQUIRED_FILE_KEYS = {"schema_version", "workflow", "cases"}
REQUIRED_CASE_KEYS = {
    "id",
    "title",
    "mode",
    "trigger_expectation",
    "goal",
    "setup",
    "prompt",
    "expected_output_shape",
    "expected_safety_behavior",
    "expected_validation_behavior",
    "pass_criteria",
    "fail_signals",
}
REQUIRED_RESULT_KEYS = {
    "schema_version",
    "case_id",
    "workflow",
    "run_timestamp",
    "outcome",
    "observed_subagents",
    "observed_validation",
    "observed_fail_signals",
    "notes",
}
REQUIRED_FALSE_TRIGGER_RESULT_KEYS = {
    "schema_version",
    "case_id",
    "workflow",
    "run_timestamp",
    "expected_should_trigger",
    "actual_trigger_behavior",
    "outcome",
    "unexpected_subagents",
    "unexpected_validation",
    "fail_signals",
    "notes",
    "rubric",
}
OUTCOMES = {"pass", "partial", "fail"}
RUBRIC_KEYS = {
    "trigger_match",
    "output_shape_ok",
    "safety_ok",
    "validation_ok",
}
FALSE_TRIGGER_BEHAVIORS = {
    "not_triggered",
    "secondary_only",
    "partial_trigger",
    "primary_trigger",
}
FALSE_TRIGGER_RUBRIC_KEYS = {
    "trigger_match",
    "output_shape_ok",
    "task_focus_ok",
    "safety_ok",
}


def resolve_results_dir(results_dir: str | Path | None = None) -> Path:
    if results_dir is None:
        return RESULTS_DIR
    if isinstance(results_dir, Path):
        return results_dir.expanduser()
    return Path(results_dir).expanduser()


def load_json(path: Path) -> Any:
    with path.open() as fh:
        return json.load(fh)


def load_case_files() -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in sorted(CASES_DIR.glob("*.json")):
        data = load_json(path)
        data["_path"] = str(path)
        payloads.append(data)
    return payloads


def load_fixture_catalog() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = load_json(FIXTURE_MANIFEST_PATH)
    fixtures = payload.get("fixtures", [])
    catalog = {
        item["id"]: item
        for item in fixtures
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    return payload, catalog


def load_automation_manifest(kind: str = "positive") -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = load_json(AUTOMATION_MANIFEST_PATH)
    if kind == "positive":
        supported_cases = payload.get("supported_cases", [])
    elif kind == "negative":
        supported_cases = payload.get("supported_negative_cases", [])
    else:
        raise ValueError(f"Unknown automation manifest kind: {kind}")
    catalog = {
        item["case_id"]: item
        for item in supported_cases
        if isinstance(item, dict) and isinstance(item.get("case_id"), str)
    }
    return payload, catalog


def validate_fixture_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1":
        errors.append("schema_version must be '1'")

    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        errors.append("fixtures must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict):
            errors.append(f"fixture[{index}] must be an object")
            continue
        for key in ("id", "kind", "path", "workflows", "entrypoints", "description"):
            if key not in fixture:
                errors.append(f"fixture[{index}] missing key: {key}")
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str):
            errors.append(f"fixture[{index}] id must be a string")
        elif fixture_id in seen_ids:
            errors.append(f"fixture[{index}] duplicate id: {fixture_id}")
        else:
            seen_ids.add(fixture_id)
        fixture_path = fixture.get("path")
        if isinstance(fixture_path, str):
            abs_path = ROOT / fixture_path
            if not abs_path.exists():
                errors.append(f"fixture[{index}] missing path: {abs_path}")
        else:
            errors.append(f"fixture[{index}] path must be a string")
        for list_key in ("workflows", "entrypoints"):
            value = fixture.get(list_key)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) for item in value
            ):
                errors.append(f"fixture[{index}] {list_key} must be a non-empty string list")
    return errors


def validate_automation_manifest(
    payload: dict[str, Any], case_index: dict[str, dict[str, Any]], *, kind: str = "positive"
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "2":
        errors.append("schema_version must be '2'")

    if kind == "positive":
        supported_cases = payload.get("supported_cases")
    elif kind == "negative":
        supported_cases = payload.get("supported_negative_cases")
    else:
        raise ValueError(f"Unknown automation manifest kind: {kind}")

    if not isinstance(supported_cases, list) or not supported_cases:
        section_name = "supported_cases" if kind == "positive" else "supported_negative_cases"
        errors.append(f"{section_name} must be a non-empty list")
        return errors

    seen_case_ids: set[str] = set()
    for index, item in enumerate(supported_cases):
        if not isinstance(item, dict):
            section_name = "supported_cases" if kind == "positive" else "supported_negative_cases"
            errors.append(f"{section_name}[{index}] must be an object")
            continue
        required_keys = ("case_id", "mode", "task_file") if kind == "positive" else ("case_id", "mode")
        section_name = "supported_cases" if kind == "positive" else "supported_negative_cases"
        for key in required_keys:
            if key not in item:
                errors.append(f"{section_name}[{index}] missing key: {key}")
        case_id = item.get("case_id")
        if not isinstance(case_id, str):
            errors.append(f"{section_name}[{index}] case_id must be a string")
            continue
        if case_id in seen_case_ids:
            errors.append(f"{section_name}[{index}] duplicate case_id: {case_id}")
            continue
        seen_case_ids.add(case_id)
        case = case_index.get(case_id)
        if case is None:
            errors.append(f"{section_name}[{index}] unknown case_id: {case_id}")
            continue
        mode = item.get("mode")
        if kind == "positive":
            if case.get("trigger_expectation") != "should_trigger":
                errors.append(f"supported_cases[{index}] must reference a positive case")
            if not case.get("fixture_ref"):
                errors.append(f"supported_cases[{index}] must reference a fixture-backed case")
            if mode not in {"patch-eval", "repo-bugfix"}:
                errors.append(
                    f"supported_cases[{index}] mode must be patch-eval or repo-bugfix"
                )

            fixture = None
            if case.get("fixture_ref"):
                _, fixture_catalog = load_fixture_catalog()
                fixture = fixture_catalog.get(case["fixture_ref"])
            task_file = item.get("task_file")
            if not isinstance(task_file, str):
                errors.append(f"supported_cases[{index}] task_file must be a string")
            elif fixture is not None:
                task_path = ROOT / fixture["path"] / task_file
                if not task_path.exists():
                    errors.append(f"supported_cases[{index}] missing task file: {task_path}")

            patch_file = item.get("patch_file")
            if mode == "patch-eval":
                if not isinstance(patch_file, str):
                    errors.append(f"supported_cases[{index}] patch-eval entries need patch_file")
                elif fixture is not None:
                    patch_path = ROOT / fixture["path"] / patch_file
                    if not patch_path.exists():
                        errors.append(f"supported_cases[{index}] missing patch file: {patch_path}")
            elif patch_file is not None and not isinstance(patch_file, str):
                errors.append(f"supported_cases[{index}] patch_file must be a string when provided")
        else:
            if case.get("trigger_expectation") != "should_not_trigger":
                errors.append(
                    f"supported_negative_cases[{index}] must reference a should_not_trigger case"
                )
            if mode not in {"prompt-only", "patch-eval"}:
                errors.append(
                    f"supported_negative_cases[{index}] mode must be prompt-only or patch-eval"
                )
                continue

            fixture = None
            if case.get("fixture_ref"):
                _, fixture_catalog = load_fixture_catalog()
                fixture = fixture_catalog.get(case["fixture_ref"])

            task_file = item.get("task_file")
            patch_file = item.get("patch_file")
            if mode == "prompt-only":
                if task_file is not None and not isinstance(task_file, str):
                    errors.append(f"supported_negative_cases[{index}] task_file must be a string when provided")
                if patch_file is not None and not isinstance(patch_file, str):
                    errors.append(f"supported_negative_cases[{index}] patch_file must be a string when provided")
            elif mode == "patch-eval":
                if not case.get("fixture_ref"):
                    errors.append(
                        f"supported_negative_cases[{index}] patch-eval entries must reference a fixture-backed case"
                    )
                if not isinstance(task_file, str):
                    errors.append(
                        f"supported_negative_cases[{index}] patch-eval entries need task_file"
                    )
                elif fixture is not None:
                    task_path = ROOT / fixture["path"] / task_file
                    if not task_path.exists():
                        errors.append(f"supported_negative_cases[{index}] missing task file: {task_path}")
                if not isinstance(patch_file, str):
                    errors.append(
                        f"supported_negative_cases[{index}] patch-eval entries need patch_file"
                    )
                elif fixture is not None:
                    patch_path = ROOT / fixture["path"] / patch_file
                    if not patch_path.exists():
                        errors.append(f"supported_negative_cases[{index}] missing patch file: {patch_path}")
    return errors


def validate_payload(
    payload: dict[str, Any], fixture_catalog: dict[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    missing_file_keys = REQUIRED_FILE_KEYS - set(payload.keys())
    if missing_file_keys:
        errors.append(f"missing file keys: {sorted(missing_file_keys)}")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return errors

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case[{index}] must be an object")
            continue
        missing_case_keys = REQUIRED_CASE_KEYS - set(case.keys())
        if missing_case_keys:
            errors.append(
                f"case[{index}] missing keys: {sorted(missing_case_keys)}"
            )
        for key in (
            "expected_output_shape",
            "expected_safety_behavior",
            "expected_validation_behavior",
            "pass_criteria",
            "fail_signals",
        ):
            value = case.get(key)
            if not isinstance(value, list) or not value:
                errors.append(f"case[{index}] {key} must be a non-empty list")
        if case.get("mode") not in {"skill", "subagent"}:
            errors.append(f"case[{index}] mode must be skill or subagent")
        if case.get("trigger_expectation") not in {"should_trigger", "should_not_trigger"}:
            errors.append(
                f"case[{index}] trigger_expectation must be should_trigger or should_not_trigger"
            )
        tier = case.get("tier")
        if tier is not None and tier not in {"EASY", "MEDIUM", "HARD"}:
            errors.append(f"case[{index}] tier must be EASY, MEDIUM, or HARD")
        why_this_tier = case.get("why_this_tier")
        if why_this_tier is not None and not isinstance(why_this_tier, str):
            errors.append(f"case[{index}] why_this_tier must be a string")
        workflows_under_test = case.get("workflows_under_test")
        if workflows_under_test is not None:
            if not isinstance(workflows_under_test, list) or not workflows_under_test or not all(
                isinstance(item, str) for item in workflows_under_test
            ):
                errors.append(
                    f"case[{index}] workflows_under_test must be a non-empty string list"
                )
        fixture_ref = case.get("fixture_ref")
        if fixture_ref is not None:
            if not isinstance(fixture_ref, str):
                errors.append(f"case[{index}] fixture_ref must be a string")
            elif fixture_ref not in fixture_catalog:
                errors.append(f"case[{index}] fixture_ref not found: {fixture_ref}")
    return errors


def iter_cases(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for payload in payloads:
        for case in payload["cases"]:
            item = dict(case)
            item["_workflow"] = payload["workflow"]
            item["_path"] = payload["_path"]
            flat.append(item)
    return flat


def case_index(payloads: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    payloads = payloads or load_case_files()
    return {case["id"]: case for case in iter_cases(payloads)}


def find_case(case_id: str) -> dict[str, Any] | None:
    for case in iter_cases(load_case_files()):
        if case["id"] == case_id:
            return case
    return None


def baseline_path_for(case: dict[str, Any]) -> Path:
    return BASELINES_DIR / case["_workflow"] / f"{case['id']}.json"


def validate_result_record(
    payload: dict[str, Any],
    *,
    expected_case_id: str | None = None,
    expected_workflow: str | None = None,
) -> list[str]:
    errors: list[str] = []
    missing_result_keys = REQUIRED_RESULT_KEYS - set(payload.keys())
    if missing_result_keys:
        errors.append(f"missing result keys: {sorted(missing_result_keys)}")

    if expected_case_id is not None and payload.get("case_id") != expected_case_id:
        errors.append(
            f"case_id mismatch: expected {expected_case_id}, got {payload.get('case_id')}"
        )
    if expected_workflow is not None and payload.get("workflow") != expected_workflow:
        errors.append(
            f"workflow mismatch: expected {expected_workflow}, got {payload.get('workflow')}"
        )

    if payload.get("outcome") not in OUTCOMES:
        errors.append("outcome must be pass, partial, or fail")

    for key in ("observed_subagents", "observed_validation", "observed_fail_signals"):
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{key} must be a string list")

    if not isinstance(payload.get("notes"), str):
        errors.append("notes must be a string")

    fixture_ref = payload.get("fixture_ref")
    if fixture_ref is not None and not isinstance(fixture_ref, str):
        errors.append("fixture_ref must be a string when provided")

    rubric = payload.get("rubric")
    if rubric is not None:
        if not isinstance(rubric, dict):
            errors.append("rubric must be an object when provided")
        else:
            unknown_rubric_keys = set(rubric.keys()) - RUBRIC_KEYS
            if unknown_rubric_keys:
                errors.append(f"unknown rubric keys: {sorted(unknown_rubric_keys)}")
            for key, value in rubric.items():
                if value is not None and not isinstance(value, bool):
                    errors.append(f"rubric.{key} must be a boolean or null")
    return errors


def validate_false_trigger_record(
    payload: dict[str, Any],
    *,
    expected_case_id: str | None = None,
    expected_workflow: str | None = None,
) -> list[str]:
    errors: list[str] = []
    missing_result_keys = REQUIRED_FALSE_TRIGGER_RESULT_KEYS - set(payload.keys())
    if missing_result_keys:
        errors.append(f"missing false-trigger result keys: {sorted(missing_result_keys)}")

    if expected_case_id is not None and payload.get("case_id") != expected_case_id:
        errors.append(
            f"case_id mismatch: expected {expected_case_id}, got {payload.get('case_id')}"
        )
    if expected_workflow is not None and payload.get("workflow") != expected_workflow:
        errors.append(
            f"workflow mismatch: expected {expected_workflow}, got {payload.get('workflow')}"
        )

    if not isinstance(payload.get("expected_should_trigger"), bool):
        errors.append("expected_should_trigger must be a boolean")

    if payload.get("actual_trigger_behavior") not in FALSE_TRIGGER_BEHAVIORS:
        errors.append(
            "actual_trigger_behavior must be one of: "
            + ", ".join(sorted(FALSE_TRIGGER_BEHAVIORS))
        )

    if payload.get("outcome") not in OUTCOMES:
        errors.append("outcome must be pass, partial, or fail")

    for key in ("unexpected_subagents", "unexpected_validation", "fail_signals"):
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{key} must be a string list")

    if not isinstance(payload.get("notes"), str):
        errors.append("notes must be a string")

    fixture_ref = payload.get("fixture_ref")
    if fixture_ref is not None and not isinstance(fixture_ref, str):
        errors.append("fixture_ref must be a string when provided")

    rubric = payload.get("rubric")
    if not isinstance(rubric, dict):
        errors.append("rubric must be an object")
    else:
        unknown_rubric_keys = set(rubric.keys()) - FALSE_TRIGGER_RUBRIC_KEYS
        if unknown_rubric_keys:
            errors.append(f"unknown false-trigger rubric keys: {sorted(unknown_rubric_keys)}")
        missing_rubric_keys = FALSE_TRIGGER_RUBRIC_KEYS - set(rubric.keys())
        if missing_rubric_keys:
            errors.append(f"missing false-trigger rubric keys: {sorted(missing_rubric_keys)}")
        for key, value in rubric.items():
            if value is not None and not isinstance(value, bool):
                errors.append(f"rubric.{key} must be a boolean or null")
    return errors


def render_result_template(case: dict[str, Any], *, run_date: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "2",
        "case_id": case["id"],
        "workflow": case["_workflow"],
        "run_timestamp": f"{run_date or 'YYYY-MM-DD'}T00:00:00Z",
        "outcome": "pass",
        "observed_subagents": [],
        "observed_validation": [],
        "observed_fail_signals": [],
        "notes": "",
        "rubric": {
            "trigger_match": None,
            "output_shape_ok": None,
            "safety_ok": None,
            "validation_ok": None,
        },
    }
    if case.get("fixture_ref"):
        result["fixture_ref"] = case["fixture_ref"]
    return result


def render_false_trigger_template(
    case: dict[str, Any], *, run_date: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "1",
        "case_id": case["id"],
        "workflow": case["_workflow"],
        "run_timestamp": f"{run_date or 'YYYY-MM-DD'}T00:00:00Z",
        "expected_should_trigger": False,
        "actual_trigger_behavior": "not_triggered",
        "outcome": "pass",
        "unexpected_subagents": [],
        "unexpected_validation": [],
        "fail_signals": [],
        "notes": "",
        "rubric": {
            "trigger_match": None,
            "output_shape_ok": None,
            "task_focus_ok": None,
            "safety_ok": None,
        },
    }
    if case.get("fixture_ref"):
        result["fixture_ref"] = case["fixture_ref"]
    return result


def render_template_for_case(
    case: dict[str, Any], *, run_date: str | None = None
) -> dict[str, Any]:
    if case.get("trigger_expectation") == "should_not_trigger":
        return render_false_trigger_template(case, run_date=run_date)
    return render_result_template(case, run_date=run_date)


def cmd_validate() -> int:
    manifest_payload, fixture_catalog = load_fixture_catalog()
    manifest_errors = validate_fixture_manifest(manifest_payload)
    had_errors = False
    if manifest_errors:
        had_errors = True
        print(str(FIXTURE_MANIFEST_PATH))
        for error in manifest_errors:
            print(f"  ERROR: {error}")
    else:
        print(f"{FIXTURE_MANIFEST_PATH}: OK")

    payloads = load_case_files()
    indexed_cases = case_index(payloads)
    for payload in payloads:
        errors = validate_payload(payload, fixture_catalog)
        if errors:
            had_errors = True
            print(payload["_path"])
            for error in errors:
                print(f"  ERROR: {error}")
        else:
            print(f"{payload['_path']}: OK")

    automation_payload, automation_catalog = load_automation_manifest()
    _, negative_automation_catalog = load_automation_manifest(kind="negative")
    automation_errors = validate_automation_manifest(
        automation_payload,
        indexed_cases,
        kind="positive",
    )
    automation_errors.extend(
        validate_automation_manifest(
            automation_payload,
            indexed_cases,
            kind="negative",
        )
    )
    if automation_errors:
        had_errors = True
        print(f"{AUTOMATION_MANIFEST_PATH}")
        for error in automation_errors:
            print(f"  ERROR: {error}")
    else:
        print(f"{AUTOMATION_MANIFEST_PATH}: OK")

    for case in iter_cases(payloads):
        if case.get("trigger_expectation") != "should_trigger":
            continue
        fixture_ref = case.get("fixture_ref")
        if not fixture_ref:
            continue
        baseline_path = baseline_path_for(case)
        if not baseline_path.exists():
            had_errors = True
            print(f"{baseline_path}")
            print("  ERROR: missing baseline for fixture-backed case")
            continue
        baseline_payload = load_json(baseline_path)
        errors = validate_result_record(
            baseline_payload,
            expected_case_id=case["id"],
            expected_workflow=case["_workflow"],
        )
        if baseline_payload.get("fixture_ref") != fixture_ref:
            errors.append(
                f"fixture_ref mismatch: expected {fixture_ref}, got {baseline_payload.get('fixture_ref')}"
            )
        if errors:
            had_errors = True
            print(f"{baseline_path}")
            for error in errors:
                print(f"  ERROR: {error}")
        else:
            print(f"{baseline_path}: OK")

    for case_id in negative_automation_catalog:
        case = indexed_cases[case_id]
        baseline_path = baseline_path_for(case)
        if not baseline_path.exists():
            had_errors = True
            print(f"{baseline_path}")
            print("  ERROR: missing false-trigger baseline for automated negative case")
            continue
        baseline_payload = load_json(baseline_path)
        errors = validate_false_trigger_record(
            baseline_payload,
            expected_case_id=case["id"],
            expected_workflow=case["_workflow"],
        )
        if case.get("fixture_ref") and baseline_payload.get("fixture_ref") != case.get("fixture_ref"):
            errors.append(
                f"fixture_ref mismatch: expected {case.get('fixture_ref')}, got {baseline_payload.get('fixture_ref')}"
            )
        if baseline_payload.get("expected_should_trigger") is not False:
            errors.append("expected_should_trigger must be false for automated negative cases")
        if errors:
            had_errors = True
            print(f"{baseline_path}")
            for error in errors:
                print(f"  ERROR: {error}")
        else:
            print(f"{baseline_path}: OK")
    return 1 if had_errors else 0


def cmd_list() -> int:
    _, automation_catalog = load_automation_manifest()
    _, negative_automation_catalog = load_automation_manifest(kind="negative")
    for payload in load_case_files():
        print(f"{payload['workflow']} ({payload['_path']})")
        for case in payload["cases"]:
            details = [case["trigger_expectation"]]
            if case.get("tier"):
                details.insert(0, f"tier={case['tier']}")
            if case.get("fixture_ref"):
                details.append(f"fixture={case['fixture_ref']}")
            if case["id"] in automation_catalog:
                details.append("auto")
            if case["id"] in negative_automation_catalog:
                details.append("auto-negative")
            print(f"  - {case['id']}: {case['title']} [{' | '.join(details)}]")
    return 0


def cmd_list_auto() -> int:
    _, automation_catalog = load_automation_manifest()
    indexed_cases = case_index()
    for case_id, automation in automation_catalog.items():
        case = indexed_cases[case_id]
        print(
            f"{case_id}: {case['_workflow']} [{automation['mode']}] "
            f"(fixture={case.get('fixture_ref')})"
        )
    return 0


def cmd_list_auto_negative() -> int:
    _, automation_catalog = load_automation_manifest(kind="negative")
    indexed_cases = case_index()
    for case_id, automation in automation_catalog.items():
        case = indexed_cases[case_id]
        print(
            f"{case_id}: {case['_workflow']} [{automation['mode']}] "
            f"(trigger={case['trigger_expectation']})"
        )
    return 0


def cmd_show(case_id: str) -> int:
    case = find_case(case_id)
    if not case:
        print(f"Case not found: {case_id}", file=sys.stderr)
        return 1
    view = dict(case)
    if case.get("fixture_ref"):
        _, fixture_catalog = load_fixture_catalog()
        fixture = fixture_catalog[case["fixture_ref"]]
        view["fixture"] = dict(fixture)
        view["fixture"]["absolute_path"] = str(ROOT / fixture["path"])
        view["baseline_path"] = str(baseline_path_for(case))
    _, automation_catalog = load_automation_manifest()
    _, negative_automation_catalog = load_automation_manifest(kind="negative")
    if case_id in automation_catalog:
        view["automation"] = automation_catalog[case_id]
    if case_id in negative_automation_catalog:
        view["negative_automation"] = negative_automation_catalog[case_id]
    print(json.dumps(view, indent=2))
    return 0


def cmd_template(case_id: str) -> int:
    case = find_case(case_id)
    if not case:
        print(f"Case not found: {case_id}", file=sys.stderr)
        return 1
    print(json.dumps(render_template_for_case(case), indent=2))
    return 0


def cmd_scaffold_result(
    case_id: str, run_date: str, force: bool, results_dir: str | None
) -> int:
    case = find_case(case_id)
    if not case:
        print(f"Case not found: {case_id}", file=sys.stderr)
        return 1
    output_path = resolve_results_dir(results_dir) / run_date / f"{case_id}.json"
    if output_path.exists() and not force:
        print(f"Result already exists: {output_path}", file=sys.stderr)
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = render_template_for_case(case, run_date=run_date)
    with output_path.open("w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(output_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local harness for Codex workflow evals.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    sub.add_parser("list")
    sub.add_parser("list-auto")
    sub.add_parser("list-auto-negative")
    show = sub.add_parser("show")
    show.add_argument("case_id")
    template = sub.add_parser("template")
    template.add_argument("case_id")
    scaffold = sub.add_parser("scaffold-result")
    scaffold.add_argument("case_id")
    scaffold.add_argument(
        "--date",
        default=date.today().isoformat(),
        dest="run_date",
        help="Result directory date in YYYY-MM-DD format.",
    )
    scaffold.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing result file for the same case/date.",
    )
    scaffold.add_argument(
        "--results-dir",
        default=None,
        help="Optional override for the results root directory. Default: ~/.codex/evals/results",
    )
    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate()
    if args.command == "list":
        return cmd_list()
    if args.command == "list-auto":
        return cmd_list_auto()
    if args.command == "list-auto-negative":
        return cmd_list_auto_negative()
    if args.command == "show":
        return cmd_show(args.case_id)
    if args.command == "template":
        return cmd_template(args.case_id)
    if args.command == "scaffold-result":
        return cmd_scaffold_result(
            args.case_id,
            args.run_date,
            args.force,
            args.results_dir,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
