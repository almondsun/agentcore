#!/usr/bin/env python3
"""Continue changed-worktree turns that end without validation evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys


VALIDATION_MARKERS = (
    "validated",
    "validation",
    "tests run",
    "checks run",
    "not run",
    "could not run",
    "unverified",
    "remaining risk",
    "remaining unverified",
)


def _git_has_changes(cwd: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if payload.get("stop_hook_active"):
        return 0

    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        return 0

    message = payload.get("last_assistant_message")
    if not isinstance(message, str):
        message = ""

    if not _git_has_changes(cwd):
        return 0

    lower_message = message.lower()
    if any(marker in lower_message for marker in VALIDATION_MARKERS):
        return 0

    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "The worktree has changes, but the closeout did not mention validation. "
                    "Run the smallest relevant check, or explicitly state why validation was not run and what remains unverified."
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
