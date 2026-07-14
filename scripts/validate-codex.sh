#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

strict_prompt='Reply exactly OK.'
strict_output="$(mktemp -t agentcore-codex-strict.XXXXXX.jsonl)"
trap 'rm -f "$strict_output"' EXIT

echo "== codex doctor =="
if ! codex doctor --summary --no-color --ascii; then
  echo "warning: codex doctor reported live environment issues; continuing with local deterministic checks" >&2
fi

echo "== bootstrap validation =="
python3 -B scripts/bootstrap_codex_environment.py --validate-only

echo "== TOML parse =="
python3 - <<'PYTOML'
from pathlib import Path
import tomllib

paths = [
    Path('openai/dot-codex/config.toml'),
    Path.home() / '.codex' / 'config.toml',
]
paths.extend(sorted(Path('openai/dot-codex').glob('*.config.toml')))
paths.extend(sorted((Path.home() / '.codex').glob('*.config.toml')))
for path in paths:
    with path.open('rb') as handle:
        tomllib.load(handle)
    print(f'ok {path}')
PYTOML

echo "== Codex compatibility metadata =="
python3 -B scripts/validate-compatibility.py
python3 - <<'PYVERSION'
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

compatibility_path = Path('openai/dot-codex/compatibility.json')
metadata = json.loads(compatibility_path.read_text(encoding='utf-8'))
minimum = metadata.get('minimum_codex_cli')
tested = metadata.get('tested_codex_cli')
config = tomllib.loads(Path('openai/dot-codex/config.toml').read_text(encoding='utf-8'))
if metadata.get('default_model') != config.get('model'):
    raise SystemExit('compatibility default_model does not match config.toml model')

def version_tuple(value):
    return tuple(int(part) for part in value.split('.') if part.isdigit())

codex = shutil.which('codex')
if not codex:
    print('warning: codex binary not found; skipped compatibility check')
    raise SystemExit(0)
result = subprocess.run([codex, '--version'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
text = (result.stdout or result.stderr).strip()
if result.returncode != 0:
    raise SystemExit(f'codex --version failed: {text}')
actual = text.split()[-1] if text else ''
if not minimum or version_tuple(actual) < version_tuple(minimum):
    raise SystemExit(f'Codex {actual!r} is older than required minimum {minimum!r}')
if tested and actual != tested:
    print(f'warning: Codex {actual} satisfies the minimum but differs from tested version {tested}')
print(f'ok codex-cli {actual} (minimum {minimum}, tested {tested})')
PYVERSION

echo "== Codex feature compatibility =="
python3 - <<'PYFEATURES'
import shutil
import subprocess
import tomllib
from pathlib import Path

codex = shutil.which('codex')
if not codex:
    print('warning: codex binary not found; skipped feature compatibility check')
    raise SystemExit(0)
config = tomllib.loads(Path('openai/dot-codex/config.toml').read_text(encoding='utf-8'))
enabled = {name for name, value in config.get('features', {}).items() if value is True}
try:
    result = subprocess.run(
        [codex, 'features', 'list'],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
except subprocess.TimeoutExpired:
    print('warning: codex features list timed out; skipped feature compatibility check')
    raise SystemExit(0)
if result.returncode != 0:
    raise SystemExit(f'codex features list failed: {(result.stdout or result.stderr).strip()}')
removed = set()
deprecated = set()
unstable = set()
for line in result.stdout.splitlines():
    parts = line.split()
    if len(parts) < 3:
        continue
    name, stage = parts[0], parts[1]
    if stage == 'removed':
        removed.add(name)
    elif stage == 'deprecated':
        deprecated.add(name)
    elif stage in {'experimental', 'under'}:
        unstable.add(name)
bad_removed = sorted(enabled & removed)
bad_deprecated = sorted(enabled & deprecated)
bad_unstable = sorted(enabled & unstable)
if bad_removed:
    raise SystemExit('config enables removed Codex features: ' + ', '.join(bad_removed))
if bad_deprecated:
    raise SystemExit('config enables deprecated Codex features: ' + ', '.join(bad_deprecated))
if bad_unstable:
    raise SystemExit('config enables experimental/under-development Codex features: ' + ', '.join(bad_unstable))
print('ok no enabled removed/deprecated/unstable features')
PYFEATURES

echo "== eval catalog and baseline validation =="
python3 -B openai/dot-codex/evals/scripts/eval_harness.py validate

echo "== mirror drift check =="
python3 -B scripts/check_codex_mirror.py

echo "== branch sync check =="
if git diff --quiet && git diff --cached --quiet; then
  python3 -B scripts/check_branch_sync.py
else
  if ! python3 scripts/check_branch_sync.py; then
    echo "warning: branch sync check failed while worktree is dirty; treat this as a pre-commit/publish gate" >&2
  fi
fi

echo "== bootstrap config regression tests =="
python3 -B scripts/test-bootstrap-config.py

echo "== hook regression tests =="
python3 -B scripts/test-codex-hooks.py

echo "== eval runner regression tests =="
python3 -B scripts/test-eval-runner.py

echo "== fixture and live-task tests =="
python3 -B scripts/test-python-projects.py

echo "== strict codex config load =="
codex exec --strict-config --json --config default_permissions='":read-only"' --skip-git-repo-check --cd "$repo_root" "$strict_prompt" >"$strict_output"
STRICT_OUTPUT="$strict_output" python3 - <<'PYCHECK'
from pathlib import Path
import os
text = Path(os.environ['STRICT_OUTPUT']).read_text(encoding='utf-8')
if '"text":"OK"' not in text:
    raise SystemExit('strict Codex validation did not return OK')
print('ok codex exec --strict-config')
PYCHECK

echo "validation passed"
