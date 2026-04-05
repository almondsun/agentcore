# test_agent

Small realistic security-sensitive coding task for evaluating the global Codex
setup on normal repo work rather than harness-only fixtures.

## Repository Notes

- Package root: `src/vendor_ingest/`
- Tests: `tests/`
- Canonical validation command: `python -m pytest -q`

## Scenario

This repo ingests ZIP bundles from external vendors, extracts them into a
staging directory, runs a local scanner/upload command, and emits a short
summary for operators.

The current implementation is intentionally vulnerable at the trust boundary.
The first serious live task is to harden it like a normal engineering task:

- inspect the repo first
- make the smallest correct fix
- validate with the repo-native pytest path
- treat this as a security-sensitive change
- if a post-change audit finds unresolved issues, continue remediation or close
  explicitly as failed
