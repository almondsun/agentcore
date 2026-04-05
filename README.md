# agents-workbench

`agents-workbench` is a personal, migration-friendly workspace for durable AI-agent configuration,
evaluation assets, and real-task verification material.

This repository is meant to preserve the parts of an agent setup that are worth versioning:

- human-managed Codex configuration and policy
- custom Codex skills
- durable evaluation assets
- reusable task sandboxes and notes
- documentation about how the environment is organized

It is not intended to be a raw home-directory backup.

## Current structure

```text
.
├── codex/
│   ├── dot-codex/
│   ├── dot-agents/
│   └── codexlab/
└── claude/
```

What each area means:

- `codex/dot-codex/`: sanitized mirror of the durable, human-managed parts of `~/.codex`.
- `codex/dot-agents/`: mirror of custom user-managed Codex skills from `~/.agents`.
- `codex/codexlab/`: durable evaluation and live-task workspace for Codex.
- `claude/`: reserved space for future non-Codex agent configuration; currently only documented, not populated.

## What is intentionally included

The Codex subtree keeps the durable pieces that are useful to migrate, review, or publish:

- `AGENTS.md`
- `config.toml`
- agent definition files
- rules and templates
- evaluation harness inputs and scripts
- custom skills from `~/.agents`
- the `codexlab` durable workspace

## What is intentionally excluded

This repository deliberately excludes local-only and sensitive state, including:

- authentication/session material
- local histories and transcripts by default
- sqlite state databases
- caches
- logs
- temporary directories
- local shell snapshots
- local virtual environments
- machine-specific runtime scratch state
- repo-local `.codex` sentinels from unrelated task repositories

If you need any of those for debugging, keep them local and out of version control.

## Migration intent

This repo is designed to help reconstruct a working environment on another Linux machine without copying raw runtime state.

The intended migration pattern is:

1. clone this repository
2. review `codex/README.md`
3. merge the desired files into real locations such as `~/.codex/` and `~/.agents/`
4. recreate virtual environments locally instead of copying them
5. keep caches, logs, and auth state machine-local

Do not blindly overwrite a live agent home directory without reviewing the target machine's existing configuration.

## Publishing note

Before publishing updates, review changes for:

- secrets or auth state
- private transcripts or snapshots
- machine-specific paths you do not want public
- live-task repositories that should remain private

This repo should read like a curated workbench, not a raw workstation dump.
