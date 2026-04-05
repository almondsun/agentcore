# Custom Codex Skills

This directory is the user-managed home for custom Codex skills.

## Purpose

Use `~/.agents/skills` for skills you author, tune, or maintain directly.
These skills extend Codex with workflows, review patterns, and domain-specific guidance that are specific to your environment.

## Current layout

- `skills/`: custom skill directories, each containing a `SKILL.md` file and any optional supporting assets.

Current custom skills include:

- `build-validate`
- `interop-review`
- `openai-knowledge`
- `orchestrated-implementation`
- `orchestrated-review`
- `pr-draft-summary`
- `security-review`
- `structured-review-record`

## Relationship to ~/.codex

The Codex environment is split intentionally:

- `/home/marti/.codex/skills/.system` = system-provided skills
- `/home/marti/.agents/skills` = custom/user-managed skills

Use the system area for built-in capabilities and this directory for your own maintained skill set.

For the broader Codex environment map, see:

- `/home/marti/.codex/README.md`

## Maintenance guidance

When adding or refining custom skills:

1. keep each skill focused on one workflow or domain
2. make `SKILL.md` concise and operational
3. avoid overlapping skills unless they serve clearly different use cases
4. prefer updating an existing skill over creating near-duplicates
5. document any special validation or tool expectations inside the skill itself

## Cleanup guidance

This directory should stay small and human-managed.

Do not store runtime state, caches, logs, or temporary artifacts here.
Only keep maintained skill definitions and any tightly related support files.
