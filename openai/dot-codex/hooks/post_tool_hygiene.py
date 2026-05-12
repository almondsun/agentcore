#!/usr/bin/env python3
"""Surface high-signal follow-up context after supported tools run."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


FAILURE_PATTERNS = [
    (r"\btraceback \(most recent call last\):", "Python traceback"),
    (r"\bsyntaxerror\b", "syntax error"),
    (r"process exited with code [1-9]\d*", "nonzero command exit"),
    (r"exit code [1-9]\d*", "nonzero command exit"),
    (r"\b(?:bash|sh|zsh|fish): .*command not found\b", "command not found"),
    (r"^\s*[\w./+-]+: command not found\b", "command not found"),
    (r"\b(?:can't open file|cannot open|failed to open|io error).*no such file or directory\b", "missing file or directory"),
    (r"^\s*(?:[\w./+-]+: )?.*\bpermission denied\b", "permission denied"),
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
    if value.get("isError") is True:
        return "tool-reported error"
    for key in ("exit_code", "exitCode", "returncode", "return_code", "status"):
        code = value.get(key)
        if isinstance(code, int) and code != 0:
            return f"nonzero command exit ({key}={code})"
        if isinstance(code, str) and code.lower() in {"error", "failed", "failure"}:
            return f"tool-reported failure ({key}={code})"
    return None


def _explicit_success(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("isError") is False:
        return True
    for key in ("exit_code", "exitCode", "returncode", "return_code", "status"):
        code = value.get(key)
        if isinstance(code, int):
            return code == 0
        if isinstance(code, str) and code.lower() in {"ok", "success", "succeeded", "passed"}:
            return True
    return False


def _should_scan_failure_phrases(payload: dict[str, Any], response_text: str) -> bool:
    tool_name = str(payload.get("tool_name", "")).lower()
    if tool_name in {"bash", "shell", "exec", "exec_command", "unified_exec"}:
        return True
    return "process exited with code" in response_text.lower()


def _diagnostic_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("+", "-", "@@", "diff --git ", "index ")):
            continue
        if stripped.startswith(('"', "'", "(", "[", "{")):
            continue
        lines.append(line)
    return lines


def _failure_reason_from_text(text: str) -> str | None:
    for line in _diagnostic_lines(text.lower()):
        for pattern, reason in FAILURE_PATTERNS:
            if re.search(pattern, line):
                return reason
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

    tool_response = payload.get("tool_response")
    response_text = _as_text(tool_response)
    explicit_failure = _explicit_failure(tool_response)
    if explicit_failure:
        _message(explicit_failure)
        return 0

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(response_text):
            _message(f"secret-looking output ({label})")
            return 0

    # Successful structured tool results can legitimately contain diagnostic
    # examples, source code, diffs, or benign probe chatter with words such as
    # "No such file or directory". Do not force the agent to explain those
    # strings unless the tool result itself failed.
    if _explicit_success(tool_response):
        return 0

    if not _should_scan_failure_phrases(payload, response_text):
        return 0

    failure_reason = _failure_reason_from_text(response_text)
    if failure_reason:
        _message(failure_reason)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
