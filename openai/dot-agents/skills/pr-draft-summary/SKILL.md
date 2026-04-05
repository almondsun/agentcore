---
name: pr-draft-summary
description: Use when the user wants a PR description, draft summary, release-style change summary, or review-ready writeup based on the current working tree, git diff, recent commits, validation results, and affected subsystems. Do not trigger for implementing code changes or for code review tasks whose primary output should be findings rather than a summary.
---

# PR Draft Summary

Produce a concise, review-ready summary grounded in actual repository state.

## Inputs To Gather

- `git status` for scope and staged vs unstaged changes.
- `git diff` or PR diff for behavioral details.
- Recent commits when they clarify intent or sequencing.
- Validation that was actually run.
- Touched subsystems, interfaces, and risk areas.

## Writing Rules

- Summarize what changed and why, not just which files moved.
- Group by subsystem or behavior when that is clearer than file-by-file narration.
- Include validation that actually ran; never invent tests, builds, or checks.
- Call out compatibility, security, interop, migration, deployment, or operational impact when relevant.
- State remaining unverified areas plainly.
- Keep the result readable for reviewers scanning quickly.

## Output Shape

- `Summary:` high-level change and intent.
- `Affected areas:` main subsystems, interfaces, or workflows touched.
- `Validation:` checks actually run and key outcomes.
- `Risk / follow-up:` compatibility concerns, security or interop implications, rollback concerns, and remaining unverified areas when relevant.

## Quality Bar

- Prefer precise claims over completeness theater.
- If the diff is large or messy, say which parts appear most review-critical.
- If validation is missing, say that directly instead of smoothing it over.
