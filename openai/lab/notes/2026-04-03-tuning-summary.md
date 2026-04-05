# 2026-04-03 tuning summary

## Current practical status

Codex is ready to be used as a serious professional tool on real tasks.
The current practical rating is approximately `8/10` overall:

- strong on normal implementation workflows
- strong enough on notebook and coursework-style technical work
- improved on security-sensitive work because unresolved audit findings now force remediation or explicit failure
- still not a tool to trust blindly on high-risk trust-boundary changes without validation and review

## Durable artifacts kept

- live task repo: `../live_tasks/vendor_ingest_hardening/`
- harness archive: `../results/harness_runs/codex-eval-results/`
- Codex environment map: `/home/marti/.codex/README.md`
- custom skills map: `/home/marti/.agents/README.md`

## Important operating decisions

- keep `/home/marti/code/tmp` as disposable scratch
- keep durable Codex evaluation and tuning work in `/home/marti/code/codexlab`
- treat unresolved security audit findings as open work, not commentary
- use the tiny harness as a regression tool, not as the main optimization target
- use real tasks as the primary readiness benchmark

## What was intentionally not migrated

- `homeworks/` remains in `/home/marti/code/tmp/` because it is real coursework, not part of the Codex testing core by default

## Next recommended use

- keep future representative task sandboxes under `live_tasks/`
- keep saved scorecards and exported run outputs under `results/`
- record repeated failure modes and tuning decisions under `notes/`
