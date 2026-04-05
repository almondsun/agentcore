# tiny-ffi-boundary

Treat `ffi_boundary.patch` as the full cross-language diff.

This fixture is shared by `interop-auditor`.

The patch intentionally includes:

- a returned buffer that now borrows memory from a local `std::string`
- allocator behavior drift across the boundary
- an asynchronous callback launched on a detached thread

What a strong run should do:

- focus on ownership, lifetime, allocator, ABI, and thread-safety
- call out copy-vs-borrow ambiguity immediately
- note any missing runtime or interop validation evidence
