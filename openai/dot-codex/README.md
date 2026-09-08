# dot-codex

`dot-codex/` is a sanitized mirror of the durable, human-managed parts of the Codex home directory.

It exists to preserve configuration worth migrating or reviewing, without bundling the private and machine-local runtime state that accumulates in a live `~/.codex` directory.

## Included here

This mirror intentionally keeps the parts of the Codex environment that are useful to version:

- `AGENTS.md`: the global operating standard for Codex work
- `config.toml`: Codex runtime configuration and policy
- `*.config.toml`: Codex 0.134.0+ profile overlays selected with `--profile`
- `agents/`: specialist agent definitions
- `hooks.json` and `hooks/`: deterministic lifecycle guardrails for prompt
  secret scanning, high-risk approval annotation, and validation closeout nudges
- `rules/`: durable rule files
- `README.md`: environment-map documentation
- `compatibility.json`: maintained CLI/model compatibility contract for this baseline
- `recommended-plugins.json`: opt-in curated plugin identifiers without caches or auth

## Intentionally excluded

This mirror deliberately omits local-only runtime state, including:

- authentication and session state
- histories and local transcripts
- sqlite state databases
- caches
- logs
- shell snapshots
- temporary directories
- machine-local virtual environments
- system-provided skills copied from the runtime installation

Those artifacts are part of a live workstation, not part of a portable workbench repo.

## Relationship to dot-agents

Custom user-authored skills are not kept here.
They live in the sibling [dot-agents](../dot-agents/README.md) subtree, which mirrors `~/.agents`.

Use this split:

- `dot-codex/` for durable Codex-managed configuration
- `dot-agents/` for user-authored skills and related custom behavior

## Migration guidance

When using this mirror on another machine:

1. prefer the repo-root `CODEX_AUTONOMOUS_SETUP.txt` entrypoint
2. compare it against the target machine's existing `~/.codex/`
3. merge human-managed files deliberately instead of blindly replacing the directory
4. recreate runtime state locally as needed
5. keep secrets, sessions, caches, and logs machine-local

`config.toml` and the top-level `*.config.toml` profile files are intentionally
portable. Keep trusted project paths, local plugin availability, and
target-machine workspace roots or filesystem read grants in the live
`~/.codex/config.toml`, generated under the `agentcore_workspace` permission
profile for the current machine.

The bootstrap normally leaves plugin installations untouched. Pass
`--install-recommended-plugins` to install or refresh the curated developer set
declared by `recommended-plugins.json`; this never removes other plugins or
versions plugin authentication and runtime caches.

The purpose of this directory is reproducibility and documentation, not full workstation cloning.
