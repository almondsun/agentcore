---
name: orchestrated-implementation
description: Use when the user wants a non-trivial bug fix, feature, refactor, migration, boundary fix, or validation hardening and the task benefits from staged evidence gathering, implementation in the main agent, targeted validation, and optional post-change audit. Trigger for implementation workflows, not for pure review or simple docs lookup.
---

# Orchestrated Implementation

Implement non-trivial changes with staged context gathering, targeted specialist use, validation, and optional post-change audit. Keep implementation responsibility in the main agent.

## When To Use

- Use for non-trivial bug fixes, features, refactors, migrations, boundary fixes, or validation hardening.
- Do not use for pure review tasks; use `orchestrated-review` instead.
- Do not use for trivial one-file edits where no staged workflow is needed.
- Do not spawn every specialist by default.

## Target Clarification

Start by pinning the implementation target:

- bug fix
- feature
- refactor
- migration
- boundary fix
- validation hardening

Also pin any explicit constraints such as compatibility, performance, security, ABI, rollout, or validation expectations.

## Context Pass

Inspect the repo before changing code:

- nearest `AGENTS.md`
- relevant `docs/codex/` guidance
- canonical build/test/interop/security docs when present
- obvious build and validation entry points

## Evidence Gathering Rules

- Spawn `pr-explorer` first when the affected execution path, subsystem boundaries, or likely touch points are not already obvious.
- Spawn `docs-researcher` only when framework, API, SDK, version-sensitive behavior, or OpenAI platform docs materially affect the change.
- Do not use reviewers or auditors as primary implementers.

## Implementation Rules

- Perform the implementation in the main agent.
- Keep a clear separation between:
  - evidence gathering
  - implementation
  - validation
  - post-change audit
- Prefer the smallest correct change that satisfies the request and respects repository guidance.

## Validation Phase

- Use `build-validate` after the code change.
- Choose the smallest correct validation path based on what changed.
- Escalate validation when contracts, interop boundaries, trust boundaries, parsers, packaging, concurrency, deployment paths, or generated-code assumptions were touched.

## Optional Post-Change Audit

- Hand off to `reviewer` for correctness, regression, compatibility, or test-coverage review when the user wants a post-change audit or the change is non-trivial enough to justify it.
- Hand off to `interop-auditor` only when Python/C/C++ / FFI / ABI / marshaling / ownership / allocator / lifetime boundaries were touched.
- Hand off to `security-auditor` only when trust boundaries, parsing, subprocesses, paths, secrets, serialization, native safety, or dangerous defaults were touched.
- Do not spawn auditors that are not justified by the changed surface.

If an audit is used:

- Audit findings are part of the task, not a postscript.
- If findings are minor and can be fixed safely, continue implementation and revalidate.
- If material security findings remain unresolved, do not present the work as complete or successful.
- Close explicitly as failed when unresolved security findings remain and further remediation is out of scope for the turn.
- Do not treat "audit found issues" as an acceptable stopping point without either remediation or a failed closeout.

Use this closure loop when findings appear:

1. classify findings into blocking vs non-blocking
2. remediate blocking findings in the main agent when practical
3. rerun the smallest correct validation for the remediation
4. rerun the same auditor when the fix materially changes the audited surface
5. only then decide between pass and explicit fail

Default rule:

- blocking findings + practical fix path -> continue
- blocking findings + no safe fix path this turn -> explicit fail
- no blocking findings -> close with remaining uncertainty if any

## Optional Finalization

- If the user asks for a saved review artifact after the audit, hand off to `structured-review-record`.
- If the user asks for a PR-ready writeup, hand off to `pr-draft-summary`.

## Output Contract

- `Target:` what is being changed.
- `Context used:` docs, repo guidance, or evidence agents consulted before implementation.
- `Implementation plan:` concise and practical.
- `Validation:` what was run.
- `Optional audit handoff:` which post-change auditors were used and why.
- `Remaining uncertainty:` anything still unverified.
- `Closure:` whether audit findings were fully resolved; if not, state explicit failure and residual risk.
- `Follow-up loop:` if audit findings triggered remediation, state what was fixed, what was revalidated, and whether the audited surface was rechecked.
