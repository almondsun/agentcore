# agentcore

`agentcore` is a personal, migration-friendly workspace for durable OpenAI Codex configuration and custom skills.

This repository is meant to preserve the parts of an agent setup that are worth versioning:

- human-managed agent configuration and policy
- custom agent skills and workflow extensions
- documentation about how the environment is organized

It is not intended to be a raw home-directory backup.

## Project health

Pull requests are validated on Linux and Windows with Python 3.11 and 3.13.
GitHub CodeQL, dependency review, secret scanning, Dependabot, CODEOWNERS, issue
forms, and private vulnerability reporting provide the repository maintenance
baseline. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Current structure

```text
.
├── .github/
└── openai/
    ├── dot-codex/
    └── dot-agents/
```

What each area means:

- `openai/dot-codex/`: sanitized mirror of the durable, human-managed parts of `~/.codex`.
- `openai/dot-agents/`: mirror of custom user-managed Codex skills from `~/.agents`.

## What is intentionally included

The OpenAI subtree keeps the durable pieces that are useful to migrate, review, or publish:

- `AGENTS.md`
- `config.toml`
- top-level Codex profile files such as `review.config.toml`
- agent definition files
- rules and lifecycle hooks
- custom skills from `~/.agents`

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

## Real-task validation

Validate agent behavior in the actual repository where the work happens, using
that repository's instructions, tests, review process, and security boundaries.
`agentcore` validates the portable configuration and static integrity of its
skills; it does not store synthetic scorecards, task specimens, or run results.
Keep disposable experiments and generated evidence outside this repository.

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

To install the curated developer plugins as an explicit opt-in, add
`--install-recommended-plugins` to both commands. Plugin authentication and
runtime caches remain local to the target machine.

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
`%USERPROFILE%\.codex\hooks.json` contains the bootstrap-rendered absolute
Python executable. Do not replace it with a bare `python` command.

## Publishing note

Before publishing updates, review changes for:

- secrets or auth state
- private transcripts or snapshots
- machine-specific paths you do not want public

This repo should read like a curated workbench, not a raw workstation dump.
