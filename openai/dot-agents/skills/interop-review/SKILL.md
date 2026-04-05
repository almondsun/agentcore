---
name: interop-review
description: Use when reviewing Python/C/C++ boundaries, FFI layers, ABI-sensitive interfaces, or marshaling code where ownership, lifetime, cleanup, allocator rules, exception or status translation, encoding, copy-vs-borrow semantics, or thread-safety assumptions may be wrong or unclear. Do not trigger for single-language style review or ordinary application logic with no cross-language boundary.
---

# Interop Review

Review boundary contracts, not style. Prioritize correctness, safety, and contract clarity across Python, C, and C++ edges.

## Review Focus

- Ownership: who allocates, who frees, whether data is copied, borrowed, shared, or transferred.
- Lifetime: whether views, buffers, pointers, spans, or string-like references can outlive backing storage.
- ABI and layout: calling convention, struct layout, nullability, size, range, encoding, and stable boundary types.
- Cleanup: partial-initialization cleanup, error-path cleanup, idempotence, and documented destroy/free routines.
- Error translation: exceptions crossing C boundaries, status-code loss, silent truncation, or mismatched failure semantics.
- Allocator rules: memory allocated on one side and freed on another without an explicit supported contract.
- Concurrency and reentrancy: shared mutable state, callback threading assumptions, GIL expectations, and thread-affinity rules.
- Performance-sensitive boundaries: chatty fine-grained cross-language calls in hot paths when batching is expected.

## Findings Checklist

- Hidden ownership transfer or undocumented borrowing.
- Returned or retained pointers/references to invalid or unstable storage.
- Allocator mismatch or unclear free path.
- Exceptions crossing unsupported boundaries.
- Undefined, leaky, or underdocumented cleanup behavior.
- Encoding or binary-layout assumptions that callers cannot reliably satisfy.
- Thread-safety or reentrancy assumptions missing from the contract.
- Boundary chatter likely to cause avoidable overhead in hot paths.

## Output Contract

- Present findings first, ordered by severity.
- For each finding, state what is wrong, why it matters, likely impact, and the smallest safe fix when obvious.
- If no findings are found, say so explicitly and note any residual uncertainty such as missing tests, undocumented contracts, or unverified runtime assumptions.
