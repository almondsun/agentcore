#!/usr/bin/env bash
set -euo pipefail

exec codex --profile readonly -c allow_login_shell=false "$@"
