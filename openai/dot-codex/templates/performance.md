# Performance Guide

This document defines the performance engineering standard for this repository.

Use it together with:
- `AGENTS.md` for global engineering rules
- `docs/codex/architecture.md` for subsystem boundaries and hot-path placement
- `docs/codex/build-and-test.md` for canonical validation paths
- `docs/codex/ffi-and-interop.md` for boundary and marshaling cost rules
- `docs/codex/code-review.md` for performance-focused review heuristics
- `docs/codex/security.md` when performance changes affect trust boundaries or resource limits

This file exists to make performance work explicit, evidence-driven, and compatible with correctness and maintainability.

Performance is not a license for cleverness.
Performance work must remain correct, reviewable, and justified.

---

## 1. Purpose

The purpose of this document is to ensure that performance-sensitive work in this repository:

- uses the right asymptotic approach
- avoids obvious waste
- measures meaningful behavior
- keeps hot paths in the right layer
- avoids hidden cost at language boundaries
- preserves correctness and safety
- remains maintainable under future change
- documents trade-offs honestly

Optimize for:
1. correctness under load
2. asymptotic soundness
3. predictable resource behavior
4. evidence-driven optimization
5. stable performance contracts where relevant
6. low boundary and marshaling overhead
7. maintainability

Do not optimize for aesthetics, folklore, or premature cleverness.

---

## 2. Core Principles

### 2.1 Correctness first

Performance improvements that weaken correctness are regressions, not improvements.

Do not accept:
- faster wrong answers
- faster unsafe parsing
- faster cleanup that leaks resources
- faster behavior that weakens validation
- lower latency from skipping required work
- lower memory usage from invalid lifetime assumptions

### 2.2 Optimize with evidence

Do not optimize based on intuition alone when measurement is feasible.

Evidence may include:
- benchmark results
- profiler output
- allocation counts
- wall-clock timing
- CPU usage
- memory usage
- I/O wait
- lock contention data
- boundary crossing counts
- production telemetry when available

If evidence cannot be collected, state that explicitly and use conservative reasoning.

### 2.3 Optimize where the cost is

Focus performance work on:
- hot loops
- frequent code paths
- large payload paths
- repeated allocations
- repeated copies
- repeated conversions
- repeated cross-language boundary calls
- lock contention
- startup-critical code
- latency-critical code
- memory-pressure-sensitive paths

Do not optimize cold code unless it removes a clear architectural bottleneck or safety issue.

### 2.4 Preserve clarity unless the payoff is real

Prefer the simplest design that meets the required performance.

If added complexity is justified, document:
- what cost mattered
- why the simpler approach was insufficient
- what assumptions the optimized path depends on
- what tests or checks protect the optimized behavior

### 2.5 Optimize the boundary, not just the local function

In mixed-language systems, performance is often dominated by:
- marshaling
- copying
- allocation churn
- repeated small calls across language boundaries
- string/encoding conversion
- synchronization
- cache-unfriendly layout
- serialization

Do not treat local function speed as the whole story.

---

## 3. Performance Goals and Budgets

Where practical, define the relevant performance goal before optimizing.

Typical goals include:
- throughput
- p50 latency
- p95 / p99 latency
- startup time
- steady-state memory usage
- peak memory usage
- allocation rate
- CPU utilization
- disk or network I/O cost
- cross-language boundary overhead

When a subsystem is performance-sensitive, document:
- the relevant metric
- expected input scale
- acceptable range
- critical workload shape
- environment assumptions
- whether the optimization target is latency, throughput, memory, or startup

Do not optimize without identifying which metric matters.

---

## 4. Performance Taxonomy

Use the right frame for the problem.

### 4.1 Asymptotic cost

Ask:
- is the algorithm appropriate for the expected scale?
- is there unnecessary repeated work?
- is the data structure appropriate?

### 4.2 Constant-factor cost

Ask:
- are we allocating too often?
- are we copying too much?
- are we converting or encoding too often?
- are we doing repeated map/set/string work in a hot loop?
- are we constructing temporary objects repeatedly?

### 4.3 Boundary cost

Ask:
- are we crossing Python/native boundaries too often?
- are we serializing and deserializing too often?
- are we doing chatty callback patterns where batching would help?
- are we forcing unnecessary copies between layers?

### 4.4 Memory cost

Ask:
- is the layout cache-friendly?
- is memory bounded?
- is peak memory proportional to the real need?
- are we retaining large objects too long?
- are we causing fragmentation or allocator stress?

### 4.5 Concurrency cost

Ask:
- are we contending on locks?
- are we synchronizing too often?
- are we holding locks while doing expensive work?
- are we over-parallelizing small tasks?
- are we creating scheduling overhead larger than the useful work?

---

## 5. Performance Workflow

For non-trivial performance work, follow this order:

1. identify the metric that matters
2. identify the workload that matters
3. measure the current behavior
4. find the dominant cost
5. make the smallest justified change
6. re-measure
7. keep the simpler version unless the improved one clearly wins
8. document the trade-off if complexity increased

Do not skip the “measure current behavior” step when measurement is practical.

---

## 6. General Rules

- Choose asymptotically sound approaches for expected scale.
- Avoid repeated work in hot paths.
- Avoid repeated allocation and deallocation when reuse is practical.
- Avoid repeated conversion between representations when one stable representation would suffice.
- Avoid repeated boundary crossings in tight loops when batching is practical.
- Avoid unnecessary copies of large data.
- Prefer stable, predictable data flow.
- Keep performance-sensitive assumptions explicit.
- Keep correctness and safety checks unless they are truly redundant and proven so.
- Do not weaken validation or contract clarity merely to gain speed.

---

## 7. Python Performance Guidance

Use Python primarily for:
- orchestration
- tooling
- control flow
- integration glue
- higher-level workflows
- tests and automation

### 7.1 Keep hot loops out of Python when justified

If a path is truly performance-critical:
- move the hot loop to native code or vectorized/native-library code when appropriate
- keep Python as the orchestration layer
- preserve a simple Python-facing contract

Do not move logic to native code merely because it feels more serious.

### 7.2 Avoid Python-side overhead in tight paths

Watch for:
- repeated object creation
- repeated attribute lookups in hot loops
- repeated string concatenation
- repeated conversion between bytes and str
- repeated conversion between Python containers and native buffers
- repeated crossing into C/C++ for tiny units of work

### 7.3 Prefer bulk operations

Prefer:
- one boundary call over many tiny calls
- bulk validation over repeated scalar validation where appropriate
- vectorized/native-library operations when they preserve clarity

### 7.4 Be explicit about copy behavior

When handling arrays, buffers, bytes, or large structures:
- document whether data is copied
- document whether zero-copy is attempted
- validate contiguity and dtype/shape expectations at the boundary when relevant

### 7.5 Avoid hidden fallback slow paths

If a fast path and slow path both exist:
- make the conditions explicit
- test both
- document what triggers the slow path
- avoid silent pathological behavior on common inputs

---

## 8. C Performance Guidance

Use C where explicit control, stable low-level interfaces, or constrained environments matter.

### 8.1 Respect data layout and locality

When performance matters:
- prefer contiguous data where practical
- reduce pointer chasing
- reduce indirection in hot paths
- avoid unpredictable access patterns when possible
- document layout-sensitive assumptions

### 8.2 Be disciplined about allocation

Avoid:
- repeated heap allocation in tight loops
- hidden allocation through helper layers
- allocation sizes influenced by unchecked arithmetic
- allocator churn when reuse is possible

Prefer:
- explicit reuse
- caller-provided buffers when appropriate
- fixed-capacity or bounded structures when predictability matters

### 8.3 Balance safety and speed honestly

Do not remove boundary checks or input validation merely to reduce cycles unless:
- the function is internal
- the preconditions are guaranteed by design
- the assumptions are documented
- the speedup matters
- the review confirms the safety story

### 8.4 Watch integer and size arithmetic

Performance work often changes indexing or sizing logic.
Do not introduce:
- overflow-prone size calculations
- signed/unsigned mistakes
- aliasing assumptions that are not valid
- UB in the name of speed

---

## 9. C++ Performance Guidance

Use C++ where RAII, stronger types, and zero-cost abstractions genuinely help.

### 9.1 Prefer value semantics when they are actually cheap enough

Value semantics often improve local reasoning and can still perform well.
But in hot paths:
- avoid accidental large copies
- inspect move/copy behavior
- watch allocator-backed containers
- reserve capacity where growth is predictable

### 9.2 Watch hidden cost in abstractions

Look for:
- repeated temporary construction
- hidden allocation
- unnecessary virtual dispatch
- repeated string creation
- repeated container growth
- accidental copies from pass-by-value
- expensive lambdas/functors captured by value when not needed

### 9.3 Keep headers and APIs from forcing unnecessary work

Review:
- whether a public API forces copying
- whether views have safe lifetime semantics
- whether `std::string_view` / `std::span` use avoids copies without creating lifetime hazards
- whether interfaces expose the right level of granularity

### 9.4 Avoid “template cleverness” as a substitute for measurement

Use templates or policy-based design only when they genuinely:
- remove runtime overhead
- improve type safety
- clarify a real variation point

Do not assume compile-time complexity is justified merely because runtime cost may be low.

---

## 10. Mixed-Language and Interop Performance Rules

This section is mandatory for Python/C/C++ systems.

### 10.1 Minimize boundary crossings

Cross-language calls often dominate cost.

Prefer:
- one coarse call over many tiny calls
- bulk transfer over per-element transfer
- batch processing over callback chatter
- stable memory representations over repeated conversion

Avoid:
- Python calling native code once per scalar item when batching is possible
- native code repeatedly calling back into Python in hot loops
- repeated conversion between text and bytes in tight paths
- repeated construction of boundary wrapper objects

### 10.2 Keep data in the right representation

Choose a representation that minimizes translation churn.

Examples:
- keep binary payloads as bytes/buffers instead of repeatedly converting
- keep numeric arrays in contiguous native-friendly memory when bulk native processing matters
- keep text encoding explicit and stable at the edge

### 10.3 Make copy policy explicit

For every high-volume boundary path, document:
- whether data is copied
- when it is copied
- why it is copied
- whether reuse or zero-copy is possible
- what lifetime constraints prevent zero-copy if applicable

### 10.4 Keep hot loops in the right layer

As a default:
- orchestration in Python
- hot computation in native code if justified
- boundary translation at the edge only

Do not distribute one hot loop across multiple layers if one layer can own it cleanly.

### 10.5 Watch callback cost and synchronization cost

Callbacks, locks, and marshaling can outweigh actual computation.
If callbacks are frequent:
- consider batching
- consider pull APIs
- consider buffered results
- consider coarser progress reporting

---

## 11. Memory Performance Rules

### 11.1 Measure memory, not just time

Memory problems may appear as:
- high peak usage
- fragmentation
- allocator churn
- paging
- cache misses
- GC pressure
- increased latency tails

### 11.2 Prefer bounded and predictable memory behavior

When possible:
- document maximum buffer growth
- reuse memory
- avoid retaining large structures after the hot path ends
- release resources promptly
- avoid duplicating full payloads across layers unnecessarily

### 11.3 Avoid accidental retention

Watch for:
- caches that never evict
- Python closures capturing large objects
- reference cycles
- long-lived shared ownership
- retained buffers after conversion
- container growth that never shrinks when that matters

---

## 12. Concurrency and Scalability Rules

### 12.1 Parallelism must pay for itself

Do not add concurrency unless it improves the metric that matters.

Account for:
- scheduling overhead
- synchronization cost
- data partitioning cost
- GIL constraints on Python-side work
- false sharing
- lock contention
- queueing overhead

### 12.2 Minimize contention

Prefer:
- confined ownership
- coarse independent work units
- immutable or append-only handoff where appropriate
- short lock hold times
- avoiding expensive work inside locks

### 12.3 State scalability assumptions explicitly

If performance depends on:
- number of cores
- workload size
- input distribution
- data locality
- batching
- lock contention
- external I/O latency

document that clearly.

### 12.4 Avoid performance gains that destroy debuggability

Highly concurrent optimizations must remain diagnosable and reviewable.
Do not create opaque scheduling behavior without a compelling reason.

---

## 13. Benchmarking and Profiling

### 13.1 Benchmark the right workload

Use workloads that reflect:
- realistic input sizes
- realistic input shapes
- realistic failure/success ratios when relevant
- realistic language-boundary usage
- realistic concurrency level

Do not optimize for toy inputs unless the subsystem truly operates on toy inputs.

### 13.2 Separate microbenchmarks from end-to-end checks

Use:
- microbenchmarks to isolate local cost
- end-to-end tests to verify system-level effect

A faster local function may not improve the real workflow.

### 13.3 Treat benchmark noise honestly

When reporting performance changes:
- mention variance when relevant
- avoid claiming precision not supported by the data
- distinguish “measured improvement” from “plausible improvement”
- mention environment assumptions if they matter

### 13.4 Keep benchmark code representative

Benchmark harnesses should not accidentally:
- remove important checks
- bypass realistic data conversion
- use unrealistic allocator behavior
- omit boundary cost that exists in production
- overfit to a single favorable input

---

## 14. Performance Review Triggers

Elevate performance scrutiny when changes touch:

- hot loops
- large payload handling
- Python/native boundaries
- serialization paths
- allocation-heavy code
- startup paths
- request fan-out
- lock-heavy or contention-prone code
- batching behavior
- parser throughput
- compression or encoding logic
- caches
- data layout
- parallel execution strategy

For these changes, review both local and end-to-end cost.

---

## 15. What to Measure

Measure the most relevant subset of these when applicable:

- wall-clock latency
- p50 latency
- p95 / p99 latency
- throughput
- allocation count
- peak memory
- retained memory
- CPU utilization
- lock contention
- boundary crossing count
- serialization/deserialization cost
- startup time
- steady-state cost
- cost per item / frame / request / sample / message

Do not collect metrics with no decision value.

---

## 16. Performance Regression Prevention

When a subsystem is known to be performance-sensitive:
- add or maintain a benchmark
- add threshold or trend tracking if the repo supports it
- document the important workload shape
- call out when a change knowingly spends more resources for correctness or maintainability

If a change likely slows something down but improves safety or correctness, say so explicitly.
Do not hide the trade-off.

---

## 17. Reporting Requirements

When a change is performance-relevant, the final report must state:

- what metric mattered
- what path or workload was considered
- what was measured or sanity-checked
- what changed
- what trade-off was accepted
- what assumptions remain unverified

Good:
- “Reduced Python/native boundary crossings from per-item calls to batched calls. Verified unit tests and ran the repo benchmark on 10k-item payloads; observed lower wall-clock time and fewer allocations.”

Bad:
- “Optimized performance.”
- “Should be faster now.”
- “Improved efficiency.” without evidence or reasoning

---

## 18. Review Checklist

Use this checklist when reviewing performance-relevant changes.

### Algorithm and scale
- Is the asymptotic approach appropriate?
- Is repeated work eliminated where it matters?
- Is the chosen data structure appropriate?

### Boundary cost
- Did the change increase or decrease Python/native boundary crossings?
- Is marshaling minimized?
- Is copy behavior explicit?
- Is text or binary conversion repeated unnecessarily?

### Allocation and memory
- Are allocations reduced or at least justified?
- Is memory growth bounded?
- Could this accidentally retain large objects longer?
- Are reuse and locality improved where they matter?

### Concurrency
- Does the change reduce or increase contention?
- Does parallelism actually help the target metric?
- Are locks held during expensive work?

### Safety and maintainability
- Did the optimization weaken validation, clarity, or lifecycle safety?
- Is the added complexity justified by a real payoff?
- Are the assumptions documented?

### Evidence
- Was anything measured?
- Is the reported benefit actually supported?
- Are unverified assumptions stated honestly?

---

## 19. Anti-Patterns

Do not do the following unless there is a clearly documented and justified exception:

- optimize before identifying the metric
- optimize without measuring when measurement is practical
- move logic to native code only for prestige
- weaken validation to gain speed
- add complexity for hypothetical wins
- introduce chatty cross-language APIs in hot paths
- ignore copy or marshaling cost
- benchmark toy inputs and claim real-world improvement
- hide a slower but safer behavior change
- over-parallelize small tasks
- rely on folklore such as “C++ is always faster” or “Python is always the bottleneck”
- micro-optimize cold code while ignoring dominant system costs

---

## 20. Maintenance Rule

Keep this document concrete and current.

When the repository evolves:
- update performance-sensitive subsystem notes
- update benchmark locations and commands
- update boundary-cost guidance if the interop model changes
- add review rules for recurring regressions
- remove stale assumptions about hot paths or workload shape

If the same performance mistake appears repeatedly in reviews, add an explicit rule here.
