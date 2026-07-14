# Managed Codex Configuration

`agentcore` stores a personal portable Codex baseline. It should not pretend to
be the source of truth for enterprise-managed policy.

The bootstrap records repository-owned tree entries in
`~/.codex/agentcore-manifest.json`. Reconciliation removes only files previously
installed by agentcore, preserving independently installed skills and local
files. Retired managed trees are reconciled from this ownership record without
deleting unowned content.

Retirement requires descriptor-relative, no-follow file operations. On a
platform that cannot provide those guarantees, bootstrap preserves the files
and ownership entries instead of attempting deletion.

## What belongs here

- portable `~/.codex/config.toml` defaults
- reusable agents, skills, hooks, and rules
- documentation for how the portable baseline interacts with managed policy
- validation that reports policy conflicts clearly

## What stays outside this repo

- cloud-managed ChatGPT Business or Enterprise requirements
- system `requirements.toml` files under `/etc/codex/` or
  `%ProgramData%\OpenAI\Codex\`
- MDM-delivered macOS managed preferences
- managed hook script directories deployed by endpoint-management tooling
- organization-specific allowlists for MCP servers, network domains, or command
  rules

## Compatibility rule

Codex requirements can constrain permission profiles, approval policy,
approvals reviewer, legacy sandbox modes, web search, automatic review policy,
feature flags, MCP servers, hooks, command rules, and network policy. If
managed requirements conflict with the portable baseline, the managed layer wins
and validation should report the effective behavior instead of weakening the
managed policy.

Keep local repo changes focused on portable defaults. Add managed-config
examples only when they are generic and clearly marked as examples.

Hooks and content scanners remain defense in depth. The permission profile,
sandbox, app/MCP approval policy, and managed requirements are the enforcement
layers; do not rely on regex-based hook blocking as the only control.
