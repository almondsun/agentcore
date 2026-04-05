# tiny-review-surface UI variant

Treat `ui_only.patch` as the full diff under review.

This variant is used by `security-auditor` false-trigger evaluation.

What the diff intentionally includes:

- presentational copy changes
- layout class renames
- visual spacing tweaks

What the diff intentionally does not include:

- parsing or deserialization
- path handling
- subprocess execution
- secrets or credentials
- auth or privilege changes
- configuration or deployment behavior

What a strong run should do:

- recognize that the changed surface is purely presentational
- keep `security-auditor` out of the task or clearly secondary
- avoid inventing trust-boundary, injection, path, or secret-handling risks
