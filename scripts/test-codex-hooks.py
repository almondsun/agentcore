#!/usr/bin/env python3
"""Regression tests for deterministic Codex hook scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRE_TOOL_GUARD = REPO_ROOT / 'openai' / 'dot-codex' / 'hooks' / 'pre_tool_guard.py'


def main() -> int:
    tests = [
        ('bash blocks dotenv read', bash('cat .env'), True),
        ('bash blocks pem read', bash('sed -n 1,5p ~/.ssh/client.pem'), True),
        ('bash blocks codex auth read', bash('python3 -c "print(open(\'~/.codex/auth.json\').read())"'), True),
        ('edit blocks dotenv path', tool('Edit', {'file_path': '.env.local', 'old_string': 'a', 'new_string': 'b'}), True),
        ('read blocks private ssh key', tool('Read', {'file_path': '/home/mitin/.ssh/id_ed25519'}), True),
        ('safe config grep remains allowed', bash("rg -n 'allow_login_shell' ~/.codex/config.toml"), False),
        ('safe ordinary edit remains allowed', tool('Edit', {'file_path': 'README.md', 'old_string': 'a', 'new_string': 'b'}), False),
    ]
    failures: list[str] = []
    for name, payload, should_block in tests:
        blocked, stdout = run_pre_tool_guard(payload)
        if blocked != should_block:
            failures.append(f'{name}: expected blocked={should_block}, got {blocked}; stdout={stdout!r}')
    if failures:
        print('hook regression tests failed:', file=sys.stderr)
        for failure in failures:
            print(f'- {failure}', file=sys.stderr)
        return 1
    print('hook regression tests passed')
    return 0


def bash(command: str) -> dict[str, object]:
    return tool('Bash', {'command': command})


def tool(name: str, tool_input: dict[str, object]) -> dict[str, object]:
    return {'tool_name': name, 'tool_input': tool_input}


def run_pre_tool_guard(payload: dict[str, object]) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(PRE_TOOL_GUARD)],
        input=json.dumps(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pre_tool_guard exited {result.returncode}: {result.stderr}')
    blocked = '"permissionDecision": "deny"' in result.stdout
    return blocked, result.stdout


if __name__ == '__main__':
    raise SystemExit(main())
