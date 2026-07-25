# Codex Config Compatibility

These notes capture the compatibility rules verified against `codex-cli 0.145.0`.
The machine-readable contract is `openai/dot-codex/compatibility.json`.

## Validation contract

After changing `openai/dot-codex/config.toml` or live `~/.codex/config.toml`, run:

```bash
scripts/validate-codex.sh
```

For a smaller check during editing, run:

```bash
python3 scripts/bootstrap_codex_environment.py --validate-only
codex exec --strict-config --json --config default_permissions='":read-only"' --skip-git-repo-check 'Reply exactly OK.'
```

`codex doctor` performs live network, provider, and MCP reachability checks. Run
it from a normal shell or with network access available; a restricted agent
sandbox can produce false reachability failures even when the live setup is
healthy.

## Permission profile rules

Use read-only permissions for normal sessions:

```toml
default_permissions = ":read-only"
```

Use the agentcore workspace permission profile only for trusted editing
profiles:

```toml
default_permissions = "agentcore_workspace"

[permissions.agentcore_workspace]
extends = ":workspace"
```

Current Codex documentation says not to combine `default_permissions` with
top-level `sandbox_mode` or `[sandbox_workspace_write]`. The portable baseline
therefore keeps sandbox behavior in the named permission profile instead of
legacy sandbox keys.

The checked-in profile denies `:root`, reopens `:minimal` read access, and keeps
machine-specific absolute paths out of the
portable baseline. The bootstrap helper may generate target-machine local
entries in live `~/.codex/config.toml`:

```toml
[permissions.agentcore_workspace.workspace_roots]
"/home/user/.codex/tmp" = true

[permissions.agentcore_workspace.filesystem]
"/home/user/.agents/skills" = "read"
```

Do not use the old `:project_roots` spelling. Keep secret-like workspace files
protected with permission-profile deny rules, and keep lifecycle hooks as an
additional prompt/tool guardrail rather than the only enforcement layer.

## Login-shell behavior

Keep `allow_login_shell` at top level. The installed CLI accepts the top-level
key, but rejects profile-local copies under `--strict-config`.

For a strict read-only launch that disables login-shell behavior explicitly, use:

```bash
scripts/codex-readonly.sh
```

## Web-search profiles

The default keeps `web_search = "disabled"` so routine inspection and planning
do not silently gather external context. Use the `research` profile when current
live web data matters:

```bash
codex --profile research
```

Use `ci` for non-interactive inspection where web access should be disabled.
Use `edit`, `review`, `readonly`, and `interop` when cached documentation lookup
is useful but live web freshness is not required.

Codex 0.134.0 and later reads profiles from files next to `config.toml`, not
from `[profiles.<name>]` tables inside `config.toml`. Keep the portable profile
overrides in these checked-in files:

- `openai/dot-codex/edit.config.toml`
- `openai/dot-codex/review.config.toml`
- `openai/dot-codex/readonly.config.toml`
- `openai/dot-codex/interop.config.toml`
- `openai/dot-codex/research.config.toml`
- `openai/dot-codex/ci.config.toml`

Profile files should use `default_permissions` rather than `sandbox_mode` so
they stay aligned with the permission-profile model introduced for Codex
0.138.0 and later.

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

## 0.145.0 / GPT-5.6 notes

- `gpt-5.6-sol` is the current flagship default in this baseline. The migration
  preserves medium reasoning effort as the first comparison point recommended by
  the GPT-5.6 upgrade guidance.
- Multi-agent V2 is stable but remains opt-in in Codex 0.145.0. This baseline
  enables it and uses the canonical
  `agents.max_concurrent_threads_per_session` setting instead of the legacy
  `agents.max_threads` alias.
- `allow_login_shell = false` and `shell_environment_policy.inherit = "core"`
  reduce ambient startup authority. Opt into broader shell behavior only for a
  concrete trusted workflow.
- Context7 is disabled in the base config and enabled only by the read-only
  `research` profile with prompt-by-default tool approval.
- External Browser Use, Computer Use, and automatic skill MCP dependency installs
  are disabled by default. App tools prompt for writes, destructive tools are
  disabled, and open-world app tools are disabled unless configured explicitly.
- `features.tool_search` is removed in local `codex features list`; do not
  enable it in the portable baseline.
- `features.terminal_resize_reflow` is removed in local `codex features list`;
  do not enable it in the portable baseline.
- `features.codex_git_commit`, `features.undo`, and legacy WebSocket feature
  flags report as removed locally; keep them absent.
- `features.web_search_cached` and `features.web_search_request` are deprecated;
  use top-level `web_search = "cached" | "live" | "disabled"` instead.
- `features.network_proxy` remains experimental and should stay disabled unless
  a concrete task needs sandboxed network policy.
- Experimental or under-development feature flags should not be enabled in the
  portable baseline unless a specific workflow needs them and the reason is
  documented.
- `features.hooks` is the canonical hook feature flag; `features.codex_hooks`
  is deprecated and must stay absent.
- `unified_exec` is stable and enabled by default except on Windows, so Windows
  setup should validate it rather than assuming parity with Linux.
- Managed `requirements.toml` can constrain permission profiles, approval
  policy, sandbox modes for legacy deployments, web search, automatic review,
  feature flags, MCP servers, hooks, command rules, and network requirements.
  Keep those policy layers outside this portable mirror unless a task explicitly
  asks for managed-config material.
