# codex

This subtree preserves the Codex-specific part of the broader `agents-workbench` repository.

It combines three distinct concerns that are worth keeping durable:

- `dot-codex/`: sanitized mirror of the durable, human-managed parts of `~/.codex`
- `dot-agents/`: custom user-managed Codex skills from `~/.agents`
- `codexlab/`: durable workspace for evaluation, tuning, and real-task verification

## Subtree map

```text
codex/
├── dot-codex/
├── dot-agents/
└── codexlab/
```

## dot-codex

`dot-codex/` is not a full raw copy of `~/.codex`.
It intentionally keeps only the durable configuration and evaluation surfaces that are worth migrating or publishing, such as:

- `AGENTS.md`
- `config.toml`
- `agents/`
- `rules/`
- `templates/`
- `evals/`
- `README.md`
- `version.json` when helpful as environment context

It intentionally excludes local runtime state such as auth, history, sqlite state, caches, temporary files, shell snapshots, and local virtual environments.

## dot-agents

`dot-agents/` mirrors the custom skill layer from `~/.agents`.
This is where user-authored Codex behavior extensions live.

Treat it as human-managed content:

- keep skills small and well scoped
- document the purpose of each skill clearly
- avoid storing generated artifacts here

## codexlab

`codexlab/` is the durable task-and-evaluation workspace.
Use it for:

- reusable eval assets
- live task sandboxes worth preserving
- durable notes
- saved results and snapshots that are intentionally kept

Do not use `codexlab/` as a generic scratch directory.
Scratch work still belongs outside this repository until it becomes durable enough to preserve.

## Practical migration guidance

When moving this setup to another machine:

1. review the files in `dot-codex/` and `dot-agents/`
2. merge them into the target `~/.codex/` and `~/.agents/` deliberately
3. recreate any needed virtual environments locally
4. keep runtime state machine-local

The goal is reproducible setup, not byte-for-byte workstation cloning.
