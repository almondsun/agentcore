#!/usr/bin/env python3
"""Check durable Codex setup files are synchronized across OS branches."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_BRANCHES = ('linux', 'windows')
DEFAULT_PATHS = (
    'docs/codex',
    'openai/dot-codex',
    'openai/dot-agents',
    'scripts',
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branches', nargs='+', default=list(DEFAULT_BRANCHES))
    parser.add_argument('--paths', nargs='+', default=list(DEFAULT_PATHS))
    args = parser.parse_args()

    base = args.branches[0]
    failures: list[str] = []
    for branch in args.branches[1:]:
        for path in args.paths:
            if tree_object(base, path) != tree_object(branch, path):
                failures.append(f'{path}: {base} differs from {branch}')

    if failures:
        print('branch sync check failed:', file=sys.stderr)
        for failure in failures:
            print(f'- {failure}', file=sys.stderr)
        return 1
    print('branch sync check passed')
    return 0


def tree_object(branch: str, path: str) -> str:
    result = subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'rev-parse', f'{branch}:{path}'],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return '<missing>'
    return result.stdout.strip()


if __name__ == '__main__':
    raise SystemExit(main())
