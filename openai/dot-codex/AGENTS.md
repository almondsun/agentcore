# AGENTS.md

## 1. Purpose and Priority Order

This file defines the engineering operating standard for this repository.

Optimize for the following, in order:

1. Correctness
2. Safety and security
3. Contract clarity
4. Validation evidence
5. Maintainability
6. Performance where justified
7. UX at interfaces
8. Style consistency

Prefer the lightest design that satisfies the contract.
Do not confuse architectural ceremony with engineering quality.
Use patterns only when they reduce coupling, clarify variation points, or improve testability.

This repository is optimized primarily for mixed-language systems work:
- Python for orchestration, tooling, testing, scripting, service glue, and high-level workflows
- C for explicit low-level control, stable C interfaces, constrained environments, and interoperability
- C++ for RAII, stronger invariants, value semantics, and performance-sensitive components

Keep the root file compact and high-signal.
Put lower-frequency doctrine in companion docs and reference them from here.

When working with OpenAI APIs, ChatGPT Apps SDK, Codex, or platform documentation, always use the `openaiDeveloperDocs` MCP first.

---

## 2. Repository Context

Before making non-trivial changes, inspect the repository and identify the source of truth.

Determine:
- repository purpose
- major directories and subsystem boundaries
- primary build system
- canonical test commands
- canonical lint and formatting commands
- canonical type-checking and static-analysis commands
- language versions and compiler/interpreter constraints
- CI workflows or scripts that define the expected path
- generated code, vendor code, or third-party mirrored areas
- directories with special constraints such as embedded, ABI-sensitive, FFI, or deployment-critical code

Prefer repository-native commands over generic guesses.

Check these first when they exist:
- `README.md`
- CI workflows
- `pyproject.toml`
- `requirements*.txt`
- `CMakeLists.txt`
- `CMakePresets.json`
- `meson.build`
- `Makefile`
- toolchain files
- formatter and linter configs
- test runner configs
- package manifests

If repository conventions are unclear, choose the most conservative option and state the assumption explicitly.

This is a global baseline file, so it does not declare one fixed repository map or
canonical command set. The current repository remains the source of truth.

For each non-trivial task, identify and report the concrete local equivalents for:

- core/domain path
- orchestration/tooling path
- language-boundary or ABI-sensitive path when present
- tests path
- generated or vendor paths when present
- canonical build command
- canonical test command
- canonical lint/format/type-check/static-analysis commands when present

If the current repository provides a closer `AGENTS.md` or `docs/codex/` guidance,
follow that more specific source for local structure and commands.

---

## 3. Non-Negotiable Rules

- Do not claim completion without running relevant checks when tools are available.
- Do not put side effects inside core/domain logic unless the function exists specifically for side effects.
- Do not silently swallow errors.
- Do not introduce risky shortcuts just to make tests pass.
- Do not overwrite, revert, or ignore unrelated user changes.
- Do not change public contracts, persisted formats, wire formats, or binary interfaces without calling that out explicitly.
- Do not introduce hidden ownership transfer.
- Do not mix incompatible error-handling styles within the same subsystem without a deliberate boundary.
- Do not add abstractions that are not justified by a real variation point, boundary, or testability need.
- Do not guess repository conventions when the source of truth is available.
- Do not use destructive commands unless explicitly requested.
- Do not leave new warnings in touched code unresolved.
- Do not treat “it compiles” as sufficient evidence of correctness.
- Do not hand-edit generated code unless the task explicitly requires regeneration-aware editing.
- Do not modify vendor or mirrored third-party code unless the task explicitly requires a vendor patch or update path.

For mixed-language work:
- keep language boundaries explicit
- keep contracts stable across those boundaries
- keep marshaling and translation logic at the boundary
- keep one clear ownership model per boundary
- keep one clear error model per boundary
- do not leak platform- or language-specific details across shared interfaces unless required

---

## 4. Task Execution Contract

### 4.1 General workflow

For non-trivial tasks:
1. inspect the codebase and identify the relevant boundaries
2. determine the smallest correct change that satisfies the request
3. follow existing repository conventions, naming, structure, and tools
4. keep working until the task is complete or clearly blocked
5. verify the result before finalizing
6. report what changed, what was validated, and what remains unverified

Make conservative assumptions when ambiguity is small.
Ask for clarification only when a wrong assumption would likely cause material harm.

### 4.2 Architecture-first execution

Before implementing a non-trivial change, identify:
- the system boundary
- the main responsibility of the touched module
- where side effects live
- the error model
- the ownership and lifetime model
- relevant performance, concurrency, compatibility, and security constraints

Prefer these boundaries:
- Domain/core: deterministic logic, invariants, validation, transformations
- Application/orchestration: workflows, sequencing, use cases
- Infrastructure/adapters: filesystem, network, database, OS APIs, vendor SDKs, UI frameworks

### 4.3 Mixed-language systems rules

When a task spans Python, C, and/or C++:
- minimize the cross-language surface area
- keep the boundary narrow and stable
- define ownership explicitly
- define copying vs borrowing explicitly
- define text encoding and binary layout assumptions explicitly when relevant
- define the error model explicitly
- define thread-safety and reentrancy assumptions explicitly when relevant
- keep boundary functions easy to test independently
- prefer a C-compatible boundary when ABI stability or broader interop matters

### 4.4 Operational triggers

Apply these actions when the corresponding condition occurs:

- If changing a public API, CLI contract, file format, wire format, or binary interface:
  - call out the compatibility impact explicitly
  - add or update regression coverage
  - verify the canonical path used by current callers when practical

- If changing build scripts, toolchain settings, packaging, CI assumptions, or developer tooling:
  - run the canonical full validation path
  - call out workflow changes explicitly

- If touching parsers, credentials, trust boundaries, network surfaces, file formats, or privileged operations:
  - elevate security review priority
  - validate hostile and malformed input paths
  - if a post-change security audit finds unresolved issues, continue remediation when practical or close the task explicitly as failed

- If touching generated code:
  - prefer regeneration over hand-editing
  - document the generation source and workflow

- If touching vendor or mirrored third-party code:
  - minimize the patch
  - document the reason and update path

- If touching C/C++ ownership, lifetime, concurrency, ABI-sensitive code, or FFI paths:
  - state the ownership model explicitly
  - state compatibility implications explicitly
  - run the strongest relevant validation available

- If touching migrations, auth flows, serialization, deployment paths, concurrency primitives, or compatibility-sensitive interfaces:
  - review with heightened skepticism
  - call out operational or rollback risks

### 4.5 Standalone algorithm/example mode

For standalone algorithms, examples, or interview-style tasks:
- write one pure solver plus one thin I/O wrapper
- state the expected complexity
- validate input clearly
- avoid unnecessary patterns and framework-like structure
- document meaningful assumptions such as byte-vs-Unicode semantics, indexing conventions, or overflow assumptions

### 4.6 Product/application mode

For user-facing product work:
- preserve existing design-system conventions
- handle loading, empty, partial, and error states
- keep interactions accessible and predictable
- prefer actionable error messages and safe defaults
- treat UX regressions at boundaries as correctness issues

### 4.7 Post-Audit Remediation Loop

When a post-change audit is used, treat the task flow as:

1. implement
2. validate
3. audit
4. if findings remain:
   - remediate in the main agent when practical
   - rerun the smallest correct validation for the remediation
   - rerun the relevant audit when the remediation changes the audited surface materially
5. close as success only when blocking findings are resolved
6. otherwise close explicitly as failed with residual risk

Do not treat an audit as the terminal step by default.
Treat it as a decision point:

- no blocking findings: close successfully with remaining uncertainty
- blocking findings and practical remediation available: continue implementation
- blocking findings and remediation out of scope or unsafe for the turn: close explicitly as failed

---

## 5. Definition of Done

Do not consider a task complete unless all applicable items below are satisfied.

### 5.1 Required outcomes

- the requested behavior is implemented correctly
- the change respects the existing architecture or improves it deliberately
- edge cases and invalid inputs have been considered
- assumptions that affect correctness are documented
- side effects are confined to appropriate boundaries
- public contracts remain internally consistent
- the change is no more complex than necessary
- if a post-change audit was used, any material findings are either fixed or explicitly left as a failed outcome with concrete residual risk

### 5.2 Required validation

When tools are available, run the relevant checks:
- build or configuration
- unit tests
- integration tests when relevant
- lint or format checks
- type checks
- static analysis
- sanitizers for changed C/C++ code when supported
- focused runtime sanity checks for behavior-critical paths

If a check could not be run:
- state that explicitly
- explain why
- state what remains unverified

### 5.3 Required final report

The final response must include:
- what changed
- why it changed
- what was validated
- what remains risky, limited, or unverified

If a post-change audit was performed:
- say which auditor was used and why
- state whether the audit found unresolved issues
- do not present the task as successful when unresolved security-critical findings remain
- if unresolved findings remain, either continue remediation or report an explicit failed closeout
- if remediation was attempted after the audit, say what was revalidated and whether the audited surface was rechecked

---

## 6. Language-Specific Standards

### Cross-language rules

- Make ownership, mutability, and lifetime explicit at language boundaries.
- State whether data is copied, borrowed, shared, pinned, or transferred.
- Avoid exposing unstable implementation details across language boundaries.
- Keep serialization, transcoding, ABI, alignment, packing, and numeric range assumptions explicit when relevant.
- If one language owns cleanup, all others must treat the resource as borrowed unless documented otherwise.
- Keep boundary types simple and stable.

### 6.1 Python

Use Python primarily for:
- orchestration
- tooling and automation
- testing
- adapters and service glue
- high-level workflows around lower-level components

Rules:
- use type hints for public functions, methods, and important internal interfaces
- prefer pure functions for domain logic when possible
- keep I/O, framework code, process execution, and external service access out of the computational core
- pass dependencies explicitly when they affect correctness, reproducibility, or testability
- prefer `dataclass`, `Enum`, and `Protocol` when they clarify contracts
- prefer small, cohesive modules over utility dumping
- use explicit exceptions with actionable messages
- do not hide fallback behavior unless it is clearly documented and safe
- do not rely on ambient global state for core behavior
- keep Python as the orchestration layer when lower-level code already owns the hot path

Use patterns only when justified:
- dependency injection
- adapter
- service/facade
- strategy
- repository when persistence is a real boundary

Avoid by default:
- deep inheritance
- singleton-style hidden state
- abstract base class hierarchies without real variation
- framework-driven coupling in core logic

Documentation and validation:
- document all public modules, classes, and functions
- for non-trivial functions, document purpose, parameters, return meaning, side effects, and assumptions
- add intent-focused comments before non-obvious logical blocks
- when behavior depends on text semantics, state whether logic operates on bytes, code points, grapheme-like user characters, or lines

### 6.2 C

Use C where explicit control, stable interfaces, small runtime assumptions, or constrained environments matter.

Rules:
- make buffer capacities, nullability, aliasing, ownership, and cleanup explicit
- use one consistent error model in a subsystem
- validate all external input at the boundary
- do not call `exit`, `abort`, or terminate the process from reusable or core functions
- keep allocation and cleanup behavior explicit and correct under partial initialization
- prefer focused module-style organization with `.h + .c`
- prefer fixed-width integer types when representation matters

Stop-ship C defects:
- unbounded input reads
- unsafe string handling
- unchecked buffer writes
- hidden ownership transfer
- undefined cleanup behavior
- returning pointers to invalid storage
- inconsistent error semantics
- silent truncation or overflow risks that affect correctness or safety
- `volatile` used as a threading primitive
- global mutable state without explicit justification

Public/shared C APIs must make explicit:
- who allocates
- who frees
- valid ranges
- nullability
- required capacities
- truncation behavior
- ownership of returned data
- thread-safety or reentrancy assumptions
- encoding and binary-layout assumptions when relevant

When C is used as an interop boundary:
- keep headers C-compatible
- keep the ABI surface narrow
- avoid leaking C++ constructs across the boundary
- isolate platform-specific details behind adapters
- document whether memory ownership crosses the boundary or remains local

### 6.3 C++

Use C++ where RAII, stronger invariants, value semantics, and performance-sensitive abstractions improve correctness and maintainability.

Rules:
- prefer the Rule of Zero by default
- use RAII for every resource with acquire/release semantics
- prefer stack allocation and value semantics when they improve local reasoning
- use `std::unique_ptr` by default for heap ownership
- use `std::shared_ptr` only when shared ownership is genuinely required
- use references for non-null borrowed inputs
- use pointers for nullable or reseatable relationships
- use `std::span` and `std::string_view` only when lifetime assumptions are clear and documented
- prefer composition over deep inheritance
- keep headers focused and implementation details private
- avoid hidden allocations or repeated construction in hot paths without justification
- keep exception or status-return policy consistent within a subsystem

Use patterns when justified:
- RAII wrappers
- adapter
- strategy/policy
- service/facade
- explicit state machines
- Pimpl only when ABI or compile-time insulation truly matters

Avoid by default:
- inheritance-heavy designs
- template metaprogramming without clear payoff
- hidden ownership behind raw pointers
- casual view lifetimes
- shared ownership for convenience
- abstraction layers that obscure data flow or cost

When C++ sits behind a C or Python boundary:
- keep the foreign boundary simple and stable
- do not leak exceptions across a C boundary
- translate low-level errors into the boundary error model
- contain STL-heavy internals behind adapters when ABI stability matters
- make destruction and cleanup callable from the owning side

---

## 7. Security and Safety Stop-Ship Rules

Treat the following as stop-ship defects unless explicitly acknowledged and justified:

- unsafe parsing of untrusted or external input
- unbounded or unchecked buffer operations
- shell-command construction vulnerable to injection
- SQL, path, template, or serialization injection risks
- secrets, tokens, keys, or credentials written to logs or committed artifacts
- deserialization of untrusted data without a safe boundary
- ambiguous ownership or lifetime for security-sensitive resources
- insecure defaults when a safe default is practical
- missing validation at trust boundaries
- silent downgrade of security behavior
- undefined behavior risks in C/C++ that can affect correctness or exploitability
- data races in shared mutable state
- dangerous operations triggered without explicit user intent

Security expectations:
- validate external input
- minimize privileges
- keep trust boundaries explicit
- prefer safe defaults
- fail closed when appropriate
- preserve enough context for diagnosis without leaking secrets
- treat memory safety, integer safety, and concurrency safety as correctness concerns

Post-audit closure rule:
- unresolved security findings are not mere commentary; they are open work
- do not stop at "audit found issues" unless the task is explicitly closed as failed
- do not report success when trust-boundary, parser, subprocess, path, secret-handling, or native-safety findings remain unresolved

If a change affects a trust boundary, credential path, parser, network surface, file format, or privileged operation, call that out explicitly in the final report.

---

## 8. Performance and Scalability Rules

- Choose asymptotically sound approaches for the expected scale.
- Avoid obviously wasteful repeated work, allocations, copies, or conversions.
- Optimize hot paths with evidence, not vanity.
- Preserve readability unless performance constraints justify added complexity.
- State meaningful performance assumptions when they affect the design.
- Distinguish throughput, latency, memory usage, startup cost, and tail behavior when relevant.

For mixed-language systems:
- put hot loops in the right layer
- avoid repeated crossing of language boundaries in tight loops when batching is practical
- avoid unnecessary marshaling churn
- keep data layout and ownership predictable
- prefer coarse, stable calls over chatty fine-grained boundary calls in performance-sensitive paths

Do not introduce micro-optimizations that materially harm correctness or maintainability unless there is evidence they are necessary.

---

## 9. UX / API / CLI Boundary Quality

Treat developer-facing and user-facing boundaries as product surfaces.

### For APIs and libraries

- make correct use easy and incorrect use hard
- use clear names and predictable return semantics
- make error behavior explicit
- prefer safe defaults
- keep output formats stable when callers may depend on them
- do not expose internal implementation quirks as contract

### For CLIs and scripts

- emit actionable error messages
- return meaningful exit codes
- keep machine-readable output stable when relevant
- avoid surprising defaults
- document required input formats and assumptions

### For UI or product-facing work

- preserve design-system conventions
- handle loading, empty, partial, and error states
- respect accessibility, keyboard behavior, and semantic structure
- prefer consistency over novelty

For mixed-language systems, boundary quality includes:
- clear FFI and IPC contracts
- stable data exchange formats
- explicit versioning or compatibility expectations when those boundaries are externalized

---

## 10. Review and Final Response Contract

### 10.1 When implementing changes

The final response must include:
- a concise summary of what changed
- the main architectural or boundary decisions
- validation actually run
- remaining limitations, risks, or unverified assumptions

### 10.2 When reviewing code

Report findings first, ordered by severity:
1. correctness
2. safety/security
3. contract clarity
4. performance/scalability
5. maintainability

For each finding, include:
- what is wrong
- why it matters
- likely impact
- the smallest safe fix when obvious

Do not bury material issues under style commentary.

Review with heightened skepticism when changes touch:
- auth flows
- credentials
- migrations
- parsers
- concurrency
- FFI
- serialization formats
- deployment paths
- compatibility-sensitive interfaces
- build/tooling assumptions

### 10.3 Honesty requirements

- do not claim tests were run if they were not
- do not claim a warning-free build if warnings were not checked
- do not imply confidence beyond the available evidence
- state what is uncertain
- if a check could not be run, say so explicitly

---

## 11. References to Specialized Docs

### 11.1 Repository-Specific Companion Docs

Before implementing non-trivial changes, inspect `docs/codex/` for task-relevant guidance.

Rules:
- If a relevant document exists in `docs/codex/`, read it before implementing.
- Treat `docs/codex/` as the canonical location for detailed repo-specific companion guidance.
- Follow the most specific applicable guidance when it does not conflict with higher-priority repository rules.
- Do not ignore `docs/codex/` when working in interop, build/test, security, performance, review-critical, or subsystem-specific areas.

Keep this file compact.
Put larger, topic-specific guidance in dedicated docs and reference them here.

Recommended companion docs:
- `docs/codex/architecture.md`
- `docs/codex/build-and-test.md`
- `docs/codex/security.md`
- `docs/codex/performance.md`
- `docs/codex/code-review.md`
- `docs/codex/frontend.md`
- `docs/codex/ffi-and-interop.md`
- `docs/codex/algorithms.md`

Suggested ownership of companion docs:
- `docs/codex/architecture.md`: subsystem boundaries, lifecycle rules, diagrams
- `docs/codex/build-and-test.md`: canonical commands, local setup, CI equivalence
- `docs/codex/security.md`: trust boundaries, parser guidance, secret handling, hardening rules
- `docs/codex/performance.md`: budgets, benchmarks, profiling workflow
- `docs/codex/code-review.md`: repo-specific review heuristics
- `docs/codex/ffi-and-interop.md`: ownership, ABI, encoding, marshaling, error translation
- `docs/codex/algorithms.md`: expectations for standalone solver examples and complexity reporting

If a rule is large, domain-specific, or low-frequency, move it out of this file and reference it instead.

---

## 12. Subdirectory Override Policy

Use closer, subsystem-specific instruction files when a subdirectory has constraints that differ from the repository default.

Examples:
- embedded subsystem
- Python service
- C ABI layer
- C++ performance-critical core
- frontend application
- generated-code or vendor-code areas

Closer instruction files override broader ones only for their scope.

Use subdirectory overrides for:
- build or tool differences
- stricter performance constraints
- ABI-sensitive subsystems
- ISR or real-time constraints
- stricter review rules
- special security rules
- generated-code boundaries

Do not use overrides to weaken the non-negotiable rules unless explicitly intended and documented.
