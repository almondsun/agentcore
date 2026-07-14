#!/usr/bin/env python3
"""Add lightweight context when a session starts in a dirty git worktree."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def _git_has_changes(cwd: str) -> bool:
    git = _trusted_git()
    if git is None:
        return False
    try:
        result = subprocess.run(
            [git, "-c", "core.fsmonitor=false", "status", "--short"],
            cwd=cwd,
            env=_git_environment(),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _trusted_git() -> str | None:
    if os.name != "nt" and Path("/usr/bin/git").is_file():
        return "/usr/bin/git"
    if os.name != "nt":
        return None
    candidates: list[Path] = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / "Git" / "cmd" / "git.exe")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Programs" / "Git" / "cmd" / "git.exe")
    return next((str(path.resolve()) for path in candidates if path.is_file()), None)


def _git_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "SYSTEMROOT", "WINDIR"}}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
        }
    )
    return env


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
