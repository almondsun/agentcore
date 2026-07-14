#!/usr/bin/env python3
"""Block high-confidence dangerous tool requests before they run."""

from __future__ import annotations

import json
import re
import shlex
import sys
from collections.abc import Iterable
from typing import Any


DANGEROUS_COMMAND_PATTERNS = [
    (r"(?i)(^|\s)rm\s+(?:-(?=[^\s;]*r)(?=[^\s;]*f)[^\s;]+|--recursive\s+--force|--force\s+--recursive)\s+(?:--\s+)?/(?:\s|$)", "recursive removal of filesystem root"),
    (r"(?i)(^|\s)rm\s+(?:-(?=[^\s;]*r)(?=[^\s;]*f)[^\s;]+|--recursive\s+--force|--force\s+--recursive)\s+(?:--\s+)?\$?HOME(?:\s|/|$)", "recursive removal of the home directory"),
    (r"(?i)(^|\s)chmod\s+-R\s+777\s+/(?:\s|$)", "world-writable permissions on filesystem root"),
    (r"(?i)(^|\s)mkfs(?:\.[A-Za-z0-9_-]+)?\s+", "filesystem formatting"),
    (r"(?i)(^|\s)dd\s+.*\bof=/dev/(?:sd|nvme|vd|hd)", "raw write to a block device"),
    (r":\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "fork bomb"),
]

SECRET_PATTERNS = [
    ("an OpenAI API key", re.compile(r"\bsk-(?:(?:proj|live|test)-)?[A-Za-z0-9_-]{20,}\b")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
]



SECRET_PATH_PATTERNS = [
    ("a dotenv file", re.compile(r"(?i)(^|[/\\])\.env(?:\.[A-Za-z0-9_-]+)?$")),
    ("a PEM key or certificate file", re.compile(r"(?i)(^|[/\\])[^/\\]+\.pem$")),
    ("a PKCS key/certificate bundle", re.compile(r"(?i)(^|[/\\])[^/\\]+\.(?:p12|pfx)$")),
    ("a private SSH key", re.compile(r"(?i)(^|[/\\])id_(?:rsa|dsa|ecdsa|ed25519)$")),
    ("Codex auth state", re.compile(r"(?i)(^|[/\\])auth\.json$")),
    ("a credentials file", re.compile(r"(?i)(^|[/\\])[^/\\]*(?:credential|credentials)[^/\\]*$")),
    ("a private-key path", re.compile(r"(?i)(^|[/\\])[^/\\]*private[-_]?key[^/\\]*$")),
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


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _candidate_path_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    try:
        tokens.extend(shlex.split(text))
    except ValueError:
        tokens.extend(text.split())
    # Capture paths embedded inside quoted Python/Ruby/JS snippets where shlex
    # keeps larger code fragments as one token.
    tokens.extend(re.findall(r"(?:~|\.|/|[A-Za-z0-9_$-]+)[A-Za-z0-9_.$~+@%:/\\-]*(?:\.env(?:\.[A-Za-z0-9_-]+)?|\.pem|\.p12|\.pfx|auth\.json|id_(?:rsa|dsa|ecdsa|ed25519)|credentials?)[A-Za-z0-9_.$~+@%:/\\-]*", text, flags=re.IGNORECASE))
    return tokens


def _secret_path_reason(tool_input: Any) -> str | None:
    for value in _iter_strings(tool_input):
        for token in _candidate_path_tokens(value):
            cleaned = token.strip('"\'`,;:()[]{}<>')
            for label, pattern in SECRET_PATH_PATTERNS:
                if pattern.search(cleaned):
                    return f"Blocked tool request because it references {label}: {cleaned}."
    return None


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

    secret_path_reason = _secret_path_reason(tool_input)
    if secret_path_reason:
        _block(secret_path_reason)
        return 0

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            _block(f"Blocked tool request because it appears to write or execute content containing {label}.")
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
