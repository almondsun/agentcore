---
name: structured-review-record
description: Use when an existing review result needs to be converted into a stable machine-readable artifact, usually JSON, with an optional human-readable Markdown companion. Trigger after review has already happened, especially after orchestrated-review, not for performing the review itself.
---

# Structured Review Record

Turn an already-completed review into a stable structured artifact. This is an optional companion step after interactive review, not a replacement for review.

## When To Use

- Use after a review has already been completed and the user wants a saved artifact.
- Use especially after `orchestrated-review`, or after any findings-first review that already has real evidence.
- Do not use to generate review findings from scratch.
- Do not invent validations, findings, or evidence that were not present in the source review.

## Default Artifacts

- Primary artifact: JSON
- Optional companion: Markdown summary for human scanning

## Recommended Output Convention

Prefer a neutral project-local location such as:

- `.codex/review-records/`
- `artifacts/reviews/`
- `reports/reviews/`

If the repo already has a reporting convention, follow that instead. Otherwise prefer `.codex/review-records/` because it is explicit and low-friction without implying a product-facing artifact.

## Stable Schema

Use a stable top-level JSON object with fields like:

- `schema_version`
- `review_scope`
- `target`
- `timestamp`
- `evidence_agents_used`
- `findings`
- `validation_run`
- `uncertainty`
- `remaining_unverified`
- `source_review_kind`
- `source_review_reference`
- `synthesized_metadata`

Each item in `findings` should use stable fields such as:

- `id`
- `severity`
- `category`
- `title`
- `issue`
- `why_it_matters`
- `likely_impact`
- `smallest_safe_fix`
- `affected_files`
- `affected_symbols`
- `affected_boundaries`
- `compatibility_impact`
- `security_impact`
- `interop_impact`
- `evidence`

## Record Rules

- Preserve severity ordering from the source review.
- Deduplicate findings before emission.
- Distinguish source evidence from synthesized metadata.
- Use `null` or empty arrays instead of invented content.
- If timestamps are added, use a clear machine-readable format such as ISO 8601.
- If some fields are unknown, say so explicitly in the artifact instead of filling gaps.

## Markdown Companion

If a Markdown companion is requested, keep it secondary to the JSON artifact and align it to the same finding IDs and ordering.

## Output Contract

- Concise explanation of what artifact or artifacts were produced.
- Exact schema used.
- Exact output path convention recommended.
- Clear distinction between source review evidence and synthesized metadata.
