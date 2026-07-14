#!/usr/bin/env python3
"""
Run a small supported subset of automated eval cases via `codex exec`.

The runner keeps the subject prompt blind to the rubric, captures a JSONL trace,
collects deterministic workspace/test evidence, and uses a separate grading turn
to produce the comparable result record.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
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


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(value, indent=2) + "\n")


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
            or "ran python -m pytest successfully" in notes_lower
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
    symlinks = [path for path in source.rglob("*") if path.is_symlink()]
    if symlinks:
        raise ValueError(f"Fixture contains unsupported symlink: {symlinks[0]}")
    if destination.exists():
        if not force:
            raise FileExistsError(f"Workspace already exists: {destination}")
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)


def prepare_empty_workspace(destination: Path, force: bool) -> None:
    if destination.exists():
        if not force:
            raise FileExistsError(f"Workspace already exists: {destination}")
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)


def validate_run_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid --date {value!r}; expected YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"Invalid --date {value!r}; expected YYYY-MM-DD")
    return value


def contained_child(root: Path, *parts: str) -> Path:
    resolved_root = root.resolve()
    candidate = resolved_root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError(f"Run artifact path escapes results root: {candidate}")
    return candidate


def build_blind_prompt(case: dict[str, Any], automation: dict[str, Any]) -> str:
    """Build the subject prompt without expected answers, rubrics, or outcome labels."""

    _, fixture_catalog = load_fixture_catalog()
    fixture = fixture_catalog[case["fixture_ref"]]
    fixture_root = ROOT / fixture["path"]
    task_text = load_text(fixture_root / automation["task_file"]).strip()
    lines = [case["prompt"].strip(), "", task_text, ""]
    if automation["mode"] == "patch-eval":
        patch_text = load_text(fixture_root / automation["patch_file"]).strip()
        lines.extend(
            [
                "Changed patch:",
                patch_text,
                "",
                "Treat the patch as the changed surface. Do not modify the workspace.",
                "Return the normal user-facing review or answer.",
            ]
        )
    elif automation["mode"] == "repo-bugfix":
        lines.extend(
            [
                "Work in the current disposable workspace. Inspect it, make the requested change,",
                "run the repository-native validation, and return a normal user-facing closeout.",
            ]
        )
    else:
        raise ValueError(f"Unsupported automation mode: {automation['mode']}")
    return "\n".join(lines).strip() + "\n"


def build_blind_negative_prompt(
    case: dict[str, Any], automation: dict[str, Any] | None
) -> str:
    """Build a natural task prompt without naming the workflow being tested."""

    lines = [case["prompt"].strip(), ""]
    fixture_ref = case.get("fixture_ref")
    if automation is not None and automation["mode"] == "patch-eval":
        assert fixture_ref is not None
        _, fixture_catalog = load_fixture_catalog()
        fixture_root = ROOT / fixture_catalog[fixture_ref]["path"]
        lines.extend(
            [
                load_text(fixture_root / automation["task_file"]).strip(),
                "",
                "Changed patch:",
                load_text(fixture_root / automation["patch_file"]).strip(),
                "",
                "Respond naturally to the request. Do not modify the workspace.",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def snapshot_workspace(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    total_bytes = 0
    for path in sorted(root.rglob("*")):
        try:
            metadata = path.lstat()
        except OSError:
            continue
        if not stat.S_ISREG(metadata.st_mode):
            continue
        rel = path.relative_to(root)
        if set(rel.parts) & {".git", ".pytest_cache", "__pycache__"}:
            continue
        if metadata.st_size > 1_000_000 or total_bytes + metadata.st_size > 5_000_000:
            snapshot[str(rel)] = f"<omitted:{metadata.st_size}-bytes>"
            continue
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError:
            continue
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_size != metadata.st_size:
                continue
            raw = os.read(descriptor, metadata.st_size + 1)
        finally:
            os.close(descriptor)
        if len(raw) > metadata.st_size:
            snapshot[str(rel)] = "<omitted:changed-during-read>"
            continue
        try:
            snapshot[str(rel)] = raw.decode("utf-8")
        except UnicodeDecodeError:
            snapshot[str(rel)] = f"<binary:{metadata.st_size}>"
        total_bytes += metadata.st_size
    return snapshot


def workspace_diff(before: dict[str, str], after: dict[str, str]) -> str:
    chunks: list[str] = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name, "")
        new = after.get(name, "")
        if old == new:
            continue
        chunks.extend(
            difflib.unified_diff(
                old.splitlines(),
                new.splitlines(),
                fromfile=f"before/{name}",
                tofile=f"after/{name}",
                lineterm="",
            )
        )
    text = "\n".join(chunks)
    return text[-30000:] if text else "<no workspace changes>"


def run_independent_validation(workspace: Path, mode: str) -> str:
    if mode != "repo-bugfix":
        return "<not applicable for read-only patch/prompt case>"
    checked = 0
    failures: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(workspace)
        if set(rel.parts) & {".git", ".pytest_cache", "__pycache__"}:
            continue
        if path.stat().st_size > 1_000_000:
            failures.append(f"{rel}: skipped because file exceeds 1 MB")
            continue
        try:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
            elif path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix == ".toml":
                tomllib.loads(path.read_text(encoding="utf-8"))
            else:
                continue
            checked += 1
        except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
            failures.append(f"{rel}: {type(exc).__name__}: {exc}")
    status = "ok" if not failures else "failed"
    details = "\n".join(failures) if failures else "no parse failures"
    return f"static_parse_status={status}\nfiles_checked={checked}\n{details}"


def build_grader_prompt(
    case: dict[str, Any],
    subject_message: str,
    trace: str,
    diff: str,
    validation: str,
    *,
    negative: bool,
) -> str:
    evidence = {
        "subject_final_message": subject_message,
        "trace_tail": trace[-30000:],
        "workspace_diff": diff,
        "independent_validation": validation,
    }
    expected = {
        "case_id": case["id"],
        "workflow": case["_workflow"],
        "fixture_ref": case.get("fixture_ref"),
        "expected_subagents": case.get("expected_subagents", []),
        "forbidden_subagents": case.get("forbidden_subagents", []),
        "expected_output_shape": case["expected_output_shape"],
        "expected_safety_behavior": case["expected_safety_behavior"],
        "expected_validation_behavior": case["expected_validation_behavior"],
        "pass_criteria": case["pass_criteria"],
        "fail_signals": case["fail_signals"],
    }
    mode = "false-trigger" if negative else "positive"
    return (
        f"You are the independent grader for one {mode} Codex evaluation.\n"
        "The subject never saw this rubric. Grade only the supplied trace, diff, validation, and final message.\n"
        "Do not infer tool calls, edits, tests, or subagents that are absent from evidence.\n"
        "Return exactly the JSON required by the output schema, using short stable observation tokens.\n\n"
        f"Expected contract:\n{json.dumps(expected, indent=2)}\n\n"
        f"Observed evidence:\n{json.dumps(evidence, indent=2)}\n"
    )


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

    run_date = validate_run_date(run_date)
    results_root = resolve_results_dir(results_dir)
    run_root = contained_child(results_root, run_date)
    workspace = contained_child(run_root, "workspaces", case_id)
    subject_output_path = contained_child(run_root, f"{case_id}.subject.txt")
    trace_path = contained_child(run_root, f"{case_id}.trace.jsonl")
    grader_prompt_path = contained_child(run_root, f"{case_id}.grader.prompt.txt")
    grader_raw_path = contained_child(run_root, f"{case_id}.grader.raw.json")
    result_path = contained_child(run_root, f"{case_id}.json")
    prompt_path = contained_child(run_root, f"{case_id}.prompt.txt")

    automation_kind = "positive" if automation is not None else "negative"
    workspace_source: Path | None = None
    if automation_kind == "positive":
        assert automation is not None
        _, fixture_catalog = load_fixture_catalog()
        fixture = fixture_catalog[case["fixture_ref"]]
        source_workspace = ROOT / fixture["path"]
        prompt_text = build_blind_prompt(case, automation)
        output_schema_path = OUTPUT_SCHEMA_PATH
        workspace_source = source_workspace
    else:
        assert negative_automation is not None
        if negative_automation["mode"] == "patch-eval":
            _, fixture_catalog = load_fixture_catalog()
            fixture = fixture_catalog[case["fixture_ref"]]
            source_workspace = ROOT / fixture["path"]
            prompt_text = build_blind_negative_prompt(case, negative_automation)
            workspace_source = source_workspace
        else:
            prompt_text = build_blind_negative_prompt(case, None)
        output_schema_path = FALSE_TRIGGER_OUTPUT_SCHEMA_PATH

    if dry_run:
        print(f"dry_run=true")
        print(f"automation_kind={automation_kind}")
        print(f"case_id={case_id}")
        print(f"workflow={case['_workflow']}")
        if workspace_source is not None:
            print(f"workspace_source={workspace_source}")
        print(f"workspace_destination={workspace}")
        print(f"prompt_path={prompt_path}")
        print(f"subject_output_path={subject_output_path}")
        print(f"trace_path={trace_path}")
        print(f"grader_prompt_path={grader_prompt_path}")
        print(f"grader_raw_path={grader_raw_path}")
        print(f"result_path={result_path}")
        print(f"output_schema={output_schema_path}")
        print("subject_prompt_begin")
        print(prompt_text, end="")
        print("subject_prompt_end")
        return 0

    artifact_paths = [
        prompt_path,
        subject_output_path,
        trace_path,
        grader_prompt_path,
        grader_raw_path,
        result_path,
    ]
    existing = [path for path in artifact_paths if path.exists()]
    if (existing or workspace.exists()) and not force:
        for path in existing:
            print(f"Run artifact already exists: {path}", file=sys.stderr)
        if workspace.exists():
            print(f"Workspace already exists: {workspace}", file=sys.stderr)
        return 1

    run_root.mkdir(parents=True, exist_ok=True)

    if automation_kind == "positive":
        assert workspace_source is not None
        stage_workspace(workspace_source, workspace, force=force)
    elif workspace_source is not None:
        stage_workspace(workspace_source, workspace, force=force)
    else:
        prepare_empty_workspace(workspace, force=force)
    before = snapshot_workspace(workspace)
    write_text_atomic(prompt_path, prompt_text)

    permission_profile = (
        "agentcore_workspace"
        if automation is not None and automation["mode"] == "repo-bugfix"
        else ":read-only"
    )
    command = [
        codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "-c",
        'approval_policy="never"',
        "-c",
        f'default_permissions="{permission_profile}"',
        "--output-last-message",
        str(subject_output_path),
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
    write_text_atomic(trace_path, completed.stdout)

    if not subject_output_path.exists():
        print(f"Codex did not write a final message: {subject_output_path}", file=sys.stderr)
        return 1

    after = snapshot_workspace(workspace)
    diff = workspace_diff(before, after)
    validation = run_independent_validation(
        workspace,
        automation["mode"] if automation is not None else negative_automation["mode"],
    )
    grader_prompt = build_grader_prompt(
        case,
        subject_output_path.read_text(encoding="utf-8"),
        completed.stdout,
        diff,
        validation,
        negative=automation_kind == "negative",
    )
    write_text_atomic(grader_prompt_path, grader_prompt)

    grader_command = [
        codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "never",
        "-c",
        'approval_policy="never"',
        "-c",
        'default_permissions=":read-only"',
        "--output-schema",
        str(output_schema_path),
        "--output-last-message",
        str(grader_raw_path),
        "-",
    ]
    if model:
        grader_command[2:2] = ["--model", model]
    graded = subprocess.run(
        grader_command,
        cwd=run_root,
        env=build_codex_exec_env(),
        input=grader_prompt,
        text=True,
        capture_output=True,
    )
    if graded.returncode != 0:
        sys.stderr.write(graded.stderr)
        return graded.returncode
    if not grader_raw_path.exists():
        print(f"Independent grader did not write output: {grader_raw_path}", file=sys.stderr)
        return 1
    with grader_raw_path.open(encoding="utf-8") as fh:
        raw_output = json.load(fh)
    if automation_kind == "positive":
        result = build_result(raw_output, case)
        if automation is not None and automation["mode"] == "repo-bugfix":
            deterministic_failures: list[str] = []
            if "static_parse_status=failed" in validation:
                deterministic_failures.append("deterministic:parse-failed")
            if diff == "<no workspace changes>":
                deterministic_failures.append("deterministic:no-workspace-change")
            if deterministic_failures:
                result["outcome"] = "fail"
                result["observed_fail_signals"] = dedupe_preserve_order(
                    [
                        item
                        for item in result.get("observed_fail_signals", [])
                        if isinstance(item, str)
                    ]
                    + deterministic_failures
                )
                rubric = result.get("rubric")
                if isinstance(rubric, dict):
                    rubric["validation_ok"] = False
    else:
        result = build_false_trigger_result(raw_output, case)
    write_json_atomic(result_path, result)

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
        help="Print the blind prompt and planned paths without writing artifacts or invoking Codex.",
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
