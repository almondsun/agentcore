#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="${1:-/tmp/codex-final-eval}"
RUN_DATE="${2:-2026-03-31}"

cd /home/marti/code/tmp

python3 /home/marti/.codex/evals/scripts/live_run_preflight.py --results-dir "${RESULTS_DIR}"
python3 /home/marti/.codex/evals/scripts/run_batch.py \
  wr-easy-local-bugfix \
  wr-medium-api-contract \
  wr-hard-security-audit \
  --date "${RUN_DATE}" \
  --results-dir "${RESULTS_DIR}" \
  --force
