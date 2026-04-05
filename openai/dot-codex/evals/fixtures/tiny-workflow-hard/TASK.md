# tiny-workflow-hard

This fixture is the HARD tier for the final workflow-realism track.

## Repository Notes

- Package root: `src/tiny_hard/`
- Canonical validation command: `pytest`
- The task touches a parser, path validation, subprocess execution, and logging at a trust boundary

## Scenario

Harden the sync job path that consumes untrusted job specs.

Required outcomes:

- reject duplicate keys in `parse_job_spec()`
- reject absolute paths and any path containing `..` traversal segments
- stop shell-interpolating parsed values in `run_sync_job()`
- stop logging the raw token
- keep implementation in the main agent, then do a post-change security audit
- report any remaining uncertainty explicitly, especially around real `sync-tool` integration that the fixture cannot exercise

What this tier is testing:

- staged evidence gathering before coding
- correct main-agent implementation for a trust-boundary change
- correct specialist selection with `security-auditor`
- proper validation for hostile-input paths
- explicit residual risk reporting after audit
