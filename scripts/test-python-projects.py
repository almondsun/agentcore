#!/usr/bin/env python3
"""Run every self-contained Python fixture through its repository-native pytest path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    "openai/lab/live_tasks/config_migration_compat",
    "openai/lab/live_tasks/vendor_ingest_hardening",
    "openai/dot-codex/evals/fixtures/tiny-python-service",
    "openai/dot-codex/evals/fixtures/tiny-workflow-easy",
    "openai/dot-codex/evals/fixtures/tiny-workflow-medium",
    "openai/dot-codex/evals/fixtures/tiny-workflow-hard",
)


def main() -> int:
    failures: list[str] = []
    for relative in PROJECTS:
        root = REPO_ROOT / relative
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(f"== {relative} ==")
        print(completed.stdout, end="")
        if completed.returncode != 0:
            failures.append(relative)
    if failures:
        print("failed projects: " + ", ".join(failures), file=sys.stderr)
        return 1
    print(f"all {len(PROJECTS)} Python projects passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
