# codexlab inventory

Current durable inventory for `/home/marti/code/codexlab`.

| Path | Why it exists | Current status |
| --- | --- | --- |
| `AGENTS.md` | Workspace operating contract for Codex evaluation, tuning, and durable artifact handling. | Active source of truth for this workspace. |
| `README.md` | Human-facing overview of what belongs in `codexlab`. | Active root orientation document. |
| `evals/` | Reserved for reusable local evaluation assets, harness helpers, and scorecards. | Scaffold only; currently contains `evals/README.md` and no kept eval cases yet. |
| `live_tasks/config_migration_compat/` | Representative compatibility-sensitive live task for config-schema evolution and caller preservation work. | Active starter repo in pre-change state; intended to test backward-compatible config migration plus caller and test updates. |
| `live_tasks/vendor_ingest_hardening/` | Representative security-sensitive live-task sandbox used to judge Codex on normal repo work. | Kept specimen with task framing, source, and tests; current code already reflects a hardened implementation rather than a pristine vulnerable seed. |
| `notes/2026-04-03-tuning-summary.md` | Durable summary of current Codex readiness, migration decisions, and operating guidance. | Active historical note. |
| `results/harness_runs/codex-eval-results/2026-03-31/` | Preserved harness archive from earlier tuning/testing work. | Migrated dry-run archive with prompts, summary JSON, and one preserved workspace fixture; internal JSON paths still point at the original source location. |
| `snapshots/` | Reserved for prompts, final responses, transcripts, and other preserved evidence for important evaluations. | Scaffold only; currently contains `snapshots/README.md` and no preserved snapshots yet. |

Items intentionally not treated as durable artifacts:

- runtime caches such as `.pytest_cache/` and `__pycache__/`
- empty marker files with no preserved context or evidence value
- disposable experiments that still belong in `/home/marti/code/tmp`
