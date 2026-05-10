#!/usr/bin/env python3
"""Add lightweight context when a session starts in a dirty git worktree."""

from __future__ import annotations

import json
import os
import subprocess
import sys


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

    source = payload.get("source")
    if source not in {"startup", "resume"}:
        return 0

    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        return 0

    if not _git_has_changes(cwd):
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "This session started or resumed inside a git worktree with existing changes. "
                        "Before editing, inspect the current status/diff and preserve unrelated user changes."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
