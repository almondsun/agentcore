---
name: security-review
description: Use when reviewing code or changes that touch trust boundaries, auth, credentials, parsers, subprocesses, file paths, network surfaces, serialization, deserialization, FFI, native memory safety, deployment, or dangerous defaults. Do not trigger for general style review or ordinary low-risk edits with no security-sensitive surface.
---

# Security Review

Treat security as part of correctness. Focus on concrete risks at boundaries and in dangerous operations.

## Review Focus

- Input validation at trust boundaries.
- Parsing of untrusted or malformed data.
- Subprocess construction, shell invocation, and command injection risk.
- Path handling, traversal, symlink assumptions, temp-file behavior, and privilege boundaries.
- Secret handling in config, logs, traces, errors, tests, and generated artifacts.
- Serialization and deserialization boundaries, including unsafe loaders or schema drift.
- Network-facing behavior, auth flows, credentials, tokens, and insecure defaults.
- FFI and native code risks including UB-prone memory handling, integer overflow, unchecked buffers, and race-prone shared state.
- Deployment or runtime-generation logic that changes what code or config executes in production.

## Findings Checklist

- Missing validation or fail-open behavior at a trust boundary.
- Injection risk through shell, path, SQL, template, or serialization surfaces.
- Unsafe deserialization or unbounded parsing.
- Secret leakage or logging of sensitive values.
- Insecure default configuration when a safer default is practical.
- Unsafe native behavior that can affect correctness or exploitability.
- Dangerous operation reachable without explicit user intent or adequate guardrails.
- Concurrency behavior that can corrupt security-sensitive state.

## Output Contract

- Present findings first, ordered by severity.
- Keep each finding concrete: issue, risk, impact, and smallest safe remediation.
- Avoid vague language. If the risk is uncertain, state exactly what evidence is missing.
- If no findings are found, say so explicitly and call out any unreviewed surfaces or missing validation evidence.
- When this review is used post-change in an implementation workflow, findings that remain unresolved should force either follow-up remediation or an explicit failed closeout rather than a soft success.
- When practical, make it clear which findings are blocking for a successful closeout versus residual uncertainty that can remain with an honest pass.
