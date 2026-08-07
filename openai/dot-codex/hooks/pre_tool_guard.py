#!/usr/bin/env python3
"""Block high-confidence dangerous tool requests before they run."""

from __future__ import annotations

import json
import re
import shlex
import sys
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


def _looks_like_shell_path(token: str) -> bool:
    if token.startswith(("/", "./", "../", "~/", ".\\", "..\\", "~\\")):
        return True
    if "/" in token or "\\" in token:
        return True
    return bool(
        re.search(
            r"(?i)(?:\.env(?:\.[A-Za-z0-9_-]+)?|\.pem|\.p12|\.pfx|\.json|id_(?:rsa|dsa|ecdsa|ed25519))$",
            token,
        )
    )


def _structured_paths(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    paths: list[str] = []
    for key, item in value.items():
        normalized = str(key).lower().replace("-", "_")
        if normalized in {"path", "file", "file_path", "filepath", "target_path"}:
            if isinstance(item, str):
                paths.append(item)
            elif isinstance(item, list):
                paths.extend(entry for entry in item if isinstance(entry, str))
    return paths


def _patch_paths(command: str) -> list[str]:
    paths: list[str] = []
    for line in command.splitlines():
        match = re.match(r"\*\*\* (?:(?:Add|Update|Delete) File|Move to):\s*(.+?)\s*$", line)
        if match:
            paths.append(match.group(1))
    return paths


def _candidate_paths(tool_name: Any, tool_input: Any) -> list[str]:
    if not isinstance(tool_input, dict):
        return []
    command = tool_input.get("command")
    if tool_name == "Bash" and isinstance(command, str):
        return [
            token.strip('"\'`,;:()[]{}<>')
            for token in _candidate_path_tokens(command)
            if _looks_like_shell_path(token.strip('"\'`,;:()[]{}<>'))
        ]
    if tool_name == "apply_patch" and isinstance(command, str):
        return _patch_paths(command)
    return _structured_paths(tool_input)


def _secret_path_reason(tool_name: Any, tool_input: Any) -> str | None:
    for path in _candidate_paths(tool_name, tool_input):
        cleaned = path.strip('"\'`,;:()[]{}<>')
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

    secret_path_reason = _secret_path_reason(tool_name, tool_input)
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
