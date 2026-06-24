# Branch Sync Contract

`agentcore` keeps durable Codex setup material synchronized across OS branches.
The current checker compares these paths between `linux` and `windows`:

- `docs/codex`
- `openai/dot-codex`
- `openai/dot-agents`
- `scripts`

Run:

```bash
python3 scripts/check_branch_sync.py
```

## Expected Workflow

When the check fails after a Linux-side Codex setup change:

1. finish and validate the Linux branch change
2. switch to or create the corresponding Windows sync branch
3. replay the durable Codex setup changes onto the Windows branch
4. run the Windows-safe validation commands from `README.md`
5. rerun `python3 scripts/check_branch_sync.py` from both branches when possible

Do not weaken the checker to pass while durable setup files differ. If an
intentional OS-specific divergence is needed, narrow the check by path or add a
documented exception in the script with the reason and expected reconciliation
path.

## Current Limitation

The checker is intentionally strict. It does not perform synchronization; it
only reports drift. Synchronizing another branch may require a separate working
tree or checkout, and should not be hidden inside ordinary config validation.
