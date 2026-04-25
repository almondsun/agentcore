#!/usr/bin/env python3
"""
Minimal preflight for the final workflow-realism live run.

Checks only the prerequisites needed to run the existing batch command:
- Codex CLI is available
- codex exec can reach its backend
- results directory is writable
- Python validation toolchain for the final fixtures is available
- the three final cases and their baselines exist in the harness
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from eval_harness import ROOT, find_case, resolve_results_dir

FINAL_CASE_IDS = [
    "wr-easy-local-bugfix",
    "wr-medium-api-contract",
    "wr-hard-security-audit",
]


def run_command(command: list[str], *, cwd: Path | None = None, timeout: int = 20) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": f"timeout after {timeout}s",
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": str(exc),
        }

    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "error": "",
    }


def ensure_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def check_codex_cli(codex_bin: str) -> dict[str, object]:
    resolved = shutil.which(codex_bin)
    result = run_command([codex_bin, "--version"], timeout=10)
    return {
        "name": "codex_cli",
        "ok": bool(resolved) and bool(result["ok"]),
        "details": {
            "codex_bin": codex_bin,
            "resolved_path": resolved,
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "error": result["error"],
        },
    }


def check_codex_backend(codex_bin: str) -> dict[str, object]:
    command = [
        codex_bin,
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "never",
        "--sandbox",
        "read-only",
        "-c",
        'approval_policy="never"',
        "-",
    ]
    try:
        probe = subprocess.run(
            command,
            cwd=Path.cwd(),
            input="Return exactly the word ok.\n",
            text=True,
            capture_output=True,
            timeout=20,
        )
        stdout = probe.stdout or ""
        stderr = probe.stderr or ""
        exit_code: int | None = probe.returncode
        error = ""
    except subprocess.TimeoutExpired as exc:
        stdout = ensure_text(exc.stdout)
        stderr = ensure_text(exc.stderr)
        exit_code = None
        error = "timeout after 20s"

    combined = stdout + stderr
    ok = exit_code == 0 and "\nok\n" in f"\n{combined}\n"
    return {
        "name": "codex_backend",
        "ok": ok,
        "details": {
            "command": command,
            "exit_code": exit_code,
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
            "error": error,
        },
    }


def check_results_dir(results_dir: Path) -> dict[str, object]:
    probe_dir = results_dir / ".preflight"
    probe_file = probe_dir / "write-test.txt"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file.write_text("ok\n")
        content = probe_file.read_text()
        ok = content == "ok\n"
        if probe_file.exists():
            probe_file.unlink()
        try:
            probe_dir.rmdir()
        except OSError:
            pass
        return {
            "name": "results_dir",
            "ok": ok,
            "details": {
                "results_dir": str(results_dir),
                "probe_file": str(probe_file),
            },
        }
    except Exception as exc:
        return {
            "name": "results_dir",
            "ok": False,
            "details": {
                "results_dir": str(results_dir),
                "error": str(exc),
            },
        }


def check_pytest_toolchain() -> dict[str, object]:
    python_result = run_command([sys.executable, "--version"], timeout=10)
    pytest_result = run_command([sys.executable, "-m", "pytest", "--version"], timeout=10)
    return {
        "name": "python_validation_toolchain",
        "ok": bool(python_result["ok"]) and bool(pytest_result["ok"]),
        "details": {
            "python_executable": sys.executable,
            "python_exit_code": python_result["exit_code"],
            "python_stdout": python_result["stdout"],
            "python_stderr": python_result["stderr"],
            "pytest_exit_code": pytest_result["exit_code"],
            "pytest_stdout": pytest_result["stdout"],
            "pytest_stderr": pytest_result["stderr"],
            "pytest_error": pytest_result["error"],
        },
    }


def check_fixture_pytests() -> dict[str, object]:
    fixture_ids = [
        "tiny-workflow-easy",
        "tiny-workflow-medium",
        "tiny-workflow-hard",
    ]
    fixture_results: list[dict[str, object]] = []
    all_ok = True
    for fixture_id in fixture_ids:
        fixture_root = ROOT / "fixtures" / fixture_id
        result = run_command([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=fixture_root, timeout=20)
        fixture_ok = bool(result["ok"])
        all_ok = all_ok and fixture_ok
        fixture_results.append(
            {
                "fixture_id": fixture_id,
                "fixture_root": str(fixture_root),
                "ok": fixture_ok,
                "exit_code": result["exit_code"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "error": result["error"],
            }
        )
    return {
        "name": "fixture_validation_readiness",
        "ok": all_ok,
        "details": {
            "fixtures": fixture_results,
        },
    }


def check_harness_prereqs() -> dict[str, object]:
    missing: list[str] = []
    for case_id in FINAL_CASE_IDS:
        case = find_case(case_id)
        if case is None:
            missing.append(f"missing case metadata: {case_id}")
            continue
        baseline_path = ROOT / "baselines" / case["_workflow"] / f"{case_id}.json"
        if not baseline_path.exists():
            missing.append(f"missing baseline: {baseline_path}")
    return {
        "name": "harness_prereqs",
        "ok": not missing,
        "details": {
            "case_ids": FINAL_CASE_IDS,
            "missing": missing,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal preflight for the final workflow-realism live run.")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument(
        "--results-dir",
        default="/tmp/codex-final-eval",
        help="Results root to use for the live batch rerun.",
    )
    args = parser.parse_args()

    results_dir = resolve_results_dir(args.results_dir)
    checks = [
        check_codex_cli(args.codex_bin),
        check_codex_backend(args.codex_bin),
        check_results_dir(results_dir),
        check_pytest_toolchain(),
        check_fixture_pytests(),
        check_harness_prereqs(),
    ]

    blockers = [check["name"] for check in checks if not check["ok"]]
    payload = {
        "ok": not blockers,
        "codex_bin": args.codex_bin,
        "results_dir": str(results_dir),
        "final_case_ids": FINAL_CASE_IDS,
        "checks": checks,
        "blockers": blockers,
        "recommended_rerun_command": (
            f"python3 {ROOT / 'scripts' / 'run_batch.py'} "
            "wr-easy-local-bugfix wr-medium-api-contract wr-hard-security-audit "
            f"--date 2026-03-31 --results-dir {results_dir} --force"
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
