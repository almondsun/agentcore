# Codex Session Controls

Use these commands to keep long-running agentcore work bounded and recoverable.

## Core workflow

- `/status`: confirm the active model, permission profile, sandbox state,
  writable roots, context, and usage before or after risky changes.
- `/goal`: attach a concrete objective to a long task. Use it for migrations,
  repo-wide cleanup, evaluation runs, or multi-turn remediation.
- `/compact`: summarize a long thread after major evidence or validation
  milestones. Preserve completed actions, active assumptions, blockers, and the
  next command.
- `/fork`: branch a conversation when the implementation path genuinely splits.
  Keep one coherent task per main thread.
- `/side`: use a short side thread for a focused question that should not steer
  the parent task.
- `/agent`: inspect or resume spawned subagent threads when multi-agent work is
  active.

## Repo-specific conventions

- Use `/apps` when a connector is part of the task, such as GitHub triage.
- Use `/plugins` to inspect installed plugin capability before assuming a tool
  exists.
- Use `/hooks` after changing `hooks.json`, hook scripts, or managed hook
  policy so the loaded hook surface is visible.
- Use `/skills` when a task should explicitly follow one local skill.
- Use `/debug-config` when effective settings differ from
  `openai/dot-codex/config.toml`.
- Use `/statusline` and `/title` for local TUI preferences only; do not commit
  machine-specific display preferences unless they are intentionally portable.

## Windows-specific command

`/sandbox-add-read-dir` is Windows-only. Use it to grant a later sandboxed
command read access to an absolute directory outside the current readable roots.
Prefer the bootstrap-generated `agentcore_workspace` profile for durable local
skill and runtime grants.
