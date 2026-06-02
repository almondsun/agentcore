# Codex Config Compatibility

These notes capture the compatibility rules verified against `codex-cli 0.135.0`.

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

Use the agentcore permission profile for normal sessions:

```toml
default_permissions = "agentcore_workspace"

[permissions.agentcore_workspace]
extends = ":workspace"
```

Current Codex documentation says not to combine `default_permissions` with
top-level `sandbox_mode` or `[sandbox_workspace_write]`. The portable baseline
therefore keeps sandbox behavior in the named permission profile instead of
legacy sandbox keys.

The checked-in profile must remain path-free. The bootstrap helper may generate
target-machine local entries in live `~/.codex/config.toml`:

```toml
[permissions.agentcore_workspace.workspace_roots]
"/home/user/.codex/tmp" = true

[permissions.agentcore_workspace.filesystem]
"/home/user/.agents/skills" = "read"
```

Do not use the old `:project_roots` spelling. Secret path protection is handled
by lifecycle hooks instead of filesystem deny globs in the portable baseline.

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

## Windows notes

Native Windows installs can use Windows-specific sandbox keys, but the portable
baseline does not enable them globally:

```toml
# [windows]
# sandbox = "unelevated"
# sandbox_private_desktop = true
```

Use `python` rather than `python3` on stock Windows unless `python3` is known to
be configured. The `python3` launcher can be a Microsoft Store alias that exits
before running the bootstrap helper.

## 0.135.0 notes

- `gpt-5.5` is the current default model in this baseline.
- `features.goals` is stable in local `codex features list`; no explicit
  portable flag is needed.
- `features.tool_search` is removed in local `codex features list`; do not
  enable it in the portable baseline.
- `features.codex_git_commit`, `features.undo`, and legacy WebSocket feature
  flags report as removed locally; keep them absent.
- `features.web_search_cached` and `features.web_search_request` are deprecated;
  use top-level `web_search = "cached" | "live" | "disabled"` instead.
- `features.network_proxy` remains experimental and should stay disabled unless
  a concrete task needs sandboxed network policy.
- `unified_exec` is stable locally. Official docs note it is enabled by default
  except on Windows, so Windows setup should validate it rather than assuming
  parity with Linux.
- Managed `requirements.toml` can constrain approval policy, sandbox modes, web
  search, automatic review, feature flags, MCP servers, hooks, command rules,
  and network requirements. Keep those policy layers outside this portable
  mirror unless a task explicitly asks for managed-config material.
