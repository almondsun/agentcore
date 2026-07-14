# Codex Workflow Helpers

## Full health check

```bash
scripts/validate-codex.sh
```

This runs `codex doctor`, bootstrap validation, TOML parsing, Codex compatibility
and feature checks, semantic eval-catalog validation, live-vs-mirror drift checks,
branch sync checks, bootstrap and hook regression tests, and a strict
non-interactive Codex config load.

`codex doctor` checks live network, provider, MCP, and WebSocket reachability.
The script reports doctor failures but continues with deterministic local checks
so a restricted sandbox does not hide config regressions.

If doctor reports an install/update target mismatch, use
`docs/codex/install-health.md`. That is a local launcher/package-manager issue,
not a Codex config parse failure.

## Live mirror drift

```bash
python3 scripts/check_codex_mirror.py
```

The checker compares durable mirrored files with the live `~/.codex` setup while
ignoring expected machine-local config such as trusted project paths and absolute
runtime read grants generated under the `agentcore_workspace` permission profile.

## Branch synchronization

```bash
python3 scripts/check_branch_sync.py
```

The checker ensures durable Codex setup paths are synchronized between the
`linux` and `windows` branches.

## Worktree cleanup

```bash
scripts/cleanup-worktrees.sh --list
scripts/cleanup-worktrees.sh --remove /home/user/code/agentcore-windows-patch
```

Removal refuses dirty worktrees and refuses to remove the primary checkout.

## Strict read-only launch

```bash
scripts/codex-readonly.sh
```

This starts Codex with the `readonly` profile, read-only sandboxing, and an
explicit top-level `allow_login_shell=false` override.
