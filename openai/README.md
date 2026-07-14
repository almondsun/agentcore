# openai

This subtree preserves the OpenAI Codex-specific part of the broader `agentcore` repository.

It combines two distinct concerns that are worth keeping durable:

- `dot-codex/`: sanitized mirror of the durable, human-managed parts of `~/.codex`
- `dot-agents/`: custom user-managed Codex skills from `~/.agents`

## Subtree map

```text
openai/
├── dot-codex/
└── dot-agents/
```

## dot-codex

`dot-codex/` is not a full raw copy of `~/.codex`.
It intentionally keeps only durable configuration surfaces worth migrating or publishing, such as:

- `AGENTS.md`
- `config.toml`
- `agents/`
- `rules/`
- `hooks/`
- `README.md`
- `compatibility.json` as the maintained CLI/model compatibility contract

It intentionally excludes local runtime state such as auth, history, sqlite state, caches, temporary files, shell snapshots, and local virtual environments.

## dot-agents

`dot-agents/` mirrors the custom skill layer from `~/.agents`.
This is where user-authored Codex behavior extensions live.

Treat it as human-managed content:

- keep skills small and well scoped
- document the purpose of each skill clearly
- avoid storing generated artifacts here

## Practical migration guidance

When moving this setup to another machine:

1. review the files in `dot-codex/` and `dot-agents/`
2. merge them into the target `~/.codex/` and `~/.agents/` deliberately
3. recreate any needed virtual environments locally
4. keep runtime state machine-local

The goal is reproducible setup, not byte-for-byte workstation cloning.
