# Codex Install Health

`codex doctor` should be clean before treating a machine as fully healthy.
The most common local failure for this setup is an install/update target
mismatch:

```text
npm install -g @openai/codex would update a different install
```

This happens when the `codex` launcher runs a package resolved through `npx`,
or when another manager such as mise places its Codex binary before npm's
global bin directory on `PATH`. In that state, `codex` itself may work, but
`codex update` or `npm install -g @openai/codex` will not update the exact
package that the launcher executes.

## Diagnosis

Run:

```bash
which codex
type -a codex
npm root -g
npm list -g @openai/codex --depth=0
mise ls codex  # when mise manages Codex on this machine
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
npm install -g @openai/codex@0.147.0
hash -r
codex doctor --summary --no-color --ascii
```

If the machine uses a wrapper that always calls `npx`, prefer changing that
wrapper to execute the stable global package after the global install exists.
Do not replace a working wrapper with a guessed path before the package is
installed and verified.

If mise owns the first launcher on `PATH`, update that installation instead:

```bash
mise upgrade codex
hash -r
codex doctor --summary --no-color --ascii
```

Mise may intentionally delay very recent releases through
`--minimum-release-age`. Keep that safety delay unless the newest release is
explicitly required; an npm install does not bypass it for a mise-owned
launcher.

To keep other mise-managed tools on their normal policy while making Codex
follow same-day releases immediately, exempt only Codex and keep its selector
on the `latest` channel:

```bash
mise settings add minimum_release_age_excludes codex
mise use --global --fuzzy codex@latest
```

## Network Failure

If npm fails with DNS or registry errors, leave the wrapper unchanged and report
the machine as operational but not install-health-clean. Retry the preferred fix
from a normal shell when registry access is available.
