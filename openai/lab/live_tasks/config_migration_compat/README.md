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

The current implementation only supports a legacy flat retry setting:

- config input field: `retries`
- payload output field: `retry_count`

The intended live task is to introduce a new config shape without breaking
existing configs or the downstream payload contract that current callers still
depend on.
