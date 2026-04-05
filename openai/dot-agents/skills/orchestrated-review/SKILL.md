---
name: orchestrated-review
description: Use when the user wants a coordinated repository review of a current diff, branch comparison, selected files, or specific review questions, and the task benefits from staged evidence gathering plus targeted review subagents. Trigger for multi-angle review orchestration, not for implementation, not for a single narrow security or interop audit, and not for simple docs lookup.
---

# Orchestrated Review

Coordinate evidence gathering, targeted subagent spawning, and final review synthesis for real repository reviews. Prefer the smallest useful set of specialists.

## When To Use

- Use for PR review, current diff review, branch-vs-branch review, selected-file review, or review questions that need staged evidence and more than one perspective.
- Do not use for implementation work.
- Do not use when the user clearly wants only one narrow specialist such as `security-auditor`, `interop-auditor`, or `docs-researcher`.
- Do not spawn every specialist by default.

## Review Target

Start by pinning the target:

- current diff
- branch vs main or another base
- selected files or directories
- explicit review questions or risk areas

If the target is unclear, resolve that first before spawning agents.

## Orchestration Procedure

1. Spawn `pr-explorer` first.
   - Ask it to map changed subsystems, key files and symbols, likely affected contracts, and likely review hotspots.
2. Decide whether docs evidence is needed.
   - Spawn `docs-researcher` only when framework, API, SDK, version-sensitive behavior, OpenAI platform behavior, or external library docs materially affect the review.
3. Spawn `reviewer` for general correctness, regression, compatibility, cleanup, and test-coverage review.
4. Spawn `interop-auditor` only if Python/C/C++ boundaries, FFI, ABI, marshaling, allocator rules, ownership, lifetime, or thread-affinity assumptions are touched.
5. Spawn `security-auditor` only if trust boundaries, parsing, subprocesses, paths, secrets, serialization, native safety, deployment-sensitive changes, or dangerous defaults are touched.
6. Wait for all spawned agents.
7. Synthesize the results into one final review.

## Specialist Selection Rules

- `pr-explorer` is the default evidence gatherer. Start there unless the review target is already fully scoped.
- `docs-researcher` is evidence-gathering only. Use it to settle documented behavior, not to judge code quality.
- `reviewer`, `interop-auditor`, and `security-auditor` are findings-oriented judges.
- If `pr-explorer` finds no interop-sensitive or security-sensitive surface, do not spawn those specialists.
- If one specialist already fully covers the request, do not add others just for completeness theater.

## Synthesis Rules

- Findings first, ordered by severity.
- Group by category only when it makes the result easier to scan.
- Remove duplicate findings across agents.
- If specialists disagree, call out the conflict explicitly and explain which evidence is stronger.
- Call out uncertainty, undocumented behavior, or missing evidence explicitly.
- Keep evidence gatherers and judges conceptually separate in the final writeup.

## Optional Handoff

- If the user asks for a PR writeup after the review, convert the validated review context into `pr-draft-summary` style output only after the findings phase.
- If the user wants a saved machine-readable review artifact, hand off to `structured-review-record` after the review is complete.
- Do not let summary writing replace the review itself.

## Output Contract

- `Scope:` what was reviewed.
- `Evidence gathered:` which subagents were used and why.
- `Findings:` ordered by severity, deduplicated.
- `Uncertainty:` conflicts, version sensitivity, missing docs, or unverified paths.
- `Optional summary:` only when explicitly requested after review.
