#!/usr/bin/env python3
"""Surface high-signal follow-up context after supported tools run."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


FAILURE_PATTERNS = [
    (r"\bcommand not found\b", "command not found"),
    (r"\bpermission denied\b", "permission denied"),
    (r"\bno such file or directory\b", "missing file or directory"),
    (r"\btraceback \(most recent call last\):", "Python traceback"),
    (r"\bsyntaxerror\b", "syntax error"),
    (r"process exited with code [1-9]\d*", "nonzero command exit"),
    (r"exit code [1-9]\d*", "nonzero command exit"),
]

SECRET_PATTERNS = [
    ("an OpenAI API key", re.compile(r"\bsk-(?:proj|live|test)?-[A-Za-z0-9_-]{20,}\b")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
]


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


def _explicit_failure(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("exit_code", "exitCode", "returncode", "return_code", "status"):
        code = value.get(key)
        if isinstance(code, int) and code != 0:
            return f"nonzero command exit ({key}={code})"
    return None


def _message(reason: str) -> None:
    print(
        json.dumps(
            {
                "systemMessage": (
                    f"Post-tool review noticed {reason}. Address this before relying on the tool result."
                ),
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"The previous tool result contained {reason}. Inspect it and either fix the issue "
                        "or explicitly state why it is benign."
                    ),
                },
            }
        )
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    response_text = _as_text(payload.get("tool_response"))
    explicit_failure = _explicit_failure(payload.get("tool_response"))
    if explicit_failure:
        _message(explicit_failure)
        return 0

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(response_text):
            _message(f"secret-looking output ({label})")
            return 0

    lower_response = response_text.lower()
    for pattern, reason in FAILURE_PATTERNS:
        if re.search(pattern, lower_response):
            _message(reason)
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
