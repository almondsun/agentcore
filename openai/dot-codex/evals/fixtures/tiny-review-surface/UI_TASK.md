# tiny-review-surface UI variant

Treat `ui_only.patch` as the full diff under review.

This variant is a low-risk control case for specialist-routing evaluation.

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
- avoid escalating to unrelated specialist workflows
- avoid inventing trust-boundary, injection, path, or secret-handling risks
