# Architecture Guide

This document defines the architecture standard for this repository.

Use it together with:
- `AGENTS.md` for global engineering rules
- `docs/codex/build-and-test.md` for canonical validation paths
- `docs/codex/ffi-and-interop.md` for Python/C/C++ boundary rules
- `docs/codex/security.md` for trust-boundary and failure-safety rules
- `docs/codex/performance.md` for hot-path and resource-cost guidance
- `docs/codex/code-review.md` for architectural review heuristics

This file exists to make architectural decisions explicit, reviewable, and stable under change.

Architecture is not decoration.
Architecture is the arrangement of responsibilities, boundaries, data flow, and failure behavior.

---

## 1. Purpose

The purpose of this document is to ensure that code in this repository:

- has clear subsystem boundaries
- keeps side effects at the edges
- makes ownership and lifecycle explicit
- keeps interfaces stable where stability matters
- places hot paths in the right layer
- preserves correctness under change
- stays testable without hidden global coupling
- scales structurally as complexity grows

Optimize for:
1. correctness
2. contract clarity
3. boundary discipline
4. testability
5. maintainability
6. safety/security
7. performance where justified
8. implementation elegance

Do not optimize for abstraction count, pattern count, or perceived sophistication.

---

## 2. Core Architectural Principles

### 2.1 Organize around responsibilities

Every non-trivial module should have a clear primary responsibility.

Good examples:
- parse a file format
- manage a native session lifecycle
- compute a deterministic transform
- orchestrate a workflow
- adapt a vendor API
- expose a stable C ABI
- provide Python bindings to a native subsystem

Bad examples:
- “misc utilities”
- “common helpers”
- “manager” without a precise responsibility
- large modules that mix parsing, business logic, I/O, and process control

### 2.2 Separate policy from mechanism

Keep business or domain decisions separate from low-level execution details.

Examples:
- algorithm selection separate from transport details
- validation rules separate from file reading
- access policy separate from persistence mechanism
- lifecycle state decisions separate from UI or CLI presentation

### 2.3 Keep side effects at the edges

Core logic should not:
- read files
- write files
- spawn processes
- talk to the network
- read environment variables
- print or log for core behavior
- terminate the process
- rely on wall-clock time unless the function’s purpose requires it

Instead:
- inject dependencies
- pass explicit inputs
- return structured results
- isolate side effects in adapters or orchestration layers

### 2.4 Make data flow explicit

A reader should be able to answer:
- where data comes from
- what validates it
- what transforms it
- who owns it
- where it leaves the subsystem
- what happens on failure

Avoid architectures that require chasing hidden state across many files.

### 2.5 Keep boundaries narrow and stable

Subsystems should interact through interfaces that are:
- small
- explicit
- typed
- documented where meaningful
- easy to validate independently

Do not expose internal convenience helpers as public subsystem contracts.

### 2.6 Prefer one obvious path

When the repository supports a primary architecture, reinforce it.

Avoid:
- multiple competing ways to do the same thing
- one subsystem using exceptions, another using sentinel values, another using callbacks, without an intentional boundary
- many overlapping helper layers that obscure the real path

---

## 3. Default Layer Model

Unless the repository already uses a different explicit structure, prefer this layered model.

### 3.1 Domain / Core

This layer contains:
- deterministic transformations
- validation rules
- algorithms
- state transitions
- mathematical or engineering logic
- invariant-preserving types

This layer should:
- be easy to test in isolation
- avoid framework coupling
- avoid hidden globals
- avoid direct file/network/process access
- avoid direct vendor SDK coupling where practical

### 3.2 Application / Orchestration

This layer contains:
- workflows
- use cases
- sequencing
- coordination across subsystems
- transaction-like control flow
- explicit error propagation across domain and infrastructure boundaries

This layer may:
- call multiple subsystems
- aggregate results
- choose strategies based on configuration or runtime context
- own high-level process flow

This layer should not become a dumping ground for low-level details.

### 3.3 Infrastructure / Adapters

This layer contains:
- filesystem access
- network clients and servers
- database access
- vendor SDK integration
- process execution
- OS APIs
- serialization/deserialization at boundaries
- UI / CLI boundary code
- FFI glue

This layer should:
- contain external complexity
- translate external types into internal types
- translate low-level failures into the repository’s error model where appropriate
- avoid leaking framework or vendor details into the core

---

## 4. Mixed-Language Architecture Model

This repository is optimized primarily for mixed Python / C / C++ systems work.

Default architectural role split:

- **Python**: orchestration, tooling, testing, automation, service glue, high-level workflows
- **C**: stable C interfaces, constrained runtimes, ABI boundaries, explicit low-level control
- **C++**: implementation-heavy native subsystems, RAII, stronger invariants, performance-sensitive code

### 4.1 Default boundary preference

Prefer the following when possible:

1. Python orchestrates
2. Python talks to a narrow C boundary
3. C boundary is implemented in C++ when stronger internal structure helps

This gives:
- a stable foreign boundary
- clear ownership and error translation
- contained C++ complexity
- easier long-term compatibility

### 4.2 Minimize cross-language surface area

Do not spread one conceptual subsystem across many tiny cross-language calls.

Prefer:
- one narrow boundary per subsystem
- coarse, meaningful calls
- explicit ownership rules
- translation at the edge
- native hot loops staying native when justified

Avoid:
- chatty callback-heavy designs
- repeated scalar calls across Python/native boundaries in hot paths
- exposing internal C++ structure directly to Python unless clearly justified

### 4.3 Keep one source of truth for ownership

For every boundary:
- one side owns the resource
- one destroy/free/release path is canonical
- one error model is canonical at the edge
- one representation is canonical for each payload crossing the boundary

If multiple layers think they own cleanup, the architecture is wrong.

---

## 5. Subsystem Boundaries

Every non-trivial subsystem should define:

- purpose
- public interface
- internal implementation details kept private
- ownership model
- error model
- thread-safety assumptions
- performance sensitivity if relevant
- configuration surface
- test strategy

A subsystem boundary is successful when:
- callers know what they may rely on
- private details remain replaceable
- tests can target the contract
- unrelated modules do not depend on private internals

---

## 6. Interface Design Rules

### 6.1 Interfaces should express contracts, not convenience

A good interface makes:
- valid use easy
- invalid use hard
- ownership visible
- errors explicit
- lifecycle understandable

Avoid “do everything” entry points with weak contracts.

### 6.2 Public APIs should be smaller than internal APIs

Internal helpers may be flexible.
Public subsystem boundaries should be conservative.

Prefer:
- narrow public API
- richer internal helper set
- internal refactoring freedom

### 6.3 Explicit beats magical

Prefer:
- explicit configuration
- explicit lifecycle transitions
- explicit conversion
- explicit cleanup
- explicit ownership

Avoid:
- hidden initialization
- hidden fallback paths
- ambient behavior via globals
- dynamic behavior that changes silently based on context

### 6.4 Contracts must survive failure

For any fallible interface, define:
- whether outputs are valid on failure
- whether state changed on failure
- whether cleanup is required
- whether retry is allowed
- whether the object remains usable

---

## 7. Choosing Patterns

Patterns are allowed tools, not markers of maturity.

Use a pattern only if it reduces coupling, clarifies variation, or improves testability.

### 7.1 Appropriate pattern triggers

Use **Dependency Injection** when:
- external collaborators affect testability, reproducibility, or portability

Use **Adapter** when:
- wrapping external systems, vendor SDKs, OS APIs, or foreign interfaces

Use **Facade / Service Layer** when:
- one workflow coordinates several moving parts and needs a stable entry point

Use **Strategy / Policy** when:
- a real algorithm or policy variation exists

Use **State Machine** when:
- behavior depends on lifecycle state or protocol state

Use **Factory / Builder** when:
- object or subsystem construction depends on environment, configuration, or backend selection

Use **Repository** when:
- persistence is a real architectural boundary

Use **Opaque Handle / Pimpl / ABI-Isolating Patterns** when:
- compatibility or compile-time insulation matters enough to justify indirection

### 7.2 Patterns to avoid by default

Avoid by default:
- singleton
- deep inheritance
- abstract hierarchies without real polymorphic need
- “manager” classes with mixed responsibilities
- interface layers whose only purpose is appearance
- macro-heavy pseudo-architectures in C
- template complexity without a measurable architectural payoff

### 7.3 Pattern burden of proof

If a pattern adds complexity, the code should make clear:
- what variation or risk it addresses
- why a simpler structure was insufficient
- what was intentionally kept private or simple

---

## 8. State and Lifecycle Architecture

### 8.1 Model state explicitly when state matters

If a subsystem has meaningful lifecycle phases, model them explicitly.

Typical examples:
- uninitialized
- configured
- running
- stopped
- faulted
- closed

Prefer:
- explicit state transitions
- validation around operations per state
- clear post-failure states

Avoid:
- scattered boolean flags
- undocumented sequencing assumptions
- “works if called in the right order” APIs

### 8.2 Lifecycle rules should be local

A reader should not need the entire codebase to answer:
- when the object becomes valid
- when it becomes invalid
- who closes or destroys it
- whether reuse/reset is supported
- what happens after failure

### 8.3 Separate setup, steady-state work, and teardown

When the subsystem is non-trivial, keep these phases distinct in design and tests.

---

## 9. Data and Representation Architecture

### 9.1 Pick one canonical internal representation

Do not let every layer invent its own interpretation of the same data.

Choose:
- one internal normalized shape
- one canonical text encoding where relevant
- one canonical units convention
- one canonical ownership rule

Perform translation at the boundaries.

### 9.2 Validate before normalization when boundary safety requires it

If input is untrusted or externally sourced:
- validate structural soundness
- validate sizes and tags
- then normalize

Do not normalize malformed data into ambiguous states.

### 9.3 Keep serialization at the edges

Serialized or wire representations should not become the internal domain model unless that is explicitly the design.

Prefer:
- parser/serializer at the boundary
- validated internal representation for core logic
- explicit conversion back to external form

---

## 10. Error Model Architecture

### 10.1 One dominant error style per subsystem

Choose a primary model and stay consistent inside the subsystem.

Examples:
- Python exceptions
- C status codes + output parameters
- C++ exceptions
- C++ status-return types
- explicit result objects

Mixing models is allowed only at deliberate translation boundaries.

### 10.2 Translate once at the edge

Examples:
- native status code → Python exception
- C++ exception → C error result
- vendor SDK failure → internal subsystem failure category

Do not leak raw external error conventions throughout the codebase.

### 10.3 Failure semantics are part of the architecture

Document and design for:
- unchanged state on failure
- partially changed state on failure
- retryable vs non-retryable errors
- fatal vs local failure
- cleanup obligations

---

## 11. Configuration Architecture

### 11.1 Make configuration explicit

Configuration should be:
- explicit
- typed where practical
- validated at the boundary
- easy to inspect
- separated from operational state

Avoid hidden configuration pulled from many implicit places.

### 11.2 Separate config from runtime state

Configuration is not the same as dynamic state.
Do not overload one structure to mean both if that harms clarity.

### 11.3 Fail fast on invalid configuration

Invalid configuration should fail clearly and early unless the product explicitly supports partial degraded operation.

---

## 12. Dependency Architecture

### 12.1 Keep dependencies directional

Preferred dependency direction:

- infrastructure depends on external libraries and systems
- application depends on domain and infrastructure interfaces
- domain depends on as little as practical

Do not let the domain layer depend directly on:
- web frameworks
- database clients
- CLI frameworks
- OS-specific SDKs
- vendor-specific transport APIs
- environment variables
- logging for core behavior

### 12.2 External dependencies must stay contained

Wrap third-party or platform-specific behavior behind adapters when:
- behavior is unstable
- the API is awkward
- the dependency is not the architectural center of the subsystem
- testability improves by containing it

### 12.3 Generated and vendor code are not architecture anchors

Do not let generated or vendor code define the conceptual structure of your system unless that is explicitly intended.

---

## 13. Testing Architecture

### 13.1 Architecture should support layered testing

Prefer a structure where you can test:

- domain/core logic without I/O
- application workflows with light fakes or test doubles
- infrastructure adapters with focused integration tests
- interop boundaries with round-trip tests
- end-to-end behavior only where necessary

### 13.2 Tests should target contracts

Tests should primarily encode:
- what is promised
- what is rejected
- what remains valid after failure
- what ownership/lifetime guarantees exist
- what boundary behavior matters

### 13.3 Do not depend on end-to-end tests to prove local correctness

If a local module can be tested directly, test it directly.

---

## 14. Performance Architecture

### 14.1 Put hot paths in the right layer

As a default:
- orchestration in Python
- hot computation in native code when justified
- translation at the boundary only

Do not distribute one hot path across many layers if one layer can own it cleanly.

### 14.2 Optimize system shape, not just inner loops

Architecture-level performance wins often come from:
- fewer boundary crossings
- fewer conversions
- fewer allocations
- better ownership design
- better batching
- better data layout
- less lock contention
- less duplicated parsing

### 14.3 Keep performance assumptions visible

If a subsystem depends on:
- batching
- contiguous layout
- fixed-size buffers
- thread confinement
- caller-side reuse
- preallocation

document it clearly.

---

## 15. Security Architecture

### 15.1 Put trust boundaries at clear edges

Security-sensitive validation should happen at subsystem boundaries.

Do not let untrusted data flow deep into the system before validation unless that is explicitly safe and justified.

### 15.2 Privilege should be localized

Privileged operations should sit behind narrow interfaces.
Do not let privilege assumptions spread across unrelated modules.

### 15.3 Keep dangerous behavior obvious

Examples:
- process spawning
- filesystem mutation
- network access
- plugin loading
- credential handling
- privileged configuration

These should be easy to locate architecturally.

---

## 16. Concurrency Architecture

### 16.1 Make concurrency ownership explicit

Document:
- which thread or task owns a resource
- what may be called concurrently
- who synchronizes shared state
- whether callbacks may reenter
- what may block

### 16.2 Prefer confined ownership when practical

Architectures with broad shared mutable state are harder to reason about and harder to secure.

Prefer:
- local ownership
- message passing
- explicit synchronization boundaries
- immutable handoff where practical

### 16.3 Concurrency assumptions are part of the contract

Do not leave thread-safety as folklore.

---

## 17. Build and Packaging Architecture

### 17.1 Build boundaries should match architectural boundaries

Where practical:
- separate public headers from private implementation
- separate binding code from core native code
- separate generated artifacts from hand-written code
- separate benchmark targets from production targets
- separate tests by layer when that improves clarity

### 17.2 Public artifacts are architectural outputs

Examples:
- wheels
- shared libraries
- executables
- Python packages
- generated bindings
- container images

Changes to these outputs are architectural changes when they affect callers, load paths, ABI, or distribution assumptions.

---

## 18. Review Heuristics for Architecture

During review, ask:

### Boundaries
- Is the responsibility of the changed module clear?
- Did the change strengthen or weaken subsystem boundaries?
- Did translation logic spread inward from the edge?
- Did a public API grow without good reason?

### Side effects
- Did core logic gain new side effects?
- Did process/network/filesystem behavior leak into the wrong layer?

### Ownership and lifecycle
- Is ownership clearer or less clear after the change?
- Is lifecycle state easier or harder to reason about?
- Did cleanup become more fragile?

### Coupling
- Did the change create hidden dependencies?
- Did it make a domain concept depend on infrastructure detail?
- Did it add a pattern without a real variation point?

### Interop
- Did the language boundary stay narrow?
- Are ownership, encoding, and error translation still explicit?
- Did the change increase boundary chatter or marshaling cost?

### Compatibility
- Did any externally visible contract change?
- Is the compatibility impact documented?

### Testability
- Is the changed behavior still testable at the right layer?
- Did the architecture become more dependent on end-to-end tests?

---

## 19. Architectural Triggers

Apply extra architectural scrutiny when a change does any of the following:

- introduces a new subsystem
- adds a new cross-language boundary
- changes a public API or ABI
- changes ownership or lifecycle semantics
- introduces caching or concurrency
- changes serialization or file-format behavior
- adds plugin or extension mechanisms
- changes process or deployment structure
- moves a hot path across layers
- adds a major dependency
- changes generated-code or binding generation workflow

For these changes, the final report should explicitly state:
- the boundary affected
- the responsibility split
- ownership/lifecycle implications
- compatibility implications
- validation run
- main remaining assumptions

---

## 20. Architecture Anti-Patterns

Do not do the following unless there is a clearly documented and justified exception:

- mix domain logic with filesystem, network, or process control
- let core logic depend directly on frameworks or vendor SDKs
- expose internal data layout as public contract without intention
- spread one conceptual workflow across many tiny boundary calls
- let ownership be implied instead of stated
- add interfaces with no real variation point
- create manager/god objects with mixed responsibilities
- rely on global mutable state for core behavior
- use design patterns as decoration
- keep multiple competing error models in one subsystem without a deliberate boundary
- leak C++ exceptions across a C boundary
- let Python/native translation logic spread across the codebase
- keep lifecycle sequencing implicit
- let tests be the only place where the architectural contract is discoverable

---

## 21. Recommended Documentation for Non-Trivial Subsystems

For each non-trivial subsystem, document at minimum:

- purpose
- public entry points
- main internal components
- ownership model
- error model
- lifecycle/state model
- thread-safety assumptions
- performance sensitivity if relevant
- trust boundaries if relevant
- test strategy
- compatibility constraints if externally consumed

If a subsystem is interop-heavy, also document:
- boundary language(s)
- encoding rules
- allocator/free rules
- marshaling rules
- copy vs borrow semantics

---

## 22. What to Report in the Final Response

When a task has architectural significance, the final response should include:

- what subsystem or boundary changed
- what responsibility split was used
- what was intentionally kept simple
- what patterns, if any, were used and why
- what ownership/lifecycle implications changed
- what compatibility implications changed
- what validation was run
- what assumptions remain unverified

Do not report only implementation details when the real change is architectural.

---

## 23. Maintenance Rule

Keep this document concrete and current.

When the repository evolves:
- update subsystem boundaries
- update role split across Python / C / C++
- update architecture notes for new public artifacts
- update interop assumptions when the boundary model changes
- add rules for recurring structural mistakes
- remove stale doctrine that no longer matches the codebase

If the same architectural mistake appears repeatedly in reviews, add an explicit rule here.
