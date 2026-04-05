# tiny-workflow-easy

This fixture is the EASY tier for the final workflow-realism track.

## Repository Notes

- Package root: `src/tiny_easy/`
- Canonical validation command: `pytest tests/test_validation.py`
- The fix should stay in one small module unless the agent finds a real contract reason to do more

## Scenario

`parse_retry_delay()` currently accepts blank or whitespace-only strings and silently turns them into `0`.

Fix the bug so blank input raises `ValueError` with an actionable message. Keep the change contained to the validation module, add or update focused tests, and finish like a normal coding task.

What this tier is testing:

- correct trigger discipline for a small local bug fix
- minimal repo inspection before editing
- implementation in the main agent
- narrow but real validation
- no unnecessary specialist spawning
- concise final reporting
