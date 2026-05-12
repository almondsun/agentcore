#!/usr/bin/env python3
"""Block high-confidence dangerous tool requests before they run."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


DANGEROUS_COMMAND_PATTERNS = [
    (r"(?i)(^|\s)rm\s+-[^\n;]*r[^\n;]*f[^\n;]*\s+/(?:\s|$)", "recursive removal of filesystem root"),
    (r"(?i)(^|\s)rm\s+-[^\n;]*r[^\n;]*f[^\n;]*\s+\$?HOME(?:\s|/|$)", "recursive removal of the home directory"),
    (r"(?i)(^|\s)chmod\s+-R\s+777\s+/(?:\s|$)", "world-writable permissions on filesystem root"),
    (r"(?i)(^|\s)mkfs(?:\.[A-Za-z0-9_-]+)?\s+", "filesystem formatting"),
    (r"(?i)(^|\s)dd\s+.*\bof=/dev/(?:sd|nvme|vd|hd)", "raw write to a block device"),
    (r":\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "fork bomb"),
]

SECRET_PATTERNS = [
    ("an OpenAI API key", re.compile(r"\bsk-(?:proj|live|test)?-[A-Za-z0-9_-]{20,}\b")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
]


def _tool_input_text(tool_input: Any) -> str:
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    try:
        return json.dumps(tool_input, sort_keys=True)
    except (TypeError, ValueError):
        return str(tool_input)


def _block(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    text = _tool_input_text(tool_input)

    if tool_name == "Bash":
        for pattern, reason in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, text):
                _block(f"Blocked catastrophic command pattern before execution: {reason}.")
                return 0

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            _block(f"Blocked tool request because it appears to write or execute content containing {label}.")
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
