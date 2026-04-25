#!/usr/bin/env python3
"""Deny catastrophic shell approval requests and annotate risky ones."""

from __future__ import annotations

import json
import re
import sys


DENY_PATTERNS = [
    (r"(?i)(^|\s)rm\s+-[^\n;]*r[^\n;]*f[^\n;]*\s+/(?:\s|$)", "recursive removal of filesystem root"),
    (r"(?i)(^|\s)rm\s+-[^\n;]*r[^\n;]*f[^\n;]*\s+\$?HOME(?:\s|/|$)", "recursive removal of the home directory"),
    (r"(?i)(^|\s)chmod\s+-R\s+777\s+/(?:\s|$)", "world-writable permissions on filesystem root"),
    (r"(?i)(^|\s)mkfs(?:\.[A-Za-z0-9_-]+)?\s+", "filesystem formatting"),
    (r"(?i)(^|\s)dd\s+.*\bof=/dev/(?:sd|nvme|vd|hd)", "raw write to a block device"),
    (r":\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "fork bomb"),
]

WARN_PATTERNS = [
    (r"(?i)\b(?:curl|wget)\b[^\n|;&]*[|]\s*(?:sudo\s+)?(?:bash|sh)\b", "downloaded script execution"),
    (r"(?i)(^|\s)sudo\s+", "privileged command"),
    (r"(?i)(^|\s)git\s+clean\s+-[^\n;]*[xdf]", "destructive git clean"),
    (r"(?i)(^|\s)rm\s+-[^\n;]*r[^\n;]*f", "recursive forced removal"),
]


def _command(payload: dict[str, object]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    command = _command(payload)
    if not command:
        return 0

    for pattern, reason in DENY_PATTERNS:
        if re.search(pattern, command):
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PermissionRequest",
                            "decision": {
                                "behavior": "deny",
                                "message": f"Blocked catastrophic command pattern: {reason}.",
                            },
                        }
                    }
                )
            )
            return 0

    for pattern, reason in WARN_PATTERNS:
        if re.search(pattern, command):
            print(
                json.dumps(
                    {
                        "systemMessage": (
                            f"Approval request includes a high-risk shell pattern ({reason}). "
                            "Confirm explicit user intent, affected paths, and rollback path before proceeding."
                        )
                    }
                )
            )
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
