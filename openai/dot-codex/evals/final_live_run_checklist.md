# Final Workflow-Realism Live-Run Checklist

Use this checklist to make the final `workflow-realism` scorecard runnable end to end.

This pack does not change the harness. It only addresses the current live-run blockers:

- Codex backend connectivity for `codex exec`
- `pytest` availability in the same Python environment used by the harness

## 1. Manual Environment Checks

These are operator tasks outside Codex when the current environment blocks network access.

### 1.1 Codex backend connectivity

The live run requires `codex exec` to reach:

- `wss://chatgpt.com/backend-api/codex/responses`
- `https://chatgpt.com/backend-api/wham/apps`
- `https://developers.openai.com/mcp`
- `https://mcp.context7.com/mcp`

If your environment uses firewall, proxy, DNS filtering, container policy, or websocket restrictions, allow outbound access for the Codex CLI to those endpoints.

### 1.2 Python validation toolchain

The harness uses `/usr/bin/python3` in the current environment. `pytest` must be installed in that same interpreter environment.

Verify the interpreter:

```bash
/usr/bin/python3 --version
```

Install `pytest` into that interpreter environment using your normal package-management policy. Example:

```bash
/usr/bin/python3 -m pip install pytest
```

If your environment requires `pip3`:

```bash
pip3 install pytest
```

If your environment requires a virtual environment, activate it first and make sure the harness will use that same `python3`.

## 2. Exact Verification Commands

Run these manually after fixing the environment.

### 2.1 Verify Codex CLI is present

```bash
codex --version
```

### 2.2 Verify Codex backend connectivity

Run from `/home/marti/code/tmp`:

```bash
codex exec --skip-git-repo-check --ephemeral --color never --sandbox read-only -c 'approval_policy="never"' -
```

Then provide this input:

```text
Return exactly the word ok.
```

Expected success signal:

- the command exits successfully
- the final output includes exactly `ok`

If it hangs, times out, or shows websocket / DNS / `Operation not permitted` errors, stop and fix the network policy first.

### 2.3 Verify pytest in the harness interpreter

```bash
/usr/bin/python3 -m pytest --version
```

### 2.4 Verify final fixture readiness

```bash
/usr/bin/python3 -m pytest --collect-only -q /home/marti/.codex/evals/fixtures/tiny-workflow-easy
/usr/bin/python3 -m pytest --collect-only -q /home/marti/.codex/evals/fixtures/tiny-workflow-medium
/usr/bin/python3 -m pytest --collect-only -q /home/marti/.codex/evals/fixtures/tiny-workflow-hard
```

## 3. Codex-Automatable Steps

After the environment is fixed, Codex can run:

```bash
python3 /home/marti/.codex/evals/scripts/live_run_preflight.py --results-dir /tmp/codex-final-eval
python3 /home/marti/.codex/evals/scripts/run_batch.py wr-easy-local-bugfix wr-medium-api-contract wr-hard-security-audit --date 2026-03-31 --results-dir /tmp/codex-final-eval --force
```

## 4. Stop/Go Sequence

### Stop

If this command fails:

```bash
python3 /home/marti/.codex/evals/scripts/live_run_preflight.py --results-dir /tmp/codex-final-eval
```

do not run the final batch. Read the reported `blockers` and fix them first.

### Go

If the preflight returns `ok: true`, run:

```bash
python3 /home/marti/.codex/evals/scripts/run_batch.py wr-easy-local-bugfix wr-medium-api-contract wr-hard-security-audit --date 2026-03-31 --results-dir /tmp/codex-final-eval --force
```

## 5. Recommended Command Sequence

```bash
cd /home/marti/code/tmp
python3 /home/marti/.codex/evals/scripts/live_run_preflight.py --results-dir /tmp/codex-final-eval
python3 /home/marti/.codex/evals/scripts/run_batch.py wr-easy-local-bugfix wr-medium-api-contract wr-hard-security-audit --date 2026-03-31 --results-dir /tmp/codex-final-eval --force
```
