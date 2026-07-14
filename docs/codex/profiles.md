# Codex Profile Contract

Use profiles to make workflow cost, permissions, and evidence expectations
explicit. The base config is conservative and read-only; profiles opt into
broader behavior only when the task needs it.

## Base session

Use the base config for questions, repo inspection, planning, and low-risk
triage.

- Permissions: read-only.
- Web: disabled.
- Reasoning: medium.
- Verbosity: low.
- Subagents: available but bounded; do not spawn them unless the task justifies
  a second model run.

## `edit`

Use for normal trusted code changes in a known checkout.

- Permissions: `agentcore_workspace`.
- Web: cached.
- Reasoning: medium.
- Verbosity: medium.
- Expected validation: focused repo-native checks for touched behavior.

## `review`

Use for code review, bug hunting, and compatibility checks where findings matter
more than implementation speed.

- Permissions: read-only.
- Web: cached.
- Reasoning: high.
- Verbosity: low.
- Expected output: findings first, ordered by severity.

## `interop`

Use only for Python/C/C++ boundaries, FFI, ABI, ownership, lifetime, allocator,
encoding, marshaling, and thread-safety work.

- Permissions: `agentcore_workspace`.
- Web: cached.
- Reasoning: high.
- Verbosity: medium.
- Expected validation: strongest relevant boundary checks available.

## `research`

Use when current documentation, standards, package behavior, or external
evidence materially affects the answer.

- Permissions: read-only.
- Web: live.
- Reasoning: medium.
- Verbosity: medium.
- Context7 MCP: explicitly enabled with prompt-by-default tool approvals.
- Expected output: cite sources and distinguish documented facts from inference.

## `readonly`

Use when local side effects should be avoided but normal planning quality is
still useful.

- Permissions: read-only.
- Web: cached.
- Reasoning: medium.
- Verbosity: medium.

## `ci`

Use for scripted inspection and non-interactive checks.

- Permissions: read-only.
- Approval: never.
- Web: disabled.
- Reasoning: low.
- Verbosity: low.
