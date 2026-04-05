# FFI and Interop Guide

This document defines how to design, implement, review, and validate boundaries between Python, C, and C++ in this repository.

Its purpose is to make mixed-language systems:
- correct
- hard to misuse
- stable across changes
- diagnosable under failure
- safe in memory and concurrency behavior
- clear about ownership, layout, encoding, and error semantics

Use it together with:
- `AGENTS.md` for global engineering rules
- `docs/codex/architecture.md` for subsystem boundaries and side-effect placement around language edges
- `docs/codex/build-and-test.md` for canonical validation paths and boundary-focused execution checks
- `docs/codex/security.md` for trust-boundary, parser, and failure-safety expectations
- `docs/codex/performance.md` for marshaling, batching, and boundary-cost guidance
- `docs/codex/code-review.md` for mixed-language review heuristics

---

## 1. Scope and Goals

This guide applies whenever code crosses one or more of these boundaries:
- Python ↔ C
- Python ↔ C++
- C ↔ C++
- process ↔ shared library
- runtime ↔ plugin
- native code ↔ generated bindings
- native code ↔ serialized buffers or wire formats

Optimize for:
1. stable contracts
2. explicit ownership and lifetime
3. explicit error semantics
4. ABI and layout safety
5. thread-safety clarity
6. low and predictable boundary cost
7. testability

Do not optimize first for convenience, cleverness, or minimal wrapper code.

---

## 2. Core Principles

### 2.1 Keep the boundary narrow

Expose the smallest surface that solves the problem.

Prefer:
- a few stable entry points
- explicit data carriers
- coarse operations with clear contracts

Avoid:
- chatty fine-grained calls across the boundary
- exposing internal helper functions
- leaking implementation-specific types
- exporting unstable data structures directly

### 2.2 Keep the boundary boring

Interop code should be conservative and unsurprising.

Prefer:
- simple types
- explicit buffers and lengths
- explicit lifecycle functions
- simple status/error returns
- stable, versionable interfaces

Avoid:
- hidden ownership transfer
- implicit allocation rules
- overloaded semantics
- exceptions escaping into foreign callers
- template-heavy or STL-heavy foreign interfaces

### 2.3 Keep translation at the boundary

Convert once at the edge.

Examples:
- Python `str` ↔ UTF-8 bytes
- Python exceptions ↔ status codes
- C++ internal objects ↔ opaque handles
- native structs ↔ serialized messages

Do not scatter conversion logic throughout the system.

### 2.4 Keep one clear owner

Every cross-language resource must have one clearly documented ownership model.

Valid models:
- caller-owned
- callee-owned
- shared with explicit refcount protocol
- borrowed for the duration of a call only
- borrowed until a clearly defined release point

If ownership is not obvious from the API, the API is not acceptable.

### 2.5 Prefer the lowest-complexity stable boundary

General preference order:

1. Pure C ABI
2. C ABI backed by C++ implementation
3. Python bindings over a C ABI
4. Python bindings directly over C++ only when justified and controlled

Use a direct Python ↔ C++ boundary only when it is clearly worth the additional complexity.

---

## 3. Choosing the Boundary Shape

### 3.1 Prefer a C ABI for long-lived foreign boundaries

Use a C ABI when:
- ABI stability matters
- multiple languages may call the library
- the library may be loaded dynamically
- you want to isolate C++ implementation details
- you need a simple FFI target for Python, Rust, Go, or other languages

Advantages:
- stable calling convention
- easier tool support
- easier symbol inspection
- easier long-term compatibility management

### 3.2 Use C++ only behind the ABI when possible

Prefer this pattern:

- public boundary: C-compatible header
- implementation: C++ source
- ownership and resource safety: handled internally with RAII
- foreign language: binds to the C ABI only

This keeps:
- exceptions contained
- STL types private
- templates private
- ABI churn localized

### 3.3 Use direct Python/native binding only when justified

Direct binding libraries can be effective, but they are not the default answer.

Use them only when:
- ergonomics clearly improve
- performance requires it
- the boundary is tightly controlled
- the team can maintain the binding surface competently

If using a direct Python/native binding library, document:
- ownership mapping
- exception mapping
- GIL behavior
- thread model
- lifetime constraints
- binary compatibility expectations

---

## 4. Supported Boundary Patterns

### 4.1 Opaque handle pattern

Use for stateful native objects.

Example shape:
- create/init returns handle
- operations accept handle
- destroy/free releases handle

Advantages:
- private internal layout
- ABI stability
- explicit lifecycle
- simpler foreign bindings

Rules:
- handle validity rules must be documented
- nullability rules must be documented
- repeated destroy semantics must be documented
- thread-safety of handle operations must be documented

### 4.2 Flat buffer + size pattern

Use for binary payloads, arrays, and encoded data.

Rules:
- always pass pointer and length together
- always document units: bytes, elements, samples, frames
- always document ownership of the buffer
- always document mutability
- always document whether aliasing is allowed

### 4.3 Struct-as-configuration pattern

Use for explicit argument groups, especially when APIs evolve.

Rules:
- prefer versionable config structs for growing APIs
- document default value semantics explicitly
- document padding/alignment assumptions if externally visible
- do not expose unstable internal fields as public contract

### 4.4 Callback pattern

Use only when streaming, progress, logging, or external control is truly needed.

Rules:
- document callback thread/context
- document whether reentrancy is allowed
- document callback lifetime rules
- document what may block and what must not block
- document whether callback exceptions/errors may abort the operation

Avoid callbacks when a simple pull API or returned result is sufficient.

---

## 5. Ownership and Lifetime Rules

### 5.1 Ownership must be explicit

For every pointer, handle, buffer, or view crossing the boundary, document:

- who allocates it
- who frees it
- who may mutate it
- how long it remains valid
- whether it may be retained after the call
- whether aliasing is permitted

### 5.2 Borrowed memory rules

Borrowed memory must have a clear validity window.

Examples:
- valid only during the call
- valid until the next mutation on the owning object
- valid until explicit release
- valid while the parent handle remains alive

Do not return borrowed memory whose validity depends on undocumented internal state.

### 5.3 Returned data rules

If a function returns data to a foreign caller, choose one of these models:

- caller provides output buffer and capacity
- callee allocates and caller frees with a provided free function
- callee writes into a stable object owned by a handle and returns a borrowed view with a documented validity window

Do not mix these models casually in one subsystem.

### 5.4 C++ lifetime containment

Keep C++ resource ownership inside C++ whenever possible.

Prefer:
- `std::unique_ptr` internally
- RAII-managed buffers and handles
- boundary objects translated into plain C representations only at the edge

Do not expose raw C++ object ownership rules directly to Python unless strictly necessary.

### 5.5 Python lifetime mapping

When exposing native resources to Python:
- map ownership into a clear Python object lifecycle
- ensure cleanup is deterministic enough for the use case
- provide explicit close/release methods where waiting for GC would be unsafe
- document whether context-manager usage is recommended or required

If the resource is scarce or externally visible, require explicit close semantics.

---

## 6. Error Model and Error Translation

### 6.1 One error model per boundary

Pick one primary boundary error model and use it consistently.

Common acceptable models:
- status code + output parameters
- status enum + error retrieval API
- nullable return + error retrieval API
- result object with status/details
- Python exception mapping at the Python layer

Avoid mixing:
- ad hoc sentinel values
- partial exceptions
- hidden global state
- inconsistent status conventions

### 6.2 C boundary error rules

At a C ABI boundary:
- do not throw C++ exceptions across the boundary
- translate internal exceptions into explicit error results
- document whether outputs are modified on failure
- document whether partial success is possible
- document whether error objects/messages must be freed

### 6.3 Python boundary error rules

At the Python layer:
- raise clear Python exceptions for programmer-visible failures
- map low-level failures into domain-relevant exceptions where practical
- preserve enough detail for diagnosis
- do not leak raw internal/native implementation noise unless it is genuinely useful

### 6.4 Error context

Error reporting should preserve:
- operation that failed
- high-level reason
- relevant identifier or argument name when safe
- native error code or category when useful
- whether retry is meaningful

Do not log or expose secrets in error paths.

### 6.5 Post-failure contract

Every fallible boundary function must make clear:
- whether outputs are untouched on failure
- whether partial mutation may have occurred
- whether the handle/resource remains usable
- whether cleanup is required after failure

---

## 7. ABI and Binary Compatibility Rules

### 7.1 ABI-sensitive boundaries must stay simple

For ABI-facing C APIs:
- use fixed-width integer types when representation matters
- document alignment and packing assumptions when relevant
- document endianness when data is serialized or shared externally
- avoid exposing compiler-specific constructs
- avoid exposing C++ standard library types
- avoid exposing implementation-dependent layouts unless frozen deliberately

### 7.2 Public structs must be treated as contracts

If a struct is visible to foreign callers:
- changing field order is a breaking change
- changing field types is a breaking change
- changing packing/alignment may be a breaking change
- changing ownership meaning is a breaking change

If the struct must evolve, prefer:
- version field
- size field
- reserved fields for future use
- accessor functions instead of direct field exposure

### 7.3 Symbol stability

When applicable:
- keep exported symbols minimal
- namespace or prefix symbols consistently
- hide internal symbols by default
- treat renames and removals as compatibility-impacting changes

### 7.4 Versioning

For any externally consumed boundary, document:
- semantic versioning policy if used
- what counts as a breaking change
- compatibility expectations between caller and callee versions

---

## 8. Data Representation Rules

### 8.1 Text encoding

Never leave text encoding implicit across the boundary.

Document whether text is:
- UTF-8 bytes
- UTF-16
- ASCII subset
- binary blob with no text semantics

For Python/native boundaries, UTF-8 is usually the preferred external byte representation unless a stronger reason exists.

### 8.2 Numeric ranges and units

Document:
- integer widths
- signedness
- floating-point precision
- saturation/truncation behavior
- units such as `[s]`, `[ms]`, `[Hz]`, `[bytes]`, `[samples]`

Do not rely on “obvious” units or ranges.

### 8.3 Arrays and buffers

Document:
- element type
- shape
- row-major/column-major if multidimensional
- stride assumptions if relevant
- contiguous vs non-contiguous requirements
- mutability
- ownership
- required alignment if relevant

### 8.4 Booleans and enums

Be careful with externally visible booleans and enums.

Document:
- exact representation if externally serialized or ABI-visible
- allowed enum values
- meaning of unknown or future values
- whether invalid values are rejected or normalized

### 8.5 Time and duration

Do not pass ambiguous time-like values.

Use names and documentation that make the meaning explicit:
- `timeout_ms`
- `sample_rate_hz`
- `start_s`
- `duration_s`

State:
- wall-clock vs monotonic
- absolute vs relative time
- time zone handling when relevant

---

## 9. Threading, Reentrancy, and Concurrency

### 9.1 Thread-safety must be explicit

For each boundary API, document whether it is:
- thread-safe
- thread-compatible but not safe for concurrent use on the same object
- single-threaded only
- reentrant
- ISR-safe or real-time safe if applicable

### 9.2 Callback context must be explicit

If callbacks are used, document:
- which thread invokes them
- whether they may race with other operations
- whether they may call back into the library
- whether they may block
- whether they may raise exceptions or fail

### 9.3 Python GIL rules

If Python is involved, document:
- whether native code requires the GIL
- whether the native implementation releases the GIL during long-running work
- whether callbacks into Python reacquire the GIL safely
- which objects must not outlive Python-managed state

### 9.4 Native concurrency rules

For C/C++ boundaries, document:
- shared-state synchronization ownership
- atomic vs mutex-based expectations
- lock ordering when externally relevant
- whether caller-side synchronization is required

Do not assume foreign callers infer your thread model correctly.

---

## 10. Memory Management and Allocation Strategy

### 10.1 Prefer caller-visible simplicity

Choose allocation models that are easy for foreign callers to use correctly.

Usually best:
- caller-owned output buffer when size is known or bounded
- explicit allocator/free pair when variable-sized outputs must be returned
- opaque handles for stateful resources

### 10.2 Avoid allocator mismatch

Do not allocate in one runtime and expect arbitrary freeing in another unless the API explicitly provides the correct free path.

Rules:
- if callee allocates, callee must provide the release function or retain ownership
- never assume `free()` from an arbitrary caller is valid unless documented and guaranteed

### 10.3 Large transfer policy

For large data:
- prefer batching
- prefer zero-copy only when lifetime rules remain clear
- prefer copying over fragile aliasing when correctness would otherwise degrade
- document cost trade-offs honestly

### 10.4 Hot path guidance

In performance-sensitive interop paths:
- avoid repeated allocation per call
- avoid repeated boundary crossings inside tight loops
- prefer bulk operations
- document whether buffers may be reused by the caller

---

## 11. API Shape Recommendations

### 11.1 Prefer explicit init/use/destroy lifecycles

For stateful native modules, prefer a lifecycle that is easy to reason about:

- create/init
- configure if needed
- use
- reset if needed
- destroy/free

Avoid hidden lazy initialization unless clearly justified and documented.

### 11.2 Prefer explicit output parameters when needed

When returning complex or multiple values across a C ABI:
- prefer explicit output parameters
- return status separately
- document output validity on failure

### 11.3 Avoid ambiguous null semantics

If null is allowed:
- document exactly what it means
- document whether it is equivalent to default behavior
- document whether it is valid for input, output, or both

### 11.4 Keep naming explicit

Names should reveal:
- ownership when relevant
- units when relevant
- blocking behavior when relevant
- whether the call mutates state
- whether the call may allocate

Examples:
- `buffer_capacity_bytes`
- `timeout_ms`
- `destroy_session`
- `read_frame`
- `encode_utf8`

---

## 12. Python Binding Guidance

### 12.1 Keep the Python layer thin but safe

Python bindings should:
- expose a Pythonic surface
- preserve contract clarity
- translate native errors cleanly
- own or borrow resources explicitly
- avoid hiding important lifetime constraints

### 12.2 Prefer explicit resource objects

For scarce or stateful resources, wrap them in Python objects with:
- explicit `close()`
- context-manager support when appropriate
- clear invalid-after-close behavior
- clear exception behavior after failed initialization

### 12.3 Python data exchange

When accepting arrays, buffers, or memory views:
- document contiguity requirements
- document dtype/element type
- document ownership and copy behavior
- validate shape and size at the Python boundary before entering deep native code when practical

### 12.4 Python exception mapping

Map categories sensibly, for example:
- invalid input → `ValueError`
- missing or invalid state → `RuntimeError` or a repo-specific exception
- resource exhaustion or OS failure → `OSError`-like or repo-specific wrapper
- programmer misuse → explicit, actionable exception

Do not expose meaningless low-level error codes without translation.

---

## 13. C and C++ Interop Guidance

### 13.1 Prefer C-compatible headers

If C and C++ meet at a public boundary:
- keep the public header C-compatible
- use `extern "C"` from the C++ side as needed
- keep templates and STL internals private

### 13.2 Keep C++ exceptions contained

At a C boundary:
- catch all internal exceptions
- translate to the boundary error model
- do not let stack unwinding cross into C

### 13.3 Use RAII behind the boundary

Internally in C++:
- use RAII to manage resources
- use `std::unique_ptr` and strong internal invariants
- translate into plain C shapes only at the edge

### 13.4 Keep ownership single-source

If C owns a handle and C++ implements it:
- document destroy path clearly
- ensure idempotence or document non-idempotence
- ensure cleanup is correct under partial initialization and failed operations

---

## 14. Serialization and File/Wire Boundaries

### 14.1 Treat serialized formats as contracts

If data crosses a file, pipe, socket, or shared-memory boundary:
- document versioning
- document encoding and endianness
- document optional vs required fields
- document failure behavior on malformed input

### 14.2 Keep parsing hardened

Parsers must:
- validate lengths before reading
- validate enum/tag values
- reject malformed or unsupported structures safely
- avoid unbounded recursion or uncontrolled allocation from hostile input

### 14.3 Translation layering

Prefer:
- parser/serializer at the edge
- validated internal representation after parsing
- no raw serialized data structures leaking into the core logic

---

## 15. Testing and Validation for Interop

### 15.1 Required validation categories

When changing an interop boundary, validate as many of these as apply:

- build succeeds through the canonical path
- ABI-facing headers compile cleanly in their intended language modes
- round-trip or integration tests across the boundary
- invalid-input tests
- ownership/lifetime tests
- cleanup tests
- concurrency tests when relevant
- sanitizer runs for changed native code when supported
- static-analysis checks when supported

### 15.2 High-value test cases

Prioritize:
- null / empty / zero-length inputs
- undersized output buffers
- malformed encodings
- invalid enum/tag values
- use-after-close scenarios
- repeated destroy or close behavior
- partial initialization failure
- error propagation across the boundary
- concurrency on shared handles when relevant
- large payload or repeated-call behavior in hot paths

### 15.3 Python/native tests

When Python binds native code, include tests for:
- exception translation
- lifetime after GC pressure when relevant
- explicit close semantics
- memoryview/bytes/str behavior
- Unicode handling
- array shape/dtype validation when relevant

### 15.4 Native validation tools

Prefer repository-native tools, but when supported, use:
- compiler warnings at strong levels
- `clang-tidy`
- `cppcheck`
- ASan
- UBSan
- TSan for concurrency-sensitive changes
- valgrind or platform equivalents when relevant

---

## 16. Review Checklist

Use this checklist when reviewing interop code.

### Contract
- Is the boundary narrow and stable?
- Are ownership and lifetime explicit?
- Are encoding, layout, and units explicit?
- Are thread-safety and reentrancy explicit?
- Is the error model explicit and consistent?

### Safety
- Could foreign callers free the wrong memory?
- Could the API return invalid borrowed memory?
- Could exceptions cross an unsupported boundary?
- Could malformed input cause overflow, UB, or uncontrolled allocation?
- Could callbacks reenter unsafely?

### Compatibility
- Is there any ABI-visible change?
- Is any public struct layout changed?
- Is any exported symbol changed or removed?
- Is any serialized or wire format changed?

### Performance
- Are there excessive boundary crossings?
- Are there repeated allocations in hot paths?
- Is copying justified and documented?
- Is batching preferable here?

### Usability
- Is the API hard to misuse?
- Are cleanup paths obvious?
- Are error messages actionable?
- Are null/default semantics understandable?

---

## 17. Anti-Patterns

Do not do the following unless there is a clearly documented, justified exception:

- expose STL containers in a C ABI
- throw C++ exceptions across a C boundary
- return pointers to temporary or unstable storage
- hide ownership transfer
- require callers to guess buffer sizes without a discovery path
- use ambiguous text encodings
- use callbacks when a simple return value or iterator-style API would do
- perform repeated tiny boundary crossings in a hot loop
- hand-wave thread-safety
- let Python GC timing be the only cleanup mechanism for scarce native resources
- assume allocator compatibility across runtimes
- leave malformed input behavior unspecified
- treat ABI-visible layout changes as harmless refactors

---

## 18. Documentation Requirements

For any public or shared interop surface, document at minimum:

- purpose of the boundary API
- ownership model
- lifetime rules
- mutability rules
- error model
- thread-safety model
- text encoding and binary-layout assumptions when relevant
- units and valid ranges when relevant
- cleanup requirements
- compatibility expectations if externally consumed

For non-trivial boundaries, also document:
- why this boundary shape was chosen
- what was intentionally kept private
- what validation was performed
- what limitations remain

---

## 19. Final Rule

Interop code must optimize for correctness and stability before convenience.

When forced to choose:
- prefer explicit over implicit
- prefer stable over clever
- prefer simple over magical
- prefer one extra copy over fragile ownership ambiguity
- prefer one extra wrapper over leaking unstable implementation details
- prefer clear failure over hidden corruption
