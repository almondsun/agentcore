#!/usr/bin/env python3
"""Regression tests for deterministic Codex hook scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRE_TOOL_GUARD = REPO_ROOT / 'openai' / 'dot-codex' / 'hooks' / 'pre_tool_guard.py'
HOOK_ROOT = REPO_ROOT / 'openai' / 'dot-codex' / 'hooks'
HOOK_CONFIG = REPO_ROOT / 'openai' / 'dot-codex' / 'hooks.json'


def main() -> int:
    tests = [
        ('bash blocks dotenv read', bash('cat .env'), True),
        ('bash blocks pem read', bash('sed -n 1,5p ~/.ssh/client.pem'), True),
        ('bash blocks codex auth read', bash('python3 -c "print(open(\'~/.codex/auth.json\').read())"'), True),
        ('edit blocks dotenv path', tool('Edit', {'file_path': '.env.local', 'old_string': 'a', 'new_string': 'b'}), True),
        ('read blocks private ssh key', tool('Read', {'file_path': '/home/mitin/.ssh/id_ed25519'}), True),
        ('safe config grep remains allowed', bash("rg -n 'allow_login_shell' ~/.codex/config.toml"), False),
        (
            'credential diagnostic regex remains allowed',
            bash("journalctl --user -b | rg -i \"invalid keyring|couldn't create credential|authentication required\""),
            False,
        ),
        (
            'patch prose about credentials remains allowed',
            tool(
                'apply_patch',
                {
                    'command': (
                        '*** Begin Patch\n*** Update File: README.md\n@@\n'
                        '-old\n+Credentials and private-key material stay local.\n*** End Patch'
                    )
                },
            ),
            False,
        ),
        ('safe ordinary edit remains allowed', tool('Edit', {'file_path': 'README.md', 'old_string': 'a', 'new_string': 'b'}), False),
        ('read blocks relative credentials file', tool('Read', {'file_path': 'config/credentials.json'}), True),
        ('bash blocks relative credentials file', bash('cat credentials.json'), True),
        ('patch blocks dotenv target', tool('apply_patch', {'command': '*** Begin Patch\n*** Update File: .env\n@@\n-a\n+b\n*** End Patch'}), True),
        ('patch blocks move to dotenv target', tool('apply_patch', {'command': '*** Begin Patch\n*** Update File: config.txt\n*** Move to: .env\n@@\n-a\n+b\n*** End Patch'}), True),
        ('bash blocks rm flag permutation', bash('rm -fr /'), True),
        ('bash blocks legacy OpenAI key', bash('tool --token ' + 's' + 'k-' + 'A' * 40), True),
    ]
    failures: list[str] = []
    for name, payload, should_block in tests:
        blocked, stdout = run_pre_tool_guard(payload)
        if blocked != should_block:
            failures.append(f'{name}: expected blocked={should_block}, got {blocked}; stdout={stdout!r}')
    failures.extend(test_hook_protocols())
    failures.extend(test_isolated_launchers())
    failures.extend(test_hostile_git_config())
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
    return run_hook(PRE_TOOL_GUARD, payload, '"permissionDecision": "deny"')


def run_hook(
    script: Path, payload: dict[str, object], decision_marker: str
) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, '-I', '-S', str(script)],
        input=json.dumps(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pre_tool_guard exited {result.returncode}: {result.stderr}')
    blocked = decision_marker in result.stdout
    return blocked, result.stdout


def test_hook_protocols() -> list[str]:
    failures: list[str] = []
    prompt_guard = HOOK_ROOT / 'user_prompt_secret_guard.py'
    blocked, _ = run_hook(
        prompt_guard,
        {'prompt': 'value ' + 's' + 'k-' + 'A' * 40},
        '"decision": "block"',
    )
    if not blocked:
        failures.append('user prompt guard did not block a legacy OpenAI key shape')

    permission_guard = HOOK_ROOT / 'permission_request_guard.py'
    blocked, _ = run_hook(
        permission_guard,
        {'tool_input': {'command': 'rm -fr /'}},
        '"behavior": "deny"',
    )
    if not blocked:
        failures.append('permission guard did not block rm -fr /')

    post_hook = HOOK_ROOT / 'post_tool_hygiene.py'
    _, stdout = run_hook(
        post_hook,
        {
            'tool_name': 'exec_command',
            'tool_response': {'exit_code': 0, 'output': 'Traceback example in source'},
        },
        '"systemMessage"',
    )
    if stdout:
        failures.append('post-tool hook produced a false warning for successful source output')
    warned, _ = run_hook(
        post_hook,
        {'tool_name': 'exec_command', 'tool_response': {'exit_code': 1, 'output': 'failed'}},
        '"systemMessage"',
    )
    if not warned:
        failures.append('post-tool hook did not report a structured nonzero exit')
    return failures


def test_isolated_launchers() -> list[str]:
    failures: list[str] = []
    config = json.loads(HOOK_CONFIG.read_text(encoding='utf-8'))
    for event, groups in config['hooks'].items():
        for group in groups:
            for hook in group['hooks']:
                if ' -I -S -c ' not in hook['command']:
                    failures.append(f'{event} Unix hook is not isolated')
                if not hook['command'].startswith('{{PYTHON_EXECUTABLE_POSIX}} '):
                    failures.append(f'{event} Unix hook lacks bootstrap-rendered interpreter')
                if ' -I -S -c ' not in hook.get('commandWindows', ''):
                    failures.append(f'{event} Windows hook is not isolated')
                if not hook.get('commandWindows', '').startswith('{{PYTHON_EXECUTABLE}} '):
                    failures.append(f'{event} Windows hook lacks bootstrap-rendered interpreter')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        marker = root / 'imported'
        (root / 'sitecustomize.py').write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
            encoding='utf-8',
        )
        subprocess.run(
            [sys.executable, '-I', '-S', '-c', 'import json; print(json.dumps({"ok": True}))'],
            cwd=root,
            env={**os.environ, 'PYTHONPATH': str(root)},
            check=True,
            capture_output=True,
            text=True,
        )
        if marker.exists():
            failures.append('isolated Python launcher imported workspace sitecustomize.py')
    return failures


def test_hostile_git_config() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        marker = root / 'fsmonitor-ran'
        monitor = root / 'monitor.py'
        monitor.write_text(
            f"#!/usr/bin/env python3\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
            encoding='utf-8',
        )
        monitor.chmod(0o700)
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        subprocess.run(
            ['git', 'config', 'core.fsmonitor', str(monitor)], cwd=root, check=True
        )
        run_hook(
            HOOK_ROOT / 'session_start_context.py',
            {'source': 'startup', 'cwd': str(root)},
            '"additionalContext"',
        )
        if marker.exists():
            failures.append('session hook executed repo-controlled core.fsmonitor')
    return failures


if __name__ == '__main__':
    raise SystemExit(main())
