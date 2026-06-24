# Codex Setup Notes

This directory documents operational conventions for the checked-in Codex setup.
The live source of truth is still the installed Codex CLI plus the mirrored files
under `openai/dot-codex/`.

- `config-compat.md`: version-sensitive config/profile rules and validation commands.
- `branch-sync.md`: durable setup parity contract for Linux and Windows
  branches.
- `install-health.md`: how to diagnose and fix local Codex install/update
  target mismatches.
- `managed-config.md`: boundary between this portable baseline and
  organization-managed `requirements.toml` policy.
- `profiles.md`: contract for when each Codex profile should be used.
- `session-controls.md`: repo-specific use of current Codex slash commands for
  long-running work.
- `workflow.md`: day-to-day helper scripts and branch/worktree conventions.
