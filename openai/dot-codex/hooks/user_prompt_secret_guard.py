#!/usr/bin/env python3
"""Block prompts that appear to contain pasted credentials."""

from __future__ import annotations

import json
import re
import sys


SECRET_PATTERNS = [
    ("an OpenAI API key", re.compile(r"\bsk-(?:(?:proj|live|test)-)?[A-Za-z0-9_-]{20,}\b")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    (
        "a credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password|private[_-]?key)\s*[:=]\s*['\"]?[^'\"\s]{12,}"
        ),
    ),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    prompt = payload.get("prompt") or ""
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(prompt):
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": (
                            f"Prompt appears to contain {label}. Remove the secret, rotate it if it was real, "
                            "and retry with a redacted value."
                        ),
                    }
                )
            )
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
