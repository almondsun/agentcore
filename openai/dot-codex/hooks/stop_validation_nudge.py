#!/usr/bin/env python3
"""Continue implementation closeouts that omit validation evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
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

PLAN_OR_DISCUSSION_MARKERS = (
    "<proposed_plan>",
    "no files were edited",
    "no file was edited",
    "no files changed",
    "no repo-tracked edits",
    "no implementation happened",
    "no implementation was performed",
    "no implementation change",
    "plan-only",
    "planning turn",
    "conversational",
    "only inspected",
    "only combined",
    "only clarified",
)

IMPLEMENTATION_CLOSEOUT_MARKERS = (
    "implemented",
    "changed",
    "updated",
    "fixed",
    "installed",
    "created",
    "removed",
    "refactored",
    "patched",
    "added",
    "deleted",
    "renamed",
    "modified",
    "configured",
    "wrote",
    "what changed",
    "summary",
    "done",
    "completed",
)


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


def _is_plan_or_discussion(message: str) -> bool:
    lower_message = message.lower()
    return any(marker in lower_message for marker in PLAN_OR_DISCUSSION_MARKERS)


def _looks_like_implementation_closeout(message: str) -> bool:
    lower_message = message.lower()
    return any(marker in lower_message for marker in IMPLEMENTATION_CLOSEOUT_MARKERS)


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

    if _is_plan_or_discussion(message):
        return 0

    if not _looks_like_implementation_closeout(message):
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
