#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="${1:-/tmp/codex-final-eval}"
RUN_DATE="${2:-2026-03-31}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/live_run_preflight.py" --results-dir "${RESULTS_DIR}"
python3 "${SCRIPT_DIR}/run_batch.py" \
  wr-easy-local-bugfix \
  wr-medium-api-contract \
  wr-hard-security-audit \
  --date "${RUN_DATE}" \
  --results-dir "${RESULTS_DIR}" \
  --force
