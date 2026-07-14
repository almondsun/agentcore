#!/usr/bin/env python3
"""Check that the live ~/.codex setup has not drifted from the agentcore mirror.

The live config is allowed to contain machine-local generated state such as
trusted project paths, writable scratch roots, model availability nux state, and
absolute filesystem read grants for installed runtimes or skills.
"""

from __future__ import annotations

import argparse
import filecmp
import pprint
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from bootstrap_codex_environment import build_rendered_hooks_config

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
MIRROR_CODEX = REPO_ROOT / 'openai' / 'dot-codex'
DEFAULT_LIVE_CODEX = Path.home() / '.codex'
MANAGED_RELATIVE_FILES = [
    Path('AGENTS.md'),
    Path('README.md'),
]
MANAGED_RELATIVE_DIRS = [
    Path('agents'),
    Path('hooks'),
    Path('rules'),
    Path('templates'),
    Path('evals'),
]
SKIP_NAMES = {'__pycache__'}
SKIP_SUFFIXES = {'.pyc', '.pyo'}
AGENTCORE_PERMISSION_PROFILE = 'agentcore_workspace'


class Drift:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def add(self, message: str) -> None:
        self.messages.append(message)

    def ok(self) -> bool:
        return not self.messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-codex', type=Path, default=DEFAULT_LIVE_CODEX)
    parser.add_argument('--skip-files', action='store_true', help='only compare normalized config')
    args = parser.parse_args()

    drift = Drift()
    compare_config(args.live_codex, drift)
    if not args.skip_files:
        compare_managed_files(args.live_codex, drift)
        compare_profile_files(args.live_codex, drift)

    if drift.ok():
        print('codex mirror check passed')
        return 0
    print('codex mirror drift detected:', file=sys.stderr)
    for message in drift.messages:
        print(f'- {message}', file=sys.stderr)
    return 1


def compare_config(live_codex: Path, drift: Drift) -> None:
    if tomllib is None:
        drift.add('Python tomllib is unavailable; use Python 3.11+')
        return
    mirror_path = MIRROR_CODEX / 'config.toml'
    live_path = live_codex / 'config.toml'
    if not live_path.exists():
        drift.add(f'missing live config: {live_path}')
        return
    mirror = normalize_config(load_toml(mirror_path))
    live = normalize_config(load_toml(live_path))
    if mirror != live:
        drift.add(
            'normalized config differs between mirror and live config\n'
            f'mirror={pprint.pformat(mirror, sort_dicts=True)}\n'
            f'live={pprint.pformat(live, sort_dicts=True)}'
        )


def normalize_config(data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(data)
    result.pop('projects', None)
    result.pop('plugins', None)

    tui = result.get('tui')
    if isinstance(tui, dict):
        tui.pop('model_availability_nux', None)

    hooks = result.get('hooks')
    if isinstance(hooks, dict):
        hooks.pop('state', None)
        if not hooks:
            result.pop('hooks', None)

    permissions = result.get('permissions')
    if isinstance(permissions, dict):
        profile = permissions.get(AGENTCORE_PERMISSION_PROFILE)
        if isinstance(profile, dict):
            profile.pop('workspace_roots', None)
            filesystem = profile.get('filesystem')
            if isinstance(filesystem, dict):
                for key in list(filesystem):
                    if key.startswith('/') or key.startswith('~'):
                        filesystem.pop(key, None)
                if not filesystem:
                    profile.pop('filesystem', None)
    return result


def compare_managed_files(live_codex: Path, drift: Drift) -> None:
    for rel in MANAGED_RELATIVE_FILES:
        compare_file(MIRROR_CODEX / rel, live_codex / rel, rel, drift)
    live_hooks = live_codex / 'hooks.json'
    if not live_hooks.exists():
        drift.add('missing live managed file: hooks.json')
    elif live_hooks.read_text(encoding='utf-8') != build_rendered_hooks_config():
        drift.add('managed file differs: hooks.json')
    for rel_dir in MANAGED_RELATIVE_DIRS:
        mirror_dir = MIRROR_CODEX / rel_dir
        if not mirror_dir.exists():
            continue
        for mirror_path in sorted(path for path in mirror_dir.rglob('*') if path.is_file()):
            rel = mirror_path.relative_to(MIRROR_CODEX)
            if should_skip(rel):
                continue
            compare_file(mirror_path, live_codex / rel, rel, drift)


def compare_profile_files(live_codex: Path, drift: Drift) -> None:
    mirror_profiles = {path.name: path for path in MIRROR_CODEX.glob('*.config.toml')}
    for name, mirror_path in sorted(mirror_profiles.items()):
        compare_file(mirror_path, live_codex / name, Path(name), drift)


def should_skip(rel: Path) -> bool:
    return bool(set(rel.parts) & SKIP_NAMES) or rel.suffix in SKIP_SUFFIXES


def compare_file(mirror_path: Path, live_path: Path, rel: Path, drift: Drift) -> None:
    if not live_path.exists():
        drift.add(f'missing live managed file: {rel}')
        return
    if not filecmp.cmp(mirror_path, live_path, shallow=False):
        drift.add(f'managed file differs: {rel}')


def load_toml(path: Path) -> dict[str, Any]:
    with path.open('rb') as handle:
        return tomllib.load(handle)


if __name__ == '__main__':
    raise SystemExit(main())
