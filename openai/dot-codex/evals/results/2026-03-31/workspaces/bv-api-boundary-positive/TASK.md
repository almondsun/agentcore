# tiny-python-service

This fixture is intentionally small and covers two positive workflows.

## Repository Notes

- Package root: `src/tiny_service/`
- Canonical validation command: `pytest`
- The repo is small enough to inspect manually before running the prompt

## Scenario A: `build-validate`

Use the frozen diff in `api_breaking_change.patch`.

What changed:

- `lookup_user()` changes its public return contract from `str` to `dict[str, str]`
- one test is updated, but the change is still a public API contract change

What a strong run should do:

- classify validation as escalated rather than narrow
- prefer the repo-native `pytest` command
- call out compatibility and caller-impact risk explicitly
- separate passed, failed, not run, and remaining unverified evidence

## Scenario B: `orchestrated-implementation`

Use the current fixture repo plus this bug report:

`lookup_user()` currently accepts blank or whitespace-only IDs, which normalize to an empty string and leak downstream as `user:`. Fix the bug so blank IDs raise `ValueError` from the normalization path and make sure the API layer preserves that contract cleanly.

What makes this a good eval:

- the path crosses `normalize.py` and `api.py`
- the agent should inspect the repo before editing
- implementation should stay in the main agent
- post-change validation should use `build-validate` discipline with `pytest`
