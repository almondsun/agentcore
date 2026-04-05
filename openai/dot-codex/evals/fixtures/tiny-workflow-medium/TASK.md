# tiny-workflow-medium

This fixture is the MEDIUM tier for the final workflow-realism track.

## Repository Notes

- Package root: `src/tiny_medium/`
- Canonical validation command: `pytest`
- The task changes both API-facing and CLI-facing behavior

## Scenario

Product wants one consistent public status contract across the Python API and CLI output.

Implement this contract change:

- `summarize_user()` should now return `id`, `status_code`, and `display_status`
- status aliases such as `enabled` should normalize through the shared status module
- `format_summary_line()` should use the same shared normalization and render the display label instead of the raw input

Update the repo like a normal coding task: inspect the repo first, make the smallest correct cross-module change, update focused regression coverage, and run the broader validation path that matches a public interface change.

What this tier is testing:

- repo/context inspection before coding
- disciplined use of `pr-explorer` only if path discovery is genuinely useful
- broader validation when an interface contract changes
- no unnecessary security or interop escalation
- clean reporting of compatibility-sensitive work
