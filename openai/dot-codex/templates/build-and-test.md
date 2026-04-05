# Build and Test Guide

This document defines the canonical build, test, lint, type-check, static-analysis, sanitizer, packaging, and verification workflow for this repository.

Use it together with:
- `AGENTS.md` for the global engineering contract
- `docs/codex/architecture.md` for subsystem boundaries that determine scoped vs full validation
- `docs/codex/security.md` for trust-boundary, malformed-input, and privilege-sensitive validation expectations
- `docs/codex/performance.md` for benchmark and performance-validation expectations
- `docs/codex/ffi-and-interop.md` for boundary-specific validation of ownership, ABI, encoding, and error semantics
- `docs/codex/code-review.md` for review expectations around validation evidence and risk-based test depth

If there is any conflict:
1. CI configuration wins
2. Repository build files win
3. This document wins over generic guesses

---

## 1. Purpose

The purpose of this file is to make validation explicit and repeatable.

Every non-trivial change should answer:
- how do I build it?
- how do I test it?
- how do I lint or format-check it?
- how do I type-check it?
- how do I statically analyze it?
- how do I run sanitizers for native code?
- which narrower command is sufficient for a local change?
- which broader command is required before finalizing a risky change?

Do not substitute ad hoc commands when the canonical commands are known.

---

## 2. Source of Truth

When determining the correct build and test path, check these first:

- `README.md`
- CI workflows
- `pyproject.toml`
- `tox.ini`
- `noxfile.py`
- `requirements*.txt`
- `CMakeLists.txt`
- `CMakePresets.json`
- `meson.build`
- `Makefile`
- toolchain files
- linter and formatter configs
- test runner configs
- package manifests

If this document contains placeholders, replace them with the real commands from the repository.

If the repository supports multiple workflows, document one as canonical and list the others only as exceptions.

---

## 3. Repository Map

Replace this section with the real repository layout.

- Python package or service code: `<path>`
- Python tests: `<path>`
- C public headers / ABI layer: `<path>`
- C source: `<path>`
- C++ headers: `<path>`
- C++ source: `<path>`
- Native tests: `<path>`
- Integration tests: `<path>`
- Benchmarks: `<path>`
- Generated code: `<path or "none">`
- Vendor or mirrored third-party code: `<path or "none">`
- Build output directories: `<path>`
- Packaging or deployment assets: `<path>`

Special handling:
- ABI-sensitive code: `<path>`
- FFI / interop code: `<path>`
- Parser or serialization code: `<path>`
- Security-sensitive code: `<path>`
- Real-time / embedded / ISR-sensitive code: `<path>`

---

## 4. Canonical Commands

Replace placeholders with actual repository commands.

### 4.1 Full validation path

This is the broadest canonical path to run before finalizing risky or wide changes.

~~~sh
<full validation command sequence>
~~~

Typical responsibilities:
- configure
- build
- unit tests
- integration tests
- lint
- format check
- type check
- static analysis
- sanitizer runs where supported

### 4.2 Build

~~~sh
<build command>
~~~

Use this when:
- changing implementation code
- changing headers
- changing build scripts
- changing packaging or generated bindings
- validating that code compiles before narrower tests

### 4.3 Unit tests

~~~sh
<unit test command>
~~~

Use this for:
- implementation changes
- bug fixes
- local algorithmic changes
- most routine validation

### 4.4 Integration tests

~~~sh
<integration test command>
~~~

Use this when touching:
- interop boundaries
- file or wire formats
- storage layers
- network paths
- multiprocess behavior
- packaging or deployment-sensitive flows

### 4.5 Lint

~~~sh
<lint command>
~~~

### 4.6 Format check

~~~sh
<format check command>
~~~

### 4.7 Type check

~~~sh
<type check command>
~~~

### 4.8 Static analysis

~~~sh
<static analysis command>
~~~

### 4.9 Sanitizers

~~~sh
<sanitizer build/test command>
~~~

Use this when changing:
- C or C++ memory ownership
- pointer-heavy code
- parsers
- concurrency-sensitive code
- FFI boundaries
- allocation-heavy code

### 4.10 Packaging / distribution / install validation

~~~sh
<packaging command>
~~~

Use this when changing:
- package metadata
- install paths
- exported artifacts
- binary layout
- build outputs consumed by other tooling

---

## 5. Fast Local Validation Matrix

Use the smallest command set that still gives meaningful evidence.

### 5.1 Documentation-only changes

Run:
~~~sh
<docs check command or "none">
~~~

### 5.2 Python-only implementation changes

Minimum:
~~~sh
<python build/import sanity command>
<python unit test command>
<python lint command>
<python type check command>
~~~

### 5.3 C-only implementation changes

Minimum:
~~~sh
<native build command>
<native unit test command>
<static analysis command>
<sanitizer command if supported>
~~~

### 5.4 C++-only implementation changes

Minimum:
~~~sh
<native build command>
<native unit test command>
<static analysis command>
<sanitizer command if supported>
~~~

### 5.5 Public header or ABI changes

Minimum:
~~~sh
<full build command>
<abi-sensitive test or compatibility check>
<integration tests>
<static analysis>
~~~

Also:
- call out compatibility impact explicitly
- update regression coverage

### 5.6 Python ↔ C/C++ interop changes

Minimum:
~~~sh
<full native build command>
<interop or integration tests>
<python tests that exercise the binding>
<sanitizer command if supported>
~~~

Also verify:
- ownership rules
- cleanup behavior
- exception/status translation
- text encoding behavior
- shape/size validation where applicable

### 5.7 Build-system, packaging, or CI changes

Minimum:
~~~sh
<canonical full validation path>
~~~

### 5.8 Parser, serializer, or file-format changes

Minimum:
~~~sh
<unit tests>
<invalid-input tests>
<integration tests>
<sanitizer command if supported>
~~~

### 5.9 Concurrency or thread-safety changes

Minimum:
~~~sh
<unit tests>
<integration tests>
<thread-safety oriented tests if available>
<tsan or equivalent if supported>
~~~

---

## 6. Language-Specific Validation Guidance

### 6.1 Python

Prefer repository-native tooling. Typical commands may include:

~~~sh
pytest -q
python -m pytest
ruff check .
ruff format --check .
mypy .
pyright
~~~

When Python changes are made, verify as applicable:
- import paths still work
- public APIs still match documentation
- type-checking still passes
- exceptions are still mapped sensibly
- CLI behavior and exit codes remain correct if applicable

If Python orchestrates native code, also verify:
- boundary error translation
- resource cleanup behavior
- Unicode/text behavior
- array/buffer validation if relevant

### 6.2 C

Prefer repository-native commands. Typical checks may include:
- compiler warnings at strong levels
- unit tests
- `clang-tidy`
- `cppcheck`
- ASan / UBSan
- valgrind when relevant

When C changes are made, verify as applicable:
- headers compile cleanly
- no new warnings in touched code
- allocation and cleanup paths are correct
- public API contracts remain explicit
- no unsafe input or buffer handling was introduced
- parser behavior is hardened for malformed input

### 6.3 C++

Prefer repository-native commands. Typical checks may include:
- compiler warnings at strong levels
- unit tests
- `clang-tidy`
- ASan / UBSan / TSan where applicable

When C++ changes are made, verify as applicable:
- headers compile cleanly
- no exceptions cross unsupported boundaries
- ownership and lifetime remain explicit
- hot paths do not gain hidden allocations without justification
- view and iterator lifetimes remain safe
- ABI-sensitive interfaces remain stable if externally consumed

---

## 7. Change Triggers and Required Checks

Apply these rules when the corresponding change occurs.

### 7.1 If changing a public API, CLI contract, file format, or wire format

Required:
- full build
- regression tests
- integration tests where relevant
- compatibility impact noted in final report

### 7.2 If changing build scripts, packaging, toolchain settings, or CI assumptions

Required:
- canonical full validation path
- packaging/install validation if applicable
- final report must call out workflow impact

### 7.3 If changing parsers, serializers, or input validation logic

Required:
- valid-input tests
- malformed-input tests
- boundary-length tests
- sanitizer run if native code is involved

### 7.4 If changing C/C++ memory ownership, FFI, or ABI-sensitive code

Required:
- native build
- interop/integration tests
- static analysis
- sanitizers where supported
- final report must state ownership implications

### 7.5 If changing concurrency-sensitive code

Required:
- relevant tests
- stress or concurrency tests if available
- TSan or equivalent where supported
- final report must state thread-safety implications

### 7.6 If changing generated code

Required:
- regenerate from source when applicable
- do not hand-edit generated artifacts unless explicitly required
- validate generation path
- document source-of-generation

### 7.7 If changing vendor or mirrored third-party code

Required:
- minimize the patch
- validate the patch path
- document update or rebase implications

---

## 8. Expected Test Categories

For non-trivial changes, include or update the most relevant categories:

- happy-path tests
- boundary and edge-case tests
- invalid-input tests
- regression tests for reported bugs
- interop round-trip tests
- cleanup and lifetime tests
- concurrency tests where relevant
- compatibility tests where relevant
- smoke tests for packaging or installation where relevant

Do not stop at a happy-path-only test if the change affects a boundary or contract.

---

## 9. Interop Validation Checklist

Use this section whenever Python/C/C++ boundaries are involved.

Validate:
- ownership and cleanup
- borrow vs copy semantics
- text encoding
- error/status/exception translation
- buffer size and shape validation
- null or empty input handling
- repeated create/destroy or open/close behavior
- behavior after failure
- thread-safety assumptions if relevant
- batching or call-frequency assumptions in hot paths

High-value interop tests:
- null input
- zero-length input
- malformed UTF-8 or binary payloads where relevant
- undersized output buffers
- repeated cleanup
- failure during partial initialization
- Python exception mapping
- resource lifetime after explicit close
- large payload behavior

---

## 10. Sanitizer and Static Analysis Policy

When native code changes are made, use the strongest relevant validation available.

Preferred order:
1. repository-native sanitizer path
2. repository-native static-analysis path
3. repo-configured warning levels
4. targeted runtime sanity tests

If supported, prefer:
- ASan for memory safety
- UBSan for undefined behavior
- TSan for concurrency-sensitive code
- `clang-tidy` for native static analysis
- `cppcheck` where the repo uses it

Do not claim native code is well-validated if none of these were run and they were available.

---

## 11. Performance and Benchmark Validation

Use benchmark or performance checks when:
- modifying hot loops
- changing allocation strategy
- changing data layout
- changing cross-language call frequency
- changing serialization cost
- changing startup-critical or latency-sensitive code

If the repo contains benchmark tooling, document it here:

~~~sh
<benchmark command>
~~~

When performance is relevant, report:
- what path was expected to matter
- what was measured or at least sanity-checked
- what assumptions remain unverified

Do not add complexity for performance without evidence.

---

## 12. Packaging and Reproducibility

If the repository produces packages, libraries, wheels, shared objects, executables, or containers, document the canonical validation here.

Examples:
- Python wheel build
- native shared library build
- install smoke test
- import smoke test
- container build
- deployment artifact validation

Canonical commands:

~~~sh
<package build command>
<install smoke test command>
<artifact sanity check command>
~~~

If artifacts are consumed cross-language, verify:
- artifact location
- symbol/export availability if relevant
- version metadata
- import/load behavior
- runtime dependency assumptions

---

## 13. What to Report in the Final Response

Every non-trivial task should report:

- commands actually run
- what passed
- what failed
- what could not be run
- what remains unverified
- any compatibility, security, interop, or performance implications

Do not summarize validation vaguely.
Be specific.

Good:
- “Ran `cmake -S . -B build && cmake --build build`, `ctest --test-dir build`, and Python binding tests under `pytest tests/interop -q`.”

Bad:
- “Validated everything.”
- “Looks good.”
- “Builds fine.” without the command path

---

## 14. Maintenance Rule

Keep this document concrete.

When the repository changes:
- update canonical commands
- update subsystem paths
- update generated-code paths
- update CI-equivalent commands
- update sanitizer guidance
- remove obsolete workflows

If Codex repeatedly chooses the wrong command or misses an expected validation path, update this file.
