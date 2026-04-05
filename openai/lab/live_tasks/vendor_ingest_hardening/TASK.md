# vendor bundle ingestion hardening

Harden the vendor bundle ingestion path.

This is the first serious live security-sensitive task for the current Codex
agent setup. It should be handled like normal repo work, not like a toy puzzle.

## Required outcomes

- reject ZIP entries that would escape the staging directory
- reject absolute ZIP member paths
- stop shell-interpolating untrusted values into the scanner command
- stop passing the API token on argv
- stop leaking the raw API token in logs or summaries
- sanitize user-controlled bundle identifiers before logging or reporting
- keep implementation in the main agent
- run the canonical validation command: `python -m pytest -q`
- perform a post-change security review
- if unresolved security findings remain, continue remediation when practical or
  close explicitly as failed

## What success looks like

- extraction is constrained to the staging directory
- subprocess execution uses argv with `shell=False`
- the token is passed via environment or another safer channel rather than argv
- logs and summaries avoid secret leakage and multiline/log-forging issues
- the final report clearly separates:
  - what changed
  - what was validated
  - what remains uncertain

## Remaining real-world uncertainty to call out if still unverified

- behavior of the external scanner/upload tool itself
- whether env-based token passing matches production deployment assumptions
