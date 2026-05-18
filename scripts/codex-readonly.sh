#!/usr/bin/env bash
set -euo pipefail

exec codex --profile readonly --sandbox read-only -c allow_login_shell=false "$@"
