# Security Guide

This document defines the security engineering standard for this repository.

Use it together with:
- `AGENTS.md` for global engineering rules
- `docs/codex/architecture.md` for subsystem boundaries and side-effect placement
- `docs/codex/code-review.md` for security-sensitive review expectations
- `docs/codex/ffi-and-interop.md` for boundary-specific safety and ownership rules
- `docs/codex/build-and-test.md` for validation and execution paths

This file exists to make security behavior explicit, reviewable, and operational.

Security is not a separate phase.
Security is part of correctness.

---

## 1. Purpose

The purpose of this document is to ensure that code in this repository:

- validates untrusted input correctly
- fails safely
- protects secrets and credentials
- preserves trust boundaries
- avoids insecure defaults
- prevents memory, concurrency, and serialization vulnerabilities
- keeps security-sensitive behavior explicit
- is reviewed with the right level of skepticism

Optimize for:
1. safe handling of untrusted data
2. explicit trust boundaries
3. least privilege
4. clear failure behavior
5. auditable security-relevant changes
6. secure defaults
7. minimal exposed attack surface

Do not trade security away for convenience, cleverness, or reduced boilerplate.

---

## 2. Core Security Principles

### 2.1 Treat external input as hostile

All external input must be treated as untrusted until validated.

This includes:
- user input
- CLI arguments
- environment variables
- files
- network payloads
- configuration files
- database content
- IPC messages
- plugin inputs
- deserialized objects
- FFI inputs from foreign callers

Do not assume data is safe because it came from:
- another internal service
- a previous stage of the pipeline
- a test harness
- a trusted user
- an existing file format

Validation must happen at the boundary.

### 2.2 Make trust boundaries explicit

A trust boundary exists whenever data or control crosses:
- process boundaries
- language boundaries
- service boundaries
- user privilege boundaries
- network boundaries
- storage boundaries
- plugin or extension boundaries
- generated-code boundaries
- third-party library boundaries

When touching a trust boundary:
- call it out explicitly
- validate inputs
- minimize privilege
- verify error handling
- review logging carefully
- elevate review rigor

### 2.3 Prefer safe defaults

Defaults should minimize damage.

Prefer:
- deny by default
- explicit enablement of risky behavior
- minimal permissions
- conservative parsing
- explicit cleanup
- stable and auditable configuration

Avoid:
- permissive fallback behavior
- silent downgrades
- auto-detection that changes security posture unexpectedly
- production behavior that depends on undocumented environment assumptions

### 2.4 Fail clearly and safely

When security-sensitive operations fail:
- fail closed when practical
- preserve enough context for diagnosis
- avoid leaking secrets
- avoid partial insecure success
- state whether cleanup is required
- state whether recovery or retry is meaningful

### 2.5 Minimize attack surface

Expose the smallest practical surface.

Prefer:
- narrow APIs
- small exported symbol sets
- minimal public endpoints
- minimal privilege
- short-lived tokens and resources
- minimal parsing complexity
- simple protocols over ambiguous ones

Avoid:
- unnecessary endpoints
- unnecessary capabilities
- unnecessary callbacks
- unnecessary dynamic behavior
- unnecessary shell invocation
- unnecessary deserialization of rich object graphs

---

## 3. Threat Model Expectations

Every non-trivial subsystem should be reasoned about in terms of:

- what is trusted
- what is untrusted
- what assets matter
- what operations are privileged
- what happens on malformed input
- what happens on partial failure
- what data must not leak
- what resources could be exhausted
- what unsafe states must never occur

At minimum, consider:
- malformed input
- oversized input
- unexpected encoding
- resource exhaustion
- credential leakage
- injection
- deserialization abuse
- memory corruption in native code
- race conditions
- privilege misuse
- unsafe default configuration
- compatibility changes that weaken prior security assumptions

If a change affects auth, credential handling, trust boundaries, parsers, serialization, network surfaces, plugins, deployment, or interop boundaries, treat it as security-relevant by default.

---

## 4. Security-Critical Areas

Treat the following classes of code as high scrutiny areas:

- authentication and authorization
- secrets and credential handling
- parsers and deserializers
- file and path handling
- network clients and servers
- process spawning and shell execution
- plugin loading or dynamic module loading
- native memory management
- FFI boundaries
- serialization and wire formats
- migrations and deployment scripts
- privileged operations
- concurrency around shared state
- update and install paths
- generated code that affects runtime behavior

Changes in these areas require stronger review and stronger validation.

---

## 5. Input Validation Rules

### 5.1 Validate at the boundary

Validate external inputs as early as possible.

Validation should cover:
- presence
- type
- shape
- size
- encoding
- allowed value ranges
- enum/tag validity
- required structural invariants
- length before access
- path expectations
- unit expectations where applicable

Do not rely on deeper layers to clean up boundary mistakes unless that is the documented design.

### 5.2 Reject malformed input explicitly

When input is malformed:
- reject it deterministically
- do not continue with partial assumptions
- do not silently normalize unsafe states
- do not permit ambiguous parsing when strict parsing is feasible

### 5.3 Enforce size and resource limits

All externally influenced operations should consider:
- maximum input size
- maximum nesting depth
- maximum output size
- maximum allocation size
- maximum retry or backoff behavior
- maximum concurrency where relevant
- timeout and cancellation behavior

Do not permit attacker-controlled unbounded work by default.

### 5.4 Be explicit about encoding

Never leave text or binary interpretation implicit.

Document whether input is:
- UTF-8 text
- ASCII subset
- opaque bytes
- structured binary with explicit endianness
- fixed-width encoded text

Reject undecodable or unsupported input clearly.

---

## 6. Secrets, Credentials, and Sensitive Data

### 6.1 Never expose secrets unnecessarily

Never log, print, serialize, or persist secrets unless explicitly required and protected.

Sensitive data includes:
- passwords
- tokens
- API keys
- private keys
- session cookies
- refresh tokens
- database credentials
- signing material
- credential-bearing URLs
- personally identifiable information when applicable

### 6.2 Minimize secret lifetime

Prefer:
- short-lived credentials
- ephemeral in-memory use
- explicit cleanup of sensitive buffers when practical
- least-privilege tokens
- rotation-friendly design

Avoid:
- long-lived ambient secrets
- copying secrets unnecessarily
- embedding credentials in config files or source
- passing secrets through many layers when a narrower handoff is possible

### 6.3 Redact by default

When logging security-relevant events:
- redact tokens, keys, cookies, and passwords
- avoid full raw payload logs when they may contain secrets
- log identifiers carefully
- preserve enough context to debug without leaking sensitive material

### 6.4 Be careful with environment variables

Environment variables are input, not trust.

Rules:
- validate security-relevant environment variables
- do not assume presence implies correctness
- do not dump full environment state in logs or diagnostics
- do not leak credential-bearing environment variables to child processes unless required

---

## 7. Authentication and Authorization

### 7.1 Keep authn and authz explicit

Do not blur authentication, authorization, and identity propagation.

Document:
- who is authenticated
- what is authorized
- where the decision is made
- what principal or role is being checked
- what happens on missing or invalid credentials

### 7.2 Deny by default

Missing, invalid, or ambiguous credentials must not be treated as success.

### 7.3 Avoid implicit privilege escalation

Do not let:
- defaults
- fallback paths
- compatibility modes
- stale cached state
- partial initialization
- missing config

silently expand privileges.

### 7.4 Separate policy from mechanism

Authorization logic should be explicit and reviewable.
Do not bury access decisions deep inside unrelated control flow.

---

## 8. Injection Prevention

### 8.1 Shell and process execution

Avoid invoking a shell unless absolutely necessary.

Prefer:
- direct process execution APIs
- explicit argument vectors
- fixed command names
- validated arguments
- least-privilege subprocess environments

Avoid:
- concatenated shell strings
- passing untrusted data into shell syntax
- relying on shell expansion
- inheriting more environment than needed

### 8.2 SQL, query, and template injection

Do not build queries or templates by naive string concatenation when structured parameterization exists.

Validate:
- identifiers if they must be dynamic
- templates if user-driven
- filters and selectors if externally controlled

### 8.3 Path injection

Never trust external path input without validation.

Check:
- normalization
- traversal
- symlink behavior when relevant
- allowed roots
- file type expectations
- privilege implications

Do not assume a path is safe because it is relative.

### 8.4 Serialization and expression injection

Do not evaluate externally provided expressions, templates, code fragments, or serialized object graphs unless that is explicitly the product behavior and heavily constrained.

---

## 9. Memory Safety and Native-Code Security

This section is mandatory for C and C++ work and relevant whenever Python interacts with native code.

### 9.1 Treat memory safety as a security concern

Memory bugs are security bugs unless proven otherwise.

High-risk classes:
- buffer overflows
- out-of-bounds reads
- use-after-free
- double free
- lifetime confusion
- integer overflow affecting allocation or indexing
- type confusion
- invalid aliasing assumptions
- uninitialized memory exposure
- data races

### 9.2 Native stop-ship defects

Treat the following as stop-ship defects unless explicitly justified and contained:

- unbounded input reads
- unchecked buffer writes
- unsafe string handling
- returning invalid or unstable pointers
- hidden ownership transfer
- allocator mismatch across boundaries
- use-after-close or use-after-free risks
- inconsistent cleanup after partial failure
- exceptions crossing unsupported boundaries
- unsynchronized shared mutable state
- UB-prone parsing of attacker-controlled input

### 9.3 Size and arithmetic safety

Validate:
- multiplication before allocation
- index arithmetic
- signed/unsigned conversions
- narrowing conversions
- sentinel assumptions
- capacity vs length invariants

Do not assume “small inputs” in security-sensitive paths.

### 9.4 Parsing in native code

Native parsers must:
- validate length before read
- validate enum/tag values
- validate structure before dereference
- reject malformed input safely
- avoid attacker-controlled unbounded recursion or allocation
- define behavior on partial and invalid data

---

## 10. Interop and Boundary Security

### 10.1 Security rules for Python ↔ C/C++ boundaries

Interop boundaries must define:
- ownership
- lifetime
- mutability
- encoding
- error translation
- thread-safety
- cleanup responsibility

Do not let any of these remain implicit.

### 10.2 Keep translation at the edge

Translate:
- Python exceptions ↔ native error model
- Python strings ↔ UTF-8 or explicit binary encoding
- Python buffers ↔ native pointer/size semantics
- native failures ↔ domain-relevant Python exceptions

Do not scatter conversion or trust logic across the stack.

### 10.3 Contain native failures

Do not let:
- C++ exceptions cross a C boundary
- ambiguous pointer ownership reach Python
- Python object lifetime assumptions leak into native code without documentation
- allocator assumptions cross runtimes without an explicit contract

### 10.4 Validate foreign input even from internal callers

A Python caller can still provide malformed or adversarial values to native code.
Native code must validate what matters for safety.

---

## 11. Serialization, Deserialization, and File Formats

### 11.1 Treat serialized data as untrusted

Files, IPC payloads, network messages, cache blobs, and persisted state may all be hostile or stale.

Validate:
- version
- length
- encoding
- field presence
- tag validity
- structural invariants
- size limits
- compression behavior if used

### 11.2 Prefer explicit formats

Prefer formats that are:
- versionable
- bounded
- easy to validate
- explicit about encoding and types

Avoid formats that:
- rely on implicit object reconstruction
- permit arbitrary code execution
- hide large or nested resource costs
- are difficult to validate incrementally

### 11.3 Do not deserialize rich object graphs from untrusted input by default

If rich deserialization is unavoidable:
- constrain types
- validate schema/version first
- isolate the operation
- bound memory and recursion behavior
- review the path as security-sensitive

---

## 12. Logging, Telemetry, and Observability

### 12.1 Security logging must be useful and safe

Log enough to support investigation without leaking secrets.

Useful security logs may include:
- operation attempted
- principal or subsystem identifier
- high-level reason for rejection
- error category
- correlation or request ID
- rate-limit or lockout events where applicable

Do not log:
- passwords
- tokens
- session cookies
- private keys
- full secret-bearing payloads
- raw credential headers

### 12.2 Avoid log injection and ambiguity

Treat externally influenced log fields as untrusted.
Avoid allowing hostile input to make logs misleading or structurally ambiguous.

### 12.3 Preserve auditability

Security-relevant changes should keep failure and access behavior auditable.
Do not remove useful security observability without an explicit reason.

---

## 13. Concurrency and Race Safety

### 13.1 Race conditions are security-relevant

Shared mutable state, check-then-use sequences, lifecycle transitions, and callback reentrancy can all create security bugs.

Document:
- thread-safety
- reentrancy
- lock ownership
- caller synchronization requirements
- callback context
- GIL behavior where relevant

### 13.2 Avoid TOCTOU assumptions

If a property matters for safety, do not assume it remains true after a separate check unless the design guarantees it.

### 13.3 Secure lifecycle transitions

For resources with lifecycle state:
- make states explicit
- define allowed transitions
- reject invalid operations deterministically
- define post-failure state clearly

---

## 14. Least Privilege and Process Boundaries

### 14.1 Minimize privileges

Code should operate with the smallest practical set of capabilities.

Limit:
- file access
- network access
- process execution
- token scope
- plugin capabilities
- environment inheritance
- elevated OS permissions

### 14.2 Isolate risky operations

When an operation is security-sensitive or exposed to hostile input, consider:
- process isolation
- capability reduction
- narrow interfaces
- timeouts
- bounded resource use
- reduced environment inheritance

### 14.3 Be explicit about privileged behavior

If a function or component performs privileged work, document:
- why it needs privilege
- what privilege it requires
- what inputs control it
- what safeguards exist
- what audit trail exists

---

## 15. Dependency and Supply Chain Expectations

### 15.1 Be deliberate about dependencies

Adding a dependency changes the attack surface.

Before adding one, consider:
- necessity
- maintenance quality
- update cadence
- security history
- license compatibility
- transitive dependency impact
- portability and build implications

### 15.2 Do not add dependencies casually for small conveniences

Prefer local code for very small, security-critical, or boundary-critical functionality when that reduces attack surface and complexity.

### 15.3 Pin and track intentionally

Follow repository policy for:
- version pinning
- lockfiles
- vendoring
- reproducible builds
- integrity verification

Do not bypass those workflows casually.

---

## 16. Security Review Triggers

Elevate review priority when changes touch:

- authentication or authorization
- credentials or secret handling
- parsers or deserializers
- file or path handling
- process spawning
- network surfaces
- plugin or dynamic loading
- interop boundaries
- memory ownership in native code
- concurrency-sensitive logic
- wire formats or persisted formats
- migrations or deployment paths
- generated code that affects runtime logic
- build or packaging logic that changes trust assumptions

For these changes, increase skepticism and validation depth.

---

## 17. Required Validation for Security-Relevant Changes

When a change is security-relevant, run as many of these as apply:

- boundary and invalid-input tests
- malformed-input tests
- regression tests for prior bugs
- integration tests across trust boundaries
- static analysis
- strong compiler warnings
- sanitizer runs for native code
- concurrency-oriented testing when relevant
- packaging/install validation when the change affects delivery
- permission and least-privilege sanity checks when relevant

Do not stop at a happy-path-only test.

For native code, prefer:
- ASan
- UBSan
- TSan where relevant
- `clang-tidy`
- `cppcheck`
- repository-native analysis tooling

---

## 18. Final Reporting Requirements

When a change affects security-relevant behavior, the final report must state:

- what security-relevant area was touched
- what trust boundary, if any, was affected
- what validation was run
- what assumptions were made
- what risks remain
- whether compatibility or privilege behavior changed

Be explicit.
Do not summarize security validation vaguely.

Good:
- “Touched the C parser for the wire format. Added malformed-length tests, reran native unit tests, and ran ASan/UBSan on the parser target.”

Bad:
- “Security checked.”
- “Looks safe.”
- “Validated thoroughly.” without specifics

---

## 19. Security Review Checklist

Use this checklist when reviewing security-sensitive changes.

### Input and parsing
- Is untrusted input validated at the boundary?
- Are lengths checked before access?
- Are ranges and enum/tag values validated?
- Are malformed inputs rejected safely?
- Are size and allocation limits enforced?

### Secrets and auth
- Could credentials leak to logs, files, or subprocesses?
- Are authentication and authorization decisions explicit?
- Is privilege minimized?
- Are failure paths safe and non-permissive?

### Injection and paths
- Is any shell execution safely structured?
- Are queries parameterized or otherwise constrained?
- Are paths normalized and constrained to allowed roots?
- Is dynamic evaluation avoided or tightly controlled?

### Native safety
- Could this introduce out-of-bounds access, lifetime bugs, races, or allocator mismatch?
- Are ownership and cleanup explicit?
- Are partial-failure states safe?

### Interop
- Is the boundary narrow and explicit?
- Are ownership, encoding, and error translation documented?
- Are exceptions contained appropriately?
- Is cleanup responsibility clear?

### Observability
- Are logs useful but sanitized?
- Is security-relevant behavior still auditable?

---

## 20. Anti-Patterns

Do not do the following unless there is a clearly documented and justified exception:

- trust external input by convention
- use permissive fallback behavior in security-sensitive paths
- concatenate untrusted data into shell commands
- deserialize rich objects from untrusted input by default
- log secrets or raw sensitive payloads
- leave ownership or cleanup implicit across boundaries
- hand-wave thread-safety
- expose unstable binary layouts as durable contracts
- treat memory corruption risks as mere “bugs” instead of security issues
- weaken validation to preserve backward compatibility without explicitly acknowledging the risk
- rely on tests alone when static analysis or sanitizers are available
- treat internal callers as automatically trusted

---

## 21. Maintenance Rule

Keep this document concrete and current.

When the repository changes:
- update threat-boundary notes
- update security-sensitive subsystem paths
- update dependency policy notes
- update validation commands referenced from `docs/build-and-test.md`
- update interop guidance when boundary patterns change
- remove obsolete assumptions

If the same security mistake appears repeatedly in reviews, add an explicit rule here.
