# AGENTS.md

## Purpose

This repository is the curated, versioned source for durable Codex configuration
and custom skills. It is not a raw home-directory backup.

Optimize for:

1. Correctness
2. Safety and security
3. Contract clarity
4. Validation evidence
5. Maintainability
6. Performance where justified
7. UX at interfaces
8. Style consistency

## Repository Map

- `openai/dot-codex/`: sanitized mirror of durable `~/.codex` configuration.
- `openai/dot-agents/`: custom user-managed Codex skills mirrored from
  `~/.agents`.

Do not commit local auth/session state, histories, sqlite databases, caches,
logs, shell snapshots, local virtual environments, or raw temporary directories.

## Operating Rules

- Prefer the nearest source of truth: local `README.md`, nested `AGENTS.md`, and
  task-specific files before generic assumptions.
- When working with OpenAI APIs, ChatGPT Apps SDK, Codex, or OpenAI platform
  documentation, use the `openaiDeveloperDocs` MCP first.
- Do not overwrite or revert unrelated user changes.
- Do not silently swallow errors.
- Do not change public contracts, persisted formats, wire formats, or binary
  interfaces without calling that out explicitly.
- Do not hand-edit generated code unless the task explicitly requires a
  regeneration-aware edit.
- Do not modify vendor or mirrored third-party code unless the task explicitly
  requires a vendor patch or update path.

## Validation

For non-trivial edits, identify the smallest correct validation path from the
affected area. Prefer repository-native commands over guesses. If a relevant
check cannot be run, report why and what remains unverified.

For config-only changes, at minimum parse changed TOML/JSON and run the closest
Codex CLI inspection command when available.

Agent behavior is validated in the real target repository with that
repository's own tests and review process. Keep scratch tasks and generated
behavioral evidence outside `agentcore`.

## Security

Treat trust boundaries, credentials, hooks, MCP/app permissions, subprocesses,
file paths, network access, parsers, and native memory safety as review-critical.
New automation should fail closed only for clearly dangerous actions and avoid
blocking ordinary development without a concrete risk.
