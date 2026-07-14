# Contributing

`agentcore` is a curated source for portable Codex configuration and custom
skills. Changes should remain migration-safe, security-conscious, and
reproducible.

## Before changing files

1. Read the nearest `AGENTS.md` and relevant `docs/codex/` guidance.
2. Keep auth, histories, session state, databases, caches, and machine-local paths
   out of the repository.
3. Use current official OpenAI documentation for version-sensitive Codex behavior.
4. Preserve public configuration, CLI, and schema contracts unless the
   compatibility impact is explicit.

## Validation

Run the smallest relevant checks. For repository-wide changes, run:

```bash
python3 -m pip install -r requirements-validation.txt
python3 -B scripts/bootstrap_codex_environment.py --validate-only
python3 -B scripts/validate-skills.py
python3 -B scripts/test-validate-skills.py
python3 -B scripts/test-bootstrap-config.py
python3 -B scripts/test-codex-hooks.py
```

Run `scripts/validate-codex.sh` when a compatible live Codex installation is
available. Pull requests should state exact commands, results, and remaining
uncertainty.

For behavior-changing skill edits, record the target repository, task, and
repository-native validation used as real-task evidence in the pull request.

## Pull requests

- Keep one coherent change per pull request.
- Explain permission, hook, MCP, subprocess, secret, and migration effects.
- Add focused regression coverage for behavior changes.
- Update compatibility metadata and docs when changing the supported Codex model
  or CLI baseline.
- Do not weaken a safety boundary merely to make a test pass.
