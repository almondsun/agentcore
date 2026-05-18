#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/cleanup-worktrees.sh --list
  scripts/cleanup-worktrees.sh --remove PATH

The remove mode refuses dirty worktrees and refuses to remove the primary
agentcore checkout.
EOF
}

if [[ $# -eq 0 || "$1" == "--list" ]]; then
  git -C "$repo_root" worktree list
  exit 0
fi

if [[ "$1" != "--remove" || $# -ne 2 ]]; then
  usage >&2
  exit 2
fi

target="$(realpath "$2")"
primary="$(realpath "$repo_root")"
if [[ "$target" == "$primary" ]]; then
  echo "refusing to remove primary worktree: $target" >&2
  exit 2
fi
if [[ ! -d "$target/.git" && ! -f "$target/.git" ]]; then
  echo "not a git worktree: $target" >&2
  exit 2
fi
if [[ -n "$(git -C "$target" status --short)" ]]; then
  echo "refusing to remove dirty worktree: $target" >&2
  git -C "$target" status --short >&2
  exit 1
fi

git -C "$repo_root" worktree remove "$target"
