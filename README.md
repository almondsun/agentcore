# agentcore

`agentcore` is a personal, migration-friendly workspace for durable AI-agent configuration, evaluation assets, and real-task verification material.

This repository is meant to preserve the parts of an agent setup that are worth versioning:

- human-managed agent configuration and policy
- custom agent skills and workflow extensions
- durable evaluation assets
- reusable task sandboxes and notes
- documentation about how the environment is organized

It is not intended to be a raw home-directory backup.

## Current structure

```text
.
├── openai/
│   ├── dot-codex/
│   ├── dot-agents/
│   └── lab/
└── anthropic/
```

What each area means:

- `openai/dot-codex/`: sanitized mirror of the durable, human-managed parts of `~/.codex`.
- `openai/dot-agents/`: mirror of custom user-managed Codex skills from `~/.agents`.
- `openai/lab/`: durable evaluation and live-task workspace for OpenAI Codex-related work.
- `anthropic/`: reserved space for future Anthropic-specific configuration and evaluation assets.

## What is intentionally included

The OpenAI subtree keeps the durable pieces that are useful to migrate, review, or publish:

- `AGENTS.md`
- `config.toml`
- agent definition files
- rules and templates
- evaluation harness inputs and scripts
- custom skills from `~/.agents`
- the durable lab workspace

## What is intentionally excluded

This repository deliberately excludes local-only and sensitive state, including:

- authentication and session material
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

This repo is designed to help reconstruct a working environment on another compatible machine without copying raw runtime state.

The autonomous migration entrypoint is:

```text
Read CODEX_AUTONOMOUS_SETUP.txt first, then follow it autonomously.
```

That file points Codex at `scripts/bootstrap_codex_environment.py`, which
installs the portable baseline and generates target-machine local config under
the `agentcore_workspace` permission profile, such as trusted checkout path,
`~/.codex/tmp`, and any Codex runtime read grant needed by the sandbox. It also
grants the sandbox read-only access to installed skill roots that exist on that
target machine, such as `~/.agents/skills` and system skills under
`~/.codex/skills/.system`.

The manual migration pattern is:

1. clone this repository
2. review the relevant subtree documentation such as `openai/README.md`
3. merge the desired files into real locations such as `~/.codex/` and `~/.agents/`
4. recreate virtual environments locally instead of copying them
5. keep caches, logs, auth state, and other runtime artifacts machine-local

Do not blindly overwrite a live agent home directory without reviewing the target machine's existing configuration.

## Setting up Codex on a new Windows machine

Use this repository as the portable baseline for a fresh Windows Codex setup.
The bootstrap process installs the durable files from `openai/dot-codex/` into
`%USERPROFILE%\.codex\` and custom skills from `openai/dot-agents/` into
`%USERPROFILE%\.agents\`, while preserving machine-local configuration and
backing up replaced files.

Prerequisites:

- Git for Windows
- Python 3.11 or newer available as `python`
- Codex installed and signed in on the target machine

Important Windows note: do not rely on `python3` unless you have explicitly
configured it. On a stock Windows install, `python3` may be a Microsoft Store
execution alias that exits with code 1. Use `python` for this repository's
bootstrap and validation commands.

From PowerShell:

```powershell
mkdir $env:USERPROFILE\gh
cd $env:USERPROFILE\gh
git clone https://github.com/almondsun/agentcore.git
cd agentcore
python scripts\bootstrap_codex_environment.py --dry-run
python scripts\bootstrap_codex_environment.py
```

The dry run should be reviewed first on machines that already have a
`%USERPROFILE%\.codex\config.toml` or `%USERPROFILE%\.agents\` directory. The
real run creates timestamped backups under
`%USERPROFILE%\.codex-agentcore-backups\` before replacing existing durable
files.

After bootstrap, run the closest local validation:

```powershell
python scripts\bootstrap_codex_environment.py --validate-only
codex --version
```

Then start Codex from the cloned `agentcore` checkout once so it can read the
repo-specific instructions and trust the current checkout path. If hook popups
mention any hook exiting with code 1, check that
`%USERPROFILE%\.codex\hooks.json` uses the checked-in Windows-safe hook
launcher and that `python --version` succeeds.

## Publishing note

Before publishing updates, review changes for:

- secrets or auth state
- private transcripts or snapshots
- machine-specific paths you do not want public
- live-task repositories that should remain private

This repo should read like a curated workbench, not a raw workstation dump.
