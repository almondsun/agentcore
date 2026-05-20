# Codex Config Compatibility

These notes capture the compatibility rules verified against `codex-cli 0.132.0`.

## Validation contract

After changing `openai/dot-codex/config.toml` or live `~/.codex/config.toml`, run:

```bash
scripts/validate-codex.sh
```

For a smaller check during editing, run:

```bash
python3 scripts/bootstrap_codex_environment.py --validate-only
codex exec --strict-config --json --sandbox read-only --skip-git-repo-check 'Reply exactly OK.'
```

`codex doctor` performs live network, provider, and MCP reachability checks. Run
it from a normal shell or with network access available; a restricted agent
sandbox can produce false reachability failures even when the live setup is
healthy.

## Permission profile rules

Use the built-in workspace permission profile for normal sessions:

```toml
default_permissions = ":workspace"
```

If a custom permission profile is genuinely needed, `codex-cli 0.132.0` documents
`:workspace_roots` as the scoped filesystem token. Do not use the old
`:project_roots` spelling.

```toml
[permissions.custom.filesystem.":workspace_roots"]
"." = "write"
```

The portable baseline intentionally avoids custom filesystem profiles. Secret
path protection is handled by lifecycle hooks instead of filesystem deny globs.

## Login-shell behavior

Keep `allow_login_shell` at top level. The installed CLI accepts the top-level
key, but rejects profile-local copies under `--strict-config`.

For a strict read-only launch that disables login-shell behavior explicitly, use:

```bash
scripts/codex-readonly.sh
```

## Web-search profiles

The default keeps `web_search = "cached"` for low-friction docs lookup. Use the
`research` profile when current live web data matters:

```bash
codex --profile research
```

Use `ci` for non-interactive inspection where web access should be disabled.

## 0.132.0 notes

- `codex login status` is available for automation-friendly auth checks.
- `codex exec resume` now accepts `--output-schema`, matching first-run
  `codex exec --output-schema` structured-output validation.
- The live setup has `features.memories = true`; 0.132.0 rebuilds stale memory
  summary formats automatically, so no repo migration is needed.
- `goals` remains experimental and is intentionally not enabled in the portable
  baseline.
