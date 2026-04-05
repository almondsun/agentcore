# Code Review Guide

This document defines the code review standard for this repository.

Use it together with:
- `AGENTS.md` for global engineering rules
- `docs/codex/architecture.md` for boundary, responsibility, and side-effect expectations
- `docs/codex/build-and-test.md` for canonical validation paths
- `docs/codex/security.md` for security-sensitive review expectations
- `docs/codex/performance.md` for performance-sensitive review heuristics
- `docs/codex/ffi-and-interop.md` for Python/C/C++ boundary review rules

This file exists to make review behavior explicit, consistent, and high-signal.

Code review is not style commentary.
Code review is structured risk detection.

---

## 1. Purpose

The purpose of review is to detect the highest-value problems before they become:
- bugs
- regressions
- security issues
- compatibility breaks
- operational failures
- maintainability traps
- hidden performance costs
- unsafe boundary changes

A good review should:
- prioritize real risk
- focus on correctness and safety first
- be explicit about impact
- suggest the smallest safe fix when obvious
- avoid drowning important issues in style noise

Optimize review effort in this order:
1. correctness
2. safety and security
3. contract clarity
4. compatibility
5. concurrency and lifecycle safety
6. performance where relevant
7. maintainability
8. style consistency

---

## 2. Review Scope

Review applies to:
- hand-written code
- tests
- build and packaging changes
- CI and tooling changes
- configuration that affects runtime behavior
- schema, file-format, or wire-format changes
- FFI / interop boundaries
- migrations and deployment-related changes
- generated code changes when generation behavior is changed
- documentation changes when they alter or clarify contract behavior

Do not limit review to the diff text alone when the surrounding context matters.

When needed, inspect:
- the touched subsystem
- nearby tests
- public contracts
- boundary definitions
- related build files
- serialization or config paths
- caller assumptions
- cleanup and failure paths

---

## 3. Core Review Principles

### 3.1 Review for risk, not for activity

A review should identify what could go wrong, not merely describe what changed.

Focus on:
- invalid assumptions
- missing validation
- hidden breakage
- incompatible contract changes
- failure-path weaknesses
- lifecycle or ownership confusion
- race conditions
- parser weaknesses
- dangerous defaults
- unverified behavior

### 3.2 Review the contract, not just the implementation

Ask:
- what does this code promise?
- what inputs are allowed?
- what happens on invalid input?
- what is the ownership model?
- what remains valid after failure?
- what compatibility assumptions exist?
- what callers are relying on?
- is the implementation still consistent with the documented contract?

### 3.3 Review behavior, not style first

Do not bury a correctness issue under comments about naming, formatting, or local stylistic preferences.

Only spend review energy on style when:
- it affects readability materially
- it obscures a real defect
- it violates repository conventions strongly enough to create maintenance cost

### 3.4 Prefer local, actionable findings

A good finding should say:
- what is wrong
- why it matters
- likely impact
- smallest safe fix when obvious

Avoid vague feedback such as:
- “this feels wrong”
- “can this be improved?”
- “maybe rethink this”
unless you also explain the actual risk.

### 3.5 Escalate scrutiny for risky areas

Increase skepticism when the change touches:
- auth or authorization
- secrets or credentials
- parsers or deserializers
- file paths or process spawning
- network surfaces
- FFI / interop boundaries
- ABI-sensitive headers
- serialization formats
- migrations
- deployment paths
- concurrency
- memory ownership
- generated code behavior
- build or packaging logic

---

## 4. Review Output Contract

### 4.1 Severity order

Report findings in this order:
1. correctness
2. safety/security
3. contract clarity / compatibility
4. concurrency / lifetime / resource safety
5. performance / scalability
6. maintainability

Style-only comments belong last and only when worth mentioning.

### 4.2 Finding format

Each finding should include:

- **Category**: correctness / security / compatibility / lifecycle / performance / maintainability
- **Severity**: high / medium / low
- **Location**: file and relevant function, block, or behavior
- **Issue**: concise statement of what is wrong
- **Why it matters**: concrete risk or likely impact
- **Suggested fix**: smallest safe correction when obvious

### 4.3 Evidence standard

Do not claim a regression, vulnerability, or compatibility break without a concrete basis.

Good basis:
- direct code path reasoning
- contract mismatch
- missing validation
- missing cleanup
- unsupported lifetime assumptions
- missing or incorrect tests
- known failure mode pattern
- inconsistency with repository rules or documented behavior

If uncertain, say so explicitly.
Do not overstate confidence.

### 4.4 No false completion claims

Do not imply the change is safe merely because:
- it compiles
- tests pass
- the diff is small
- the code is cleanly formatted

Passing checks are evidence, not proof.

---

## 5. What to Look For First

Review in this order unless the task clearly demands otherwise.

### 5.1 Correctness

Look for:
- wrong logic
- broken edge cases
- off-by-one errors
- invalid assumptions about inputs
- invalid assumptions about ordering or uniqueness
- mismatch between implementation and contract
- mismatch between code and tests
- stale callers after API changes
- missing failure-path handling
- incorrect default behavior
- partial mutation on failure without documentation

### 5.2 Safety and security

Look for:
- missing validation on untrusted input
- insecure defaults
- accidental privilege expansion
- secret leakage
- unsafe parsing
- shell or path injection risks
- unsafe deserialization
- undefined behavior risks in native code
- data races
- dangerous logging
- trust-boundary confusion

### 5.3 Compatibility and contract clarity

Look for:
- changed public behavior without disclosure
- changed file or wire formats
- ABI-sensitive layout changes
- changed nullability or ownership semantics
- changed error semantics
- changed timing or ordering assumptions
- changed CLI output or exit code behavior
- changed packaging or install assumptions

### 5.4 Resource, lifetime, and concurrency safety

Look for:
- unclear ownership
- invalid borrowed views
- missing cleanup
- repeated destroy/close hazards
- partial-init cleanup bugs
- exception escape across unsupported boundaries
- iterator/view lifetime hazards
- thread-safety assumptions left implicit
- callback reentrancy hazards
- lock ordering or TOCTOU problems

### 5.5 Performance and scalability

Look for:
- obviously poor asymptotic choices
- repeated allocations in hot paths
- repeated cross-language boundary crossings
- avoidable marshaling churn
- hidden copies
- accidental loss of batching
- expensive work under locks
- performance-sensitive regressions without evidence

### 5.6 Maintainability

Look for:
- hidden coupling
- abstraction without need
- duplicated logic
- confusing control flow
- scattered translation logic
- poor boundary placement
- mixed error models
- tests that do not explain behavior
- comments that hide unclear design rather than clarify it

---

## 6. Language-Specific Review Guidance

### 6.1 Python

Review Python changes for:
- typed public API clarity
- clean separation between core logic and side effects
- hidden global state
- overly framework-coupled logic
- weak exception behavior
- silent fallbacks
- poor input validation
- misuse of dynamic behavior where explicit structure would be safer
- inadequate tests around behavior and edge cases

Common Python review targets:
- CLI argument handling
- exception mapping
- resource cleanup
- Unicode/text behavior
- boundary validation before native calls
- protocol or adapter correctness
- inappropriate abstraction or dependency injection where not needed

### 6.2 C

Review C changes for:
- explicit ownership
- buffer capacities and length discipline
- nullability clarity
- cleanup correctness under partial failure
- unsafe input handling
- unchecked arithmetic affecting memory or indexing
- aliasing and lifetime assumptions
- API clarity for callers
- header contract stability
- parser hardening

Common C stop-ship defects:
- unbounded reads
- unsafe string handling
- unchecked writes
- hidden ownership transfer
- invalid pointer returns
- allocator mismatch
- inconsistent error returns
- incomplete cleanup
- UB in parser or boundary code
- undocumented mutation through shared pointers

### 6.3 C++

Review C++ changes for:
- RAII usage and cleanup safety
- Rule of Zero violations without justification
- unclear ownership
- misuse of `shared_ptr`
- view lifetime hazards with `span` / `string_view`
- exception-safety inconsistency
- hidden allocations in hot paths
- unnecessary abstraction
- ABI-sensitive leakage of unstable types
- template complexity without payoff

Common C++ review targets:
- destruction behavior
- post-move validity assumptions
- exception boundaries
- iterator invalidation
- accidental copies
- hidden dynamic allocation
- header bloat and private-detail leakage

---

## 7. Interop Review Guidance

Use this section whenever code crosses Python/C/C++ boundaries.

Review for:
- narrowness of the boundary
- explicit ownership and cleanup
- borrow vs copy clarity
- exception/status translation
- UTF-8 / binary encoding assumptions
- shape/size validation
- ABI stability where relevant
- allocator matching
- callback safety
- thread-safety assumptions
- repeated cross-language calls in hot paths

High-risk interop findings include:
- native code trusting Python-side validation too much
- Python assuming native resource lifetime without explicit rules
- C++ exceptions reaching a C boundary
- returned borrowed memory without a documented validity window
- foreign callers expected to free memory with the wrong allocator
- text encoding left implicit
- Python object lifetime coupled to native state without explicit ownership design

---

## 8. Security-Focused Review Heuristics

When a change is security-relevant, review with extra rigor.

Ask:
- what is the trust boundary?
- what input is attacker-controlled?
- what is the failure mode?
- what secret or privilege is at risk?
- what parser or deserializer assumptions exist?
- what logging is emitted?
- what capability is granted by default?
- what happens if the input is oversized, malformed, reordered, replayed, or partially missing?

Special review targets:
- auth middleware coverage
- path normalization
- subprocess invocation
- parser bounds checks
- secret handling in logs and configs
- network client defaults
- credential propagation
- permission expansion
- unsafe fallback modes
- deserialization of complex structures

Do not accept “internal-only” as a security argument by itself.

---

## 9. Contract and Compatibility Review

Review all externally visible changes for compatibility implications.

This includes:
- public APIs
- headers
- exported symbols
- configuration formats
- file formats
- network payloads
- CLI output
- environment variable handling
- packaging layout
- install artifacts

Questions to ask:
- is this a breaking change?
- if yes, was it intentional and documented?
- are existing callers still correct?
- do tests cover the old behavior, the new behavior, or both?
- does this change ownership, nullability, units, defaults, or timing semantics?

If compatibility changes are real, the final report must state them explicitly.

---

## 10. Test Review Guidance

Review tests as carefully as implementation when the change is non-trivial.

Look for:
- missing regression coverage
- happy-path-only coverage
- missing invalid-input tests
- weak assertions
- tests that mirror the implementation instead of the contract
- tests that fail to exercise cleanup or failure paths
- interop tests that do not cover ownership or encoding
- tests that accidentally permit flakiness
- tests that hide concurrency risks
- tests that pass while leaving major scenarios unverified

Good tests should:
- encode contract expectations
- cover edge cases
- cover invalid input when relevant
- cover failure behavior
- be stable and readable
- reveal why the behavior matters

---

## 11. Build, Tooling, and CI Review

Changes to build and tooling deserve real review.

Inspect:
- whether the canonical workflow still works
- whether packaging assumptions changed
- whether CI still validates the right paths
- whether sanitizer/static-analysis paths were weakened
- whether warnings were silenced rather than fixed
- whether generated-code or codegen workflows changed
- whether install/load/import behavior changed
- whether a new dependency increased attack surface or maintenance burden

Do not treat build-system changes as low-risk housekeeping.

---

## 12. Generated and Vendor Code Review

### 12.1 Generated code

Do not spend review effort nitpicking generated output unless:
- generation logic changed
- the generated output is committed and materially broken
- a generation mismatch reveals a process problem

Focus review on:
- generation source
- reproducibility
- checked-in artifact policy
- compatibility impact
- whether regeneration was performed correctly

### 12.2 Vendor or mirrored third-party code

Review these changes for:
- minimal patch size
- update path clarity
- local divergence risk
- security implications
- compatibility with upstream expectations

Do not normalize broad manual edits to vendor code.

---

## 13. Reviewer Language and Tone

Good review comments are:
- precise
- calm
- non-dramatic
- technically grounded
- explicit about uncertainty
- specific about impact

Prefer:
- “This changes the ownership contract of the returned buffer, but the caller still frees it with the old path.”
- “This parser now trusts the declared length before validating the available bytes, which can produce an out-of-bounds read.”

Avoid:
- “This is bad.”
- “I don’t like this.”
- “Can you clean this up?”
- “This feels unsafe.”
without explaining the actual issue.

Do not performatively nitpick.
Do not invent problems without a basis.
Do not bury the real issue in optional style comments.

---

## 14. Review Outcome Categories

After review, changes should fall into one of these buckets:

### 14.1 Safe to accept
No material concerns found.
Any remaining comments are optional or stylistic.

### 14.2 Accept with minor fixes
Low-risk issues exist but the design is sound.

### 14.3 Needs revision
One or more material issues exist in correctness, safety, compatibility, lifecycle, or performance.

### 14.4 Needs deeper investigation
The risk is credible, but more context, testing, or subsystem inspection is needed to conclude safely.

Do not mark a change “good” if material uncertainty remains unspoken.

---

## 15. Final Review Checklist

Use this checklist before finalizing a serious review.

### Correctness
- Does the implementation still satisfy the intended contract?
- Are edge cases handled?
- Are failure paths safe and explicit?

### Security
- Is untrusted input validated?
- Are secrets protected?
- Are trust boundaries explicit?
- Are defaults safe?

### Compatibility
- Did any API, ABI, file format, wire format, or CLI behavior change?
- Was compatibility impact called out?

### Ownership and lifecycle
- Is ownership explicit?
- Are cleanup paths correct?
- Are borrowed views safe?
- Are concurrency assumptions documented?

### Performance
- Is there an obvious regression in hot paths or boundary cost?
- Are repeated allocations or crossings introduced unnecessarily?

### Tests
- Do tests cover the contract, edge cases, and failure behavior?
- Was regression coverage added where needed?

### Final output quality
- Are the findings prioritized by severity?
- Are they concrete and actionable?
- Are important issues clearly separated from optional commentary?

---

## 16. Anti-Patterns

Do not do the following in reviews unless there is a strong, explicit reason:

- focus on style before correctness
- nitpick formatting while missing a contract break
- assume passing tests prove safety
- assume small diffs are low risk
- assume internal callers are trustworthy
- ignore ABI or ownership changes because “the implementation is similar”
- accept hidden boundary complexity because the wrapper is small
- ask for abstraction by default
- request refactors without a concrete engineering reason
- overstate confidence without evidence
- bury the main issue under many low-value comments

---

## 17. Maintenance Rule

Keep this document concrete and high-signal.

When the repository evolves:
- add review heuristics for recurring failure modes
- update high-scrutiny subsystem lists
- update compatibility-sensitive areas
- update interop-specific review expectations
- remove stale or low-value doctrine

If the same category of bug repeatedly slips through review, add a rule or checklist item here.
