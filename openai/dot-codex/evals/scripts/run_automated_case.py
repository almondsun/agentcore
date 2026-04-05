#!/usr/bin/env python3
"""
Run a small supported subset of automated eval cases via `codex exec`.

The runner is intentionally narrow:
- supports a few positive fixture-backed cases
- supports a few prompt-only or fixture-backed negative false-trigger cases
- stages each run into a disposable workspace
- uses `--output-schema` for a structured final message
- writes a comparable result record plus raw final-message JSON
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from eval_harness import (
    AUTOMATION_MANIFEST_PATH,
    ROOT,
    find_case,
    load_automation_manifest,
    load_fixture_catalog,
    resolve_results_dir,
    validate_false_trigger_record,
    validate_result_record,
)

OUTPUT_SCHEMA_PATH = ROOT / "schema" / "codex-run-output.schema.json"
FALSE_TRIGGER_OUTPUT_SCHEMA_PATH = ROOT / "schema" / "codex-false-trigger-output.schema.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_text(path: Path) -> str:
    return path.read_text()


def build_codex_exec_env() -> dict[str, str]:
    env = os.environ.copy()
    python_bin_dir = str(Path(sys.executable).resolve().parent)
    current_path = env.get("PATH", "")
    path_parts = [part for part in current_path.split(os.pathsep) if part]
    if python_bin_dir in path_parts:
        path_parts = [part for part in path_parts if part != python_bin_dir]
    path_parts.insert(0, python_bin_dir)
    env["PATH"] = os.pathsep.join(path_parts)
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        env["VIRTUAL_ENV"] = sys.prefix
    return env


def gather_runtime_facts(workspace: Path) -> dict[str, str]:
    env = build_codex_exec_env()
    python_version = subprocess.run(
        [sys.executable, "--version"],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    pytest_version = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "python_executable": sys.executable,
        "python_version": (python_version.stdout or python_version.stderr).strip(),
        "pytest_version": (pytest_version.stdout or pytest_version.stderr).strip(),
        "path": env.get("PATH", ""),
    }


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def normalize_observed_validation(
    case: dict[str, Any], values: list[str], notes: str = ""
) -> list[str]:
    values = dedupe_preserve_order(values)
    if case.get("_workflow") != "workflow-realism":
        return values

    case_id = case["id"]
    present = set(values)
    notes_lower = notes.lower()
    normalized: list[str] = []

    def add(token: str) -> None:
        if token not in normalized:
            normalized.append(token)

    if case_id == "wr-easy-local-bugfix":
        if "context:repo-inspected" in present:
            add("context:repo-inspected")
        if "context:repo-inspected" not in normalized and (
            "inspected the repo first" in notes_lower
            or "inspected task.md" in notes_lower
            or "inspected the repo" in notes_lower
        ):
            add("context:repo-inspected")
        if present & {
            "implementation:main-agent",
            "impl:main-agent",
            "edit:local-fix",
            "edit:local-module-fix",
            "command:pytest-file",
            "command:venv-python-pytest",
            "command:pytest-tests/test_validation.py",
            "target:tests-test_validation",
            "result:4-passed",
        }:
            add("implementation:main-agent")
        if "implementation:main-agent" not in normalized and (
            "kept the implementation local" in notes_lower
            or "fixed blank or whitespace-only retry delays" in notes_lower
            or "local to `src/tiny_easy/validation.py`" in notes_lower
            or "fixed parse_retry_delay()" in notes_lower
            or "added a focused regression test" in notes_lower
        ):
            add("implementation:main-agent")
        if present & {
            "validation-skill:build-validate",
            "skill:build-validate",
            "command:pytest-file",
            "command:venv-python-pytest",
            "command:pytest-tests/test_validation.py",
            "target:tests-test_validation",
            "command:pytest",
            "result:4-passed",
        }:
            add("validation-skill:build-validate")
        if present & {
            "command:pytest-tests/test_validation.py",
            "command:pytest-file",
            "command:venv-python-pytest",
            "target:tests-test_validation",
            "command:pytest",
        }:
            add("command:pytest-tests/test_validation.py")
        if "validation-skill:build-validate" not in normalized and (
            "build-validate" in notes_lower
            or "canonical pytest command" in notes_lower
            or "smallest correct validation path" in notes_lower
        ):
            add("validation-skill:build-validate")
        if "command:pytest-tests/test_validation.py" not in normalized and (
            "python -m pytest tests/test_validation.py" in notes_lower
            or "pytest tests/test_validation.py" in notes_lower
            or ("tests/test_validation.py" in notes_lower and "pass" in notes_lower)
        ):
            add("command:pytest-tests/test_validation.py")
        return normalized or values

    if case_id == "wr-medium-api-contract":
        if "context:repo-inspected" in present:
            add("context:repo-inspected")
        if "implementation:main-agent" in present:
            add("implementation:main-agent")
        if present & {"validation-skill:build-validate", "skill:build-validate"}:
            add("validation-skill:build-validate")
        if "validation-skill:build-validate" not in normalized and (
            "python -m pytest successfully" in notes_lower
            or "ran /home/marti/.venvs/codex-evals/bin/python -m pytest successfully" in notes_lower
            or "broader validation" in notes_lower
        ):
            add("validation-skill:build-validate")
        if present & {"command:pytest", "command:python-pytest"}:
            add("command:pytest")
        if present & {"compatibility:called-out", "compat:api-cli-contract"}:
            add("compatibility:called-out")
        if "compatibility:called-out" not in normalized and (
            "compatibility-sensitive impact was called out" in notes_lower
            or "compatibility impact was called out" in notes_lower
            or "compatibility-sensitive impact was explicit" in notes_lower
            or "public api response shape changed" in notes_lower
            or ("status_code/display_status" in notes_lower and "instead of status" in notes_lower)
        ):
            add("compatibility:called-out")
        if normalized:
            for token in values:
                if token in {
                    "context:repo-inspected",
                    "implementation:main-agent",
                    "validation-skill:build-validate",
                    "command:pytest",
                    "compatibility:called-out",
                }:
                    add(token)
            return dedupe_preserve_order(normalized)
        return values

    if case_id == "wr-hard-security-audit":
        if "context:repo-inspected" in present:
            add("context:repo-inspected")
        if "implementation:main-agent" in present or (
            "kept implementation in the main agent" in notes_lower
            or "implemented the parser/path/subprocess/log hardening in the main agent"
            in notes_lower
            or "parser and runner hardening was implemented in the main agent"
            in notes_lower
        ):
            add("implementation:main-agent")
        if present & {"validation-skill:build-validate", "skill:build-validate"}:
            add("validation-skill:build-validate")
        if "validation-skill:build-validate" not in normalized and (
            "python -m pytest" in notes_lower
            or "10 passing tests" in notes_lower
            or "smallest justified change" in notes_lower
            or "ran pytest with hostile-input and subprocess-safety coverage" in notes_lower
        ):
            add("validation-skill:build-validate")
        if present & {"command:pytest", "cmd:python-pytest", "validation:pytest"}:
            add("command:pytest")
        if "command:pytest" not in normalized and (
            "ran pytest" in notes_lower or "`python -m pytest` passed" in notes_lower
        ):
            add("command:pytest")
        if present & {"audit:security-post-change", "audit:security", "audit:security-review"}:
            add("audit:security-post-change")
        if "audit:security-post-change" not in normalized and (
            "performed a justified post-change security audit" in notes_lower
            or "security audit with security-auditor" in notes_lower
            or "handed off to `security-auditor`" in notes_lower
            or "security-auditor` review was performed" in notes_lower
        ):
            add("audit:security-post-change")
        if "uncertainty:integration-called-out" not in normalized and (
            "real external `sync-tool` integration remains unverified" in notes_lower
            or "real `sync-tool` integration remains unverified" in notes_lower
            or "integration remains unverified" in notes_lower
            or "residual risk" in notes_lower
            or "residual uncertainty" in notes_lower
            or "real sync-tool integration" in notes_lower
        ):
            add("uncertainty:integration-called-out")
        return normalized or values

    return values


def stage_workspace(source: Path, destination: Path, force: bool) -> None:
    if destination.exists():
        if not force:
            raise FileExistsError(f"Workspace already exists: {destination}")
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def prepare_empty_workspace(destination: Path, force: bool) -> None:
    if destination.exists():
        if not force:
            raise FileExistsError(f"Workspace already exists: {destination}")
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)


def build_prompt(
    case: dict[str, Any],
    automation: dict[str, Any],
    workspace: Path,
    runtime_facts: dict[str, str] | None = None,
) -> str:
    fixture_ref = case["fixture_ref"]
    _, fixture_catalog = load_fixture_catalog()
    fixture = fixture_catalog[fixture_ref]
    fixture_root = ROOT / fixture["path"]

    task_path = fixture_root / automation["task_file"]
    task_text = load_text(task_path).strip()

    prompt_lines = [
        "You are running one local Codex eval harness case.",
        "Return only one JSON object that matches the provided output schema.",
        "Do not wrap the JSON in markdown fences.",
        "Use short stable tokens in observed_subagents, observed_validation, and observed_fail_signals.",
        "Use outcome=pass only when the case contract is satisfied; use partial or fail otherwise.",
        "",
        f"case_id: {case['id']}",
        f"workflow: {case['_workflow']}",
        f"fixture_ref: {fixture_ref}",
        f"workspace_root: {workspace}",
        "",
        *(
            [
                "Runtime facts gathered by the runner before this Codex session:",
                json.dumps(runtime_facts, indent=2),
                "",
            ]
            if runtime_facts is not None
            else []
        ),
        "Case JSON:",
        json.dumps(
            {
                "id": case["id"],
                "workflow": case["_workflow"],
                "title": case["title"],
                "goal": case["goal"],
                "setup": case["setup"],
                "prompt": case["prompt"],
                "expected_subagents": case.get("expected_subagents", []),
                "forbidden_subagents": case.get("forbidden_subagents", []),
                "expected_output_shape": case["expected_output_shape"],
                "expected_safety_behavior": case["expected_safety_behavior"],
                "expected_validation_behavior": case["expected_validation_behavior"],
                "pass_criteria": case["pass_criteria"],
                "fail_signals": case["fail_signals"],
            },
            indent=2,
        ),
        "",
        f"Fixture task file: {automation['task_file']}",
        task_text,
        "",
    ]

    mode = automation["mode"]
    if mode == "patch-eval":
        patch_path = fixture_root / automation["patch_file"]
        patch_text = load_text(patch_path).strip()
        if case["mode"] == "subagent":
            instruction_lines = [
                "- Treat the patch text above as the only changed surface under evaluation.",
                "- Read the task file and patch before answering.",
                "- Do not modify files in the workspace.",
                f"- Evaluate only the named specialist under test: {case['_workflow']}.",
                "- Do not turn this into multi-agent orchestration, implementation planning, or validation-first output.",
                "- observed_subagents should include only the specialist under test unless the case explicitly justifies more.",
                "- Record observed behavior as short stable tokens such as findings:first, focus:regression-before-style, boundary:ownership-called-out, security:parser-risk-called-out, uncertainty:carried-forward.",
            ]
        else:
            instruction_lines = [
                "- Treat the patch text above as the only changed surface under evaluation.",
                "- Read the task file and patch before answering.",
                "- Do not modify files in the workspace.",
                "- Record observed behavior as short stable tokens such as scope:escalated, command:pytest, findings:first, findings:deduplicated, uncertainty:carried-forward.",
            ]
        prompt_lines.extend(
            [
                f"Patch file: {automation['patch_file']}",
                patch_text,
                "",
                "Instructions:",
                *instruction_lines,
            ]
        )
    elif mode == "repo-bugfix":
        instruction_lines = [
            "Instructions:",
            "- The current workspace is a disposable copy of the fixture repo.",
            "- Inspect the repo before editing.",
            "- Implement the requested bugfix in this disposable workspace.",
            "- Run the smallest correct validation path you can justify.",
            "- Treat the runtime facts provided above as authoritative for this session unless direct shell evidence in this same session contradicts them.",
            "- Prefer `python -m pytest` for pytest-based validation so the active interpreter is unambiguous.",
            "- Do not report pytest as missing when the authoritative runtime facts already show a working pytest version.",
            "- Record observed behavior as short stable tokens such as context:repo-inspected, implementation:main-agent, validation-skill:build-validate, command:pytest.",
        ]
        if case["id"] == "wr-medium-api-contract":
            instruction_lines.extend(
                [
                    "- Repo inspection and pr-explorer are preparatory only; they do not satisfy this case by themselves.",
                    "- Do not stop after exploration. This case is incomplete unless you implement the contract change, run pytest-based validation, and describe the compatibility impact in the final notes.",
                    '- If you do not implement the change, do not run pytest, or do not provide the final compatibility report, set outcome=\"fail\" rather than partial and include fail signals such as no-implementation, no-pytest, and no-final-report when applicable.',
                ]
            )
        if case["id"] == "wr-hard-security-audit":
            instruction_lines.extend(
                [
                    "- This case is not complete after validation alone; you must perform a justified post-change security audit and include a final user-facing closeout in notes.",
                    "- If the post-change audit finds unresolved security issues, set outcome=\"fail\" rather than partial or pass, list the audit findings in observed_fail_signals, and explain the residual risk in notes.",
                    "- If you do not implement the hardening, do not run validation, do not perform the required security audit, or do not provide the final closeout, set outcome=\"fail\" and include matching fail signals.",
                ]
            )
        prompt_lines.extend(instruction_lines)
    else:
        raise ValueError(f"Unsupported automation mode: {mode}")

    prompt_lines.extend(
        [
            "",
            "Required output fields:",
            '- schema_version: use "2"',
            f'- case_id: use "{case["id"]}"',
            f'- workflow: use "{case["_workflow"]}"',
            f'- fixture_ref: use "{fixture_ref}"',
            '- outcome: "pass", "partial", or "fail"',
            "- observed_subagents: short strings only",
            "- observed_validation: short strings only",
            "- observed_fail_signals: short strings only",
            "- notes: short plain-English explanation",
            "- rubric: use booleans or nulls for trigger_match, output_shape_ok, safety_ok, validation_ok",
        ]
    )
    return "\n".join(prompt_lines) + "\n"


def build_false_trigger_prompt(
    case: dict[str, Any],
    workspace: Path,
    automation: dict[str, Any] | None = None,
) -> str:
    fixture_ref = case.get("fixture_ref")
    prompt_lines = [
        "You are running one local Codex eval harness false-trigger case.",
        "The named workflow below should not trigger as the primary path for the task.",
        "Return only one JSON object that matches the provided false-trigger output schema.",
        "Do not wrap the JSON in markdown fences.",
        "Use short stable tokens in unexpected_subagents, unexpected_validation, and fail_signals.",
        "",
        f"case_id: {case['id']}",
        f"workflow_under_test: {case['_workflow']}",
        "expected_should_trigger: false",
        *([f"fixture_ref: {fixture_ref}"] if fixture_ref else []),
        f"workspace_root: {workspace}",
        "",
        "Case JSON:",
        json.dumps(
            {
                "id": case["id"],
                "workflow": case["_workflow"],
                "mode": case["mode"],
                "title": case["title"],
                "goal": case["goal"],
                "setup": case["setup"],
                "prompt": case["prompt"],
                "expected_subagents": case.get("expected_subagents", []),
                "forbidden_subagents": case.get("forbidden_subagents", []),
                "expected_output_shape": case["expected_output_shape"],
                "expected_safety_behavior": case["expected_safety_behavior"],
                "expected_validation_behavior": case["expected_validation_behavior"],
                "pass_criteria": case["pass_criteria"],
                "fail_signals": case["fail_signals"],
            },
            indent=2,
        ),
        "",
        "Behavior scale:",
        '- actual_trigger_behavior: "not_triggered", "secondary_only", "partial_trigger", or "primary_trigger"',
        '- outcome: "pass" when the workflow stays out of the task or remains clearly secondary; "partial" when it starts to overtake; "fail" when it becomes the primary response.',
        "",
    ]

    if automation is not None and automation["mode"] == "patch-eval":
        assert fixture_ref is not None
        _, fixture_catalog = load_fixture_catalog()
        fixture = fixture_catalog[fixture_ref]
        fixture_root = ROOT / fixture["path"]
        task_path = fixture_root / automation["task_file"]
        patch_path = fixture_root / automation["patch_file"]
        prompt_lines.extend(
            [
                f"Fixture task file: {automation['task_file']}",
                load_text(task_path).strip(),
                "",
                f"Patch file: {automation['patch_file']}",
                load_text(patch_path).strip(),
                "",
                "Instructions:",
                "- Treat the patch text above as the only changed surface under evaluation.",
                "- Read the task file and patch before answering.",
                "- Do not modify files in the workspace.",
                f"- Judge whether the named workflow or specialist should stay out of this changed surface: {case['_workflow']}.",
                "- If the changed surface does not justify that workflow or specialist, prefer actual_trigger_behavior=not_triggered.",
                "- Do not invent specialist-specific concerns that are unsupported by the patch.",
                "- Record only unexpected workflow behavior in unexpected_subagents and unexpected_validation.",
                "- unexpected_subagents should list wrongly-triggered specialists or explorers such as pr-explorer, reviewer, security-auditor, or interop-auditor.",
                "- unexpected_validation should list only validation-first or implementation-first behavior that should not have happened, such as validation:first, validation:commands-listed, implementation:planned, findings:first.",
                "- fail_signals should list only clear false-trigger failures such as workflow:hijacked-task, shape:implementation-plan, shape:review-orchestration, specialist:interop-primary, or specialist:security-primary.",
            ]
        )
    else:
        prompt_lines.extend(
            [
                "Instructions:",
                "- Judge whether the named workflow or specialist would wrongly take over this task.",
                "- Do not fabricate repo inspection, file edits, or validation runs.",
                "- If the best behavior is to route elsewhere, reflect that with actual_trigger_behavior=not_triggered or secondary_only.",
                "- Record only unexpected workflow behavior in unexpected_subagents and unexpected_validation.",
                "- unexpected_subagents should list wrongly-triggered specialists or explorers such as pr-explorer, reviewer, security-auditor, or interop-auditor.",
                "- unexpected_validation should list only validation-first or implementation-first behavior that should not have happened, such as validation:first, validation:commands-listed, implementation:planned, findings:first.",
                "- fail_signals should list only clear false-trigger failures such as workflow:hijacked-task, shape:implementation-plan, shape:review-orchestration, specialist:interop-primary.",
            ]
        )

    prompt_lines.extend(
        [
            "",
            "Required output fields:",
            '- schema_version: use "1"',
            f'- case_id: use "{case["id"]}"',
            f'- workflow: use "{case["_workflow"]}"',
            *([f'- fixture_ref: use "{fixture_ref}"'] if fixture_ref else []),
            "- expected_should_trigger: use false",
            '- actual_trigger_behavior: one of "not_triggered", "secondary_only", "partial_trigger", "primary_trigger"',
            '- outcome: "pass", "partial", or "fail"',
            "- unexpected_subagents: short strings only",
            "- unexpected_validation: short strings only",
            "- fail_signals: short strings only",
            "- notes: short plain-English explanation",
            "- rubric: use booleans or nulls for trigger_match, output_shape_ok, task_focus_ok, safety_ok",
        ]
    )
    return "\n".join(prompt_lines) + "\n"


def build_result(raw_output: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw_output)
    result["run_timestamp"] = utc_now_iso()
    if "schema_version" not in result:
        result["schema_version"] = "2"
    notes_text = result.get("notes") if isinstance(result.get("notes"), str) else ""
    if isinstance(result.get("observed_validation"), list):
        result["observed_validation"] = normalize_observed_validation(
            case,
            [item for item in result["observed_validation"] if isinstance(item, str)],
            notes=notes_text,
        )
    if case["id"] == "wr-medium-api-contract":
        fail_signals = {
            item for item in result.get("observed_fail_signals", []) if isinstance(item, str)
        }
        if fail_signals & {"no-implementation", "no-pytest", "no-final-report"}:
            result["outcome"] = "fail"
    if case["id"] == "wr-hard-security-audit":
        fail_signals = {
            item for item in result.get("observed_fail_signals", []) if isinstance(item, str)
        }
        if fail_signals & {
            "no-repo-inspection",
            "no-main-impl",
            "no-security-audit",
            "no-validation",
            "no-risk-report",
            "final:missing",
            "audit:argv-token",
            "audit:argv-token-leak",
            "audit:log-forge",
            "audit:log-forging",
            "audit:log-sanitize-gap",
            "audit:win-path",
            "audit:win-path-bypass",
            "audit:traversal-alias",
        }:
            result["outcome"] = "fail"
    errors = validate_result_record(
        result,
        expected_case_id=case["id"],
        expected_workflow=case["_workflow"],
    )
    if result.get("fixture_ref") != case.get("fixture_ref"):
        errors.append(
            f"fixture_ref mismatch: expected {case.get('fixture_ref')}, got {result.get('fixture_ref')}"
        )
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Invalid structured result:\n{joined}")
    return result


def build_false_trigger_result(raw_output: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw_output)
    result["run_timestamp"] = utc_now_iso()
    if "schema_version" not in result:
        result["schema_version"] = "1"
    errors = validate_false_trigger_record(
        result,
        expected_case_id=case["id"],
        expected_workflow=case["_workflow"],
    )
    if case.get("fixture_ref") and result.get("fixture_ref") != case.get("fixture_ref"):
        errors.append(
            f"fixture_ref mismatch: expected {case.get('fixture_ref')}, got {result.get('fixture_ref')}"
        )
    if result.get("expected_should_trigger") is not False:
        errors.append("expected_should_trigger must be false for automated negative cases")
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Invalid false-trigger result:\n{joined}")
    return result


def cmd_list_supported() -> int:
    _, automation_catalog = load_automation_manifest()
    for case_id, item in automation_catalog.items():
        case = find_case(case_id)
        assert case is not None
        print(f"{case_id}: {case['_workflow']} [{item['mode']}]")
    return 0


def cmd_run(
    case_id: str,
    run_date: str,
    codex_bin: str,
    model: str | None,
    force: bool,
    dry_run: bool,
    results_dir: str | None,
) -> int:
    case = find_case(case_id)
    if case is None:
        print(f"Case not found: {case_id}", file=sys.stderr)
        return 1

    _, automation_catalog = load_automation_manifest()
    _, negative_automation_catalog = load_automation_manifest(kind="negative")
    automation = automation_catalog.get(case_id)
    negative_automation = negative_automation_catalog.get(case_id)
    if automation is None and negative_automation is None:
        print(f"Case is not safely automatable yet: {case_id}", file=sys.stderr)
        print(f"Supported manifest: {AUTOMATION_MANIFEST_PATH}", file=sys.stderr)
        return 1

    run_root = resolve_results_dir(results_dir) / run_date
    run_root.mkdir(parents=True, exist_ok=True)
    workspace = run_root / "workspaces" / case_id
    raw_output_path = run_root / f"{case_id}.raw.json"
    result_path = run_root / f"{case_id}.json"
    prompt_path = run_root / f"{case_id}.prompt.txt"

    automation_kind = "positive" if automation is not None else "negative"
    workspace_source: Path | None = None
    if automation_kind == "positive":
        assert automation is not None
        _, fixture_catalog = load_fixture_catalog()
        fixture = fixture_catalog[case["fixture_ref"]]
        source_workspace = ROOT / fixture["path"]
        runtime_facts = gather_runtime_facts(source_workspace)
        prompt_text = build_prompt(case, automation, workspace, runtime_facts=runtime_facts)
        output_schema_path = OUTPUT_SCHEMA_PATH
        workspace_source = source_workspace
    else:
        assert negative_automation is not None
        if negative_automation["mode"] == "patch-eval":
            _, fixture_catalog = load_fixture_catalog()
            fixture = fixture_catalog[case["fixture_ref"]]
            source_workspace = ROOT / fixture["path"]
            prompt_text = build_false_trigger_prompt(case, workspace, automation=negative_automation)
            workspace_source = source_workspace
        else:
            prompt_text = build_false_trigger_prompt(case, workspace)
        output_schema_path = FALSE_TRIGGER_OUTPUT_SCHEMA_PATH
    prompt_path.write_text(prompt_text)

    if dry_run:
        print(f"dry_run=true")
        print(f"automation_kind={automation_kind}")
        print(f"case_id={case_id}")
        print(f"workflow={case['_workflow']}")
        if workspace_source is not None:
            print(f"workspace_source={workspace_source}")
        print(f"workspace_destination={workspace}")
        print(f"prompt_path={prompt_path}")
        print(f"raw_output_path={raw_output_path}")
        print(f"result_path={result_path}")
        print(f"output_schema={output_schema_path}")
        return 0

    if automation_kind == "positive":
        assert workspace_source is not None
        stage_workspace(workspace_source, workspace, force=force)
    elif workspace_source is not None:
        stage_workspace(workspace_source, workspace, force=force)
    else:
        prepare_empty_workspace(workspace, force=force)
    if raw_output_path.exists() and not force:
        print(f"Raw output already exists: {raw_output_path}", file=sys.stderr)
        return 1
    if result_path.exists() and not force:
        print(f"Result already exists: {result_path}", file=sys.stderr)
        return 1

    if automation_kind == "positive":
        assert automation is not None
        sandbox_mode = "read-only" if automation["mode"] == "patch-eval" else "workspace-write"
    else:
        sandbox_mode = "read-only"
    command = [
        codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "never",
        "--sandbox",
        sandbox_mode,
        "-c",
        'approval_policy="never"',
        "--output-schema",
        str(output_schema_path),
        "--output-last-message",
        str(raw_output_path),
        "-",
    ]
    if model:
        command[2:2] = ["--model", model]

    completed = subprocess.run(
        command,
        cwd=workspace,
        env=build_codex_exec_env(),
        input=prompt_text,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        return completed.returncode

    if not raw_output_path.exists():
        print(f"Codex did not write raw output: {raw_output_path}", file=sys.stderr)
        return 1

    with raw_output_path.open() as fh:
        raw_output = json.load(fh)
    if automation_kind == "positive":
        result = build_result(raw_output, case)
    else:
        result = build_false_trigger_result(raw_output, case)
    with result_path.open("w") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")

    print(result_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small supported subset of automated evals.")
    parser.add_argument("case_id", nargs="?")
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
        help="Overwrite existing run artifacts and workspace for the same case/date.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the prompt file and print planned paths without invoking codex exec.",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Optional override for the results root directory. Default: ~/.codex/evals/results",
    )
    parser.add_argument(
        "--list-supported",
        action="store_true",
        help="List the currently supported automated positive cases.",
    )
    args = parser.parse_args()

    if args.list_supported:
        return cmd_list_supported()
    if not args.case_id:
        parser.error("case_id is required unless --list-supported is used")
    return cmd_run(
        args.case_id,
        args.run_date,
        args.codex_bin,
        args.model,
        args.force,
        args.dry_run,
        args.results_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
