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
python3 scripts/bootstrap_codex_environment.py --validate-only

echo "== TOML parse =="
python3 - <<'PYTOML'
from pathlib import Path
import tomllib

paths = [
    Path('openai/dot-codex/config.toml'),
    Path.home() / '.codex' / 'config.toml',
]
for path in paths:
    with path.open('rb') as handle:
        tomllib.load(handle)
    print(f'ok {path}')
PYTOML

echo "== Codex version metadata =="
python3 - <<'PYVERSION'
import json
import shutil
import subprocess
from pathlib import Path

version_path = Path('openai/dot-codex/version.json')
metadata = json.loads(version_path.read_text(encoding='utf-8'))
expected = metadata.get('latest_version')
codex = shutil.which('codex')
if not codex:
    print('warning: codex binary not found; skipped version metadata check')
    raise SystemExit(0)
result = subprocess.run([codex, '--version'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
text = (result.stdout or result.stderr).strip()
if result.returncode != 0:
    raise SystemExit(f'codex --version failed: {text}')
actual = text.split()[-1] if text else ''
if expected != actual:
    raise SystemExit(f'version metadata mismatch: version.json has {expected!r}, installed Codex is {actual!r}')
print(f'ok codex-cli {actual}')
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
result = subprocess.run([codex, 'features', 'list'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
if result.returncode != 0:
    raise SystemExit(f'codex features list failed: {(result.stdout or result.stderr).strip()}')
removed = set()
deprecated = set()
for line in result.stdout.splitlines():
    parts = line.split()
    if len(parts) < 3:
        continue
    name, stage = parts[0], parts[1]
    if stage == 'removed':
        removed.add(name)
    elif stage == 'deprecated':
        deprecated.add(name)
bad_removed = sorted(enabled & removed)
bad_deprecated = sorted(enabled & deprecated)
if bad_removed:
    raise SystemExit('config enables removed Codex features: ' + ', '.join(bad_removed))
if bad_deprecated:
    raise SystemExit('config enables deprecated Codex features: ' + ', '.join(bad_deprecated))
print('ok no enabled removed/deprecated features')
PYFEATURES

echo "== mirror drift check =="
python3 scripts/check_codex_mirror.py

echo "== branch sync check =="
python3 scripts/check_branch_sync.py

echo "== hook regression tests =="
python3 scripts/test-codex-hooks.py

echo "== strict codex config load =="
codex exec --strict-config --json --sandbox read-only --skip-git-repo-check --cd "$repo_root" "$strict_prompt" >"$strict_output"
STRICT_OUTPUT="$strict_output" python3 - <<'PYCHECK'
from pathlib import Path
import os
text = Path(os.environ['STRICT_OUTPUT']).read_text(encoding='utf-8')
if '"text":"OK"' not in text:
    raise SystemExit('strict Codex validation did not return OK')
print('ok codex exec --strict-config')
PYCHECK

echo "validation passed"
