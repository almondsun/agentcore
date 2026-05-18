#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

strict_prompt='Reply exactly OK.'
strict_output="$(mktemp -t agentcore-codex-strict.XXXXXX.jsonl)"
trap 'rm -f "$strict_output"' EXIT

echo "== codex doctor =="
codex doctor --summary --no-color --ascii

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
