# Codex Install Health

`codex doctor` should be clean before treating a machine as fully healthy.
The most common local failure for this setup is an install/update target
mismatch:

```text
npm install -g @openai/codex would update a different install
```

This happens when the `codex` launcher runs a package resolved through `npx`,
but npm's global package root points somewhere else. In that state, `codex`
itself may work, but `codex update` or `npm install -g @openai/codex` will not
update the exact package that the launcher executes.

## Diagnosis

Run:

```bash
which codex
npm root -g
npm list -g @openai/codex --depth=0
codex doctor --summary --no-color --ascii
```

The healthy state is:

- the launcher resolves a stable installed package
- `npm list -g @openai/codex --depth=0` shows the expected Codex version
- `codex doctor` reports no install/update mismatch

## Preferred Fix

Install at least the version in `openai/dot-codex/compatibility.json` into the
same npm prefix used by the active Node runtime:

```bash
npm install -g @openai/codex@0.145.0
hash -r
codex doctor --summary --no-color --ascii
```

If the machine uses a wrapper that always calls `npx`, prefer changing that
wrapper to execute the stable global package after the global install exists.
Do not replace a working wrapper with a guessed path before the package is
installed and verified.

## Network Failure

If npm fails with DNS or registry errors, leave the wrapper unchanged and report
the machine as operational but not install-health-clean. Retry the preferred fix
from a normal shell when registry access is available.
