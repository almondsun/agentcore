# config migration compatibility task

Introduce a backward-compatible config shape change for retry settings.

This is a normal professional maintenance task, not a security hardening task.
Treat compatibility and caller impact as the main engineering concern.

## Required outcomes

- accept a new nested config shape:
  - `retry_policy.max_attempts`
  - `retry_policy.backoff_seconds`
- keep legacy `retries` support for existing configs
- preserve the downstream payload field name `retry_count`
- preserve the existing CLI entry point and its JSON output contract where
  required
- update the right callers and tests
- fail clearly when legacy and new retry settings conflict
- run the canonical validation command: `python -m pytest -q`
- report compatibility impact explicitly in the final response

## What success looks like

- old configs that only use `retries` still work
- new configs that use `retry_policy` work
- if both config styles are present and disagree, the loader rejects the config
  with a clear error
- the public payload still uses `retry_count` because the downstream worker has
  not been migrated yet
- the final report clearly separates:
  - what changed
  - what was validated
  - what compatibility contract was preserved

## Compatibility constraints to preserve

- `build_dispatch_payload()` remains the place that shapes worker-facing JSON
- callers that consume the payload still require `retry_count`, not a renamed
  field
- the CLI must remain a small wrapper over the package logic rather than
  growing separate config rules
