# config_migration_compat

Small realistic compatibility-sensitive coding task for evaluating Codex on
normal change work where contracts matter more than raw implementation speed.

## Repository Notes

- Package root: `src/config_migration_compat/`
- Tests: `tests/`
- Example config: `examples/nightly-export.json`
- Canonical validation command: `python -m pytest -q`

## Scenario

This repo loads a job dispatch config, builds the JSON payload handed to a
downstream worker, and exposes a small CLI for operators to preview the plan.

The current implementation preserves the legacy flat retry setting and also
supports the nested retry-policy shape:

- legacy input field: `retries`
- new input object: `retry_policy.max_attempts` and `retry_policy.backoff_seconds`
- stable downstream payload field: `retry_count`

This kept specimen represents the completed compatibility migration. Future
reruns should start from a frozen pre-change fixture rather than treating this
working tree as an unmodified seed.
