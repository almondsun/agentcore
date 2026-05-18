# Codex Config Compatibility

These notes capture the compatibility rules verified against `codex-cli 0.131.0`.

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

## Permission profile rules

Do not reintroduce the old inline `:project_roots` permission entry until it is
revalidated against the installed CLI:

```toml
":project_roots" = { "." = "write", "**/*.env" = "none" }
```

`codex-cli 0.131.0` rejected or warned on this setup in the live profile. Secret
path protection is handled by lifecycle hooks instead of that config pattern.

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
