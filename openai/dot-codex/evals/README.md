# Codex Harness Evals

This harness evaluates the highest-value parts of the local Codex setup without introducing a large framework.

The sixth iteration keeps the system local and lightweight, adds one final tiered workflow-realism track, and reuses the existing harness patterns instead of introducing a new framework.

The second iteration added:

- frozen fixtures for the strongest positive cases
- stable result records and stored baselines
- a small comparison script for regression checks over time

The third iteration adds:

- one structured-output schema for `codex exec`
- one tiny automation manifest for a few supported cases
- one small runner that stages a disposable workspace copy, runs `codex exec`, and writes a comparable result record
- one small batch wrapper that runs the supported automated cases and prints one short status line per case

The fourth iteration adds:

- one dedicated false-trigger result schema
- one dedicated `codex exec` output schema for negative cases
- one small negative comparison script with false-trigger-specific regression rules
- one prompt-only automation lane for selected `should_not_trigger` cases
- batch flags to run positive cases, negative cases, or both without changing the default positive flow

The fifth iteration adds:

- automation for the remaining prompt-only specialist false-trigger gap
- one fixture-backed negative specialist case using the existing false-trigger schema and comparator
- minimal runner support for negative `patch-eval` cases without changing the batch or positive comparison flow

The sixth iteration adds:

- one final `workflow-realism` case file with exactly three tiers: EASY, MEDIUM, and HARD
- three tiny repo fixtures that exercise realistic implementation, validation, and reporting behavior
- automation entries and baselines for each tier using the existing `repo-bugfix` lane
- light schema and validator support for optional tier metadata

## Scope

Initial coverage focuses on:

- `build-validate`
- `orchestrated-review`
- `orchestrated-implementation`
- `reviewer`
- `interop-auditor`
- `security-auditor`
- `workflow-realism`

These evals are designed to catch regressions in:

- trigger discipline
- safety boundaries
- output shape
- validation/reporting behavior
- specialist selection behavior

## Evidence model

Automated runs use two separate model turns. The subject receives only a
dedicated natural-task file and the changed patch or workspace; it never sees
the expected subagents, pass criteria, fail signals, or outcome labels. The
runner captures the subject's JSONL event trace, final message, actual workspace
diff, and no-execution static parse evidence for implementation cases. A separate
read-only grading turn receives that evidence plus the rubric and emits the
structured result record.

This separation prevents rubric leakage and avoids treating the subject's own
claims about edits, tests, tools, or subagents as ground truth. Model grading
still requires human calibration. Deterministic parse failures and missing
implementation changes are hard failures; test claims remain trace evidence and
are never re-executed unsandboxed by the harness.

## Layout

```text
~/.codex/evals/
  README.md
  automation/
    manifest.json
  fixtures/
    manifest.json
    tiny-python-service/
      TASK.md
      api_breaking_change.patch
      pyproject.toml
      src/tiny_service/api.py
      src/tiny_service/normalize.py
      tests/test_api.py
      tests/test_normalize.py
    tiny-review-surface/
      TASK.md
      review_surface.patch
      UI_TASK.md
      ui_only.patch
    tiny-ffi-boundary/
      TASK.md
      ffi_boundary.patch
  baselines/
    build-validate/
      bv-api-boundary-positive.json
      bv-review-only-negative.json
    orchestrated-implementation/
      oi-bugfix-validate-positive.json
      oi-review-request-negative.json
    orchestrated-review/
      or-current-diff-multi-angle-positive.json
      or-single-docs-question-negative.json
    reviewer/
      rv-regression-review-positive.json
      rv-implementation-request-negative.json
    interop-auditor/
      ia-ffi-boundary-positive.json
      ia-pure-python-negative.json
    security-auditor/
      sa-parser-subprocess-positive.json
      sa-low-risk-ui-negative.json
  results/
    YYYY-MM-DD/
      batch-all-summary.json
      batch-negative-summary.json
      batch-summary.json
      <case-id>.json
      <case-id>.prompt.txt
      <case-id>.subject.txt
      <case-id>.trace.jsonl
      <case-id>.grader.prompt.txt
      <case-id>.grader.raw.json
      workspaces/
        <case-id>/
  schema/
    eval-case.schema.json
    result-record.schema.json
    codex-run-output.schema.json
    false-trigger-result.schema.json
    codex-false-trigger-output.schema.json
  scripts/
    eval_harness.py
    compare_results.py
    compare_false_trigger_results.py
    run_automated_case.py
    run_batch.py
  cases/
    build-validate.json
    orchestrated-review.json
    orchestrated-implementation.json
    reviewer.json
    interop-auditor.json
    security-auditor.json
```

## Eval Case Model

Each case file contains:

- `schema_version`
- `workflow`
- `cases`

Each case captures:

- when the workflow should trigger or should not trigger
- the scenario setup
- the fixture reference for frozen positive cases
- a runnable prompt
- expected output shape
- expected safety behavior
- expected validation/reporting behavior
- pass criteria
- fail signals

The authoritative schema is in [`schema/eval-case.schema.json`](schema/eval-case.schema.json).

## Fixture Convention

Positive cases should point at one frozen fixture via `fixture_ref`.

Use the lightest fixture that still makes the workflow repeatable:

- frozen patch only for review or audit workflows
- tiny repo plus one patch when implementation or validation context matters

The fixture catalog lives in [`fixtures/manifest.json`](fixtures/manifest.json).

## Final Workflow-Realism Track

The final track lives in [`cases/workflow-realism.json`](cases/workflow-realism.json) and reuses the existing fixture, baseline, automation, result, and comparison flow.

Tiers:

- `EASY`: one-module local bug fix with narrow validation and no specialist spawning
- `MEDIUM`: cross-module API and CLI contract change with repo inspection and broader validation; bounded `pr-explorer` use is optional when direct inspection is sufficient
- `HARD`: parser and subprocess hardening with a justified `security-auditor` post-change audit; unresolved audit findings must close as `fail`, not soft success

All three tiers are safely automatable with the current runner because each uses
a tiny self-contained Python repo and the existing `repo-bugfix` mode. The
subject runs repo-native validation inside its Codex sandbox; the host harness
only performs non-executing syntax and data-format checks.

## Result Record Convention

Store run results outside the case definitions, for example:

- `~/.codex/evals/results/<date>/<case-id>.json`

Keep source eval cases and baselines stable and treat `results/` as run history.

By default the harness writes run artifacts under `~/.codex/evals/results/`. When the harness tree is read-only in your environment, use `--results-dir <path>` on `eval_harness.py scaffold-result`, `run_automated_case.py`, or `run_batch.py` to keep writable run history elsewhere without changing the case or baseline catalog.

The authoritative result schema is in [`schema/result-record.schema.json`](schema/result-record.schema.json).

Automated `codex exec` runs first target a slightly smaller structured-output contract and then the runner stamps `run_timestamp` and writes the final comparable result record. The structured final-message schema lives in [`schema/codex-run-output.schema.json`](schema/codex-run-output.schema.json).

Use short stable tokens inside these arrays so baseline comparison stays inspectable:

- `observed_subagents`
- `observed_validation`
- `observed_fail_signals`

Example result record:

```json
{
  "schema_version": "2",
  "case_id": "bv-api-boundary-positive",
  "workflow": "build-validate",
  "fixture_ref": "tiny-python-service",
  "run_timestamp": "2026-03-31T15:00:00Z",
  "outcome": "pass",
  "observed_subagents": [],
  "observed_validation": [
    "scope:escalated",
    "command:pytest",
    "reporting:explicit-buckets"
  ],
  "observed_fail_signals": [],
  "notes": "Used the frozen API-breaking patch and called out compatibility risk.",
  "rubric": {
    "trigger_match": true,
    "output_shape_ok": true,
    "safety_ok": true,
    "validation_ok": true
  }
}
```

## False-Trigger Result Convention

Negative automation uses a dedicated false-trigger result shape stored in the same `results/<date>/` history area, for example:

- `~/.codex/evals/results/<date>/bv-review-only-negative.json`

The authoritative false-trigger result schema is in [`schema/false-trigger-result.schema.json`](schema/false-trigger-result.schema.json).

Automated negative `codex exec` runs use a dedicated structured final-message schema in [`schema/codex-false-trigger-output.schema.json`](schema/codex-false-trigger-output.schema.json).

Key negative fields:

- `expected_should_trigger`: whether the workflow under test should trigger, which is `false` for the automated negative lane
- `actual_trigger_behavior`: one of `not_triggered`, `secondary_only`, `partial_trigger`, or `primary_trigger`
- `unexpected_subagents`: wrongly-triggered explorers or specialists
- `unexpected_validation`: validation-first or implementation-first behavior that should not have appeared
- `fail_signals`: explicit false-trigger failures such as task hijacking or wrong-workflow output shape

Example false-trigger result record:

```json
{
  "schema_version": "1",
  "case_id": "or-single-docs-question-negative",
  "workflow": "orchestrated-review",
  "run_timestamp": "2026-03-31T15:00:00Z",
  "expected_should_trigger": false,
  "actual_trigger_behavior": "not_triggered",
  "outcome": "pass",
  "unexpected_subagents": [],
  "unexpected_validation": [],
  "fail_signals": [],
  "notes": "Stayed on a narrow docs-answer path instead of turning into multi-agent review orchestration.",
  "rubric": {
    "trigger_match": true,
    "output_shape_ok": true,
    "task_focus_ok": true,
    "safety_ok": true
  }
}
```

## Baseline Convention

Treat each baseline as one known-good result record stored at:

- `~/.codex/evals/baselines/<workflow>/<case-id>.json`

Baselines should exist for the strongest positive fixture-backed cases first. Negative cases can stay documentation-first until they are worth freezing.

## Automated Runner

The automated path is intentionally narrow.

Supported positive cases now:

- `bv-api-boundary-positive`
- `or-current-diff-multi-angle-positive`
- `oi-bugfix-validate-positive`
- `rv-regression-review-positive`
- `ia-ffi-boundary-positive`
- `sa-parser-subprocess-positive`

Supported negative cases now:

- `bv-review-only-negative`
- `or-single-docs-question-negative`
- `oi-review-request-negative`
- `ia-pure-python-negative`
- `rv-implementation-request-negative`
- `sa-low-risk-ui-negative`

Support is declared in [`automation/manifest.json`](automation/manifest.json).

Each automated run:

1. loads the case and fixture metadata
2. stages a disposable workspace copy under `results/<date>/workspaces/<case-id>/`
3. builds a blind subject prompt from a dedicated natural-task file
4. runs the subject with JSONL tracing and saves its normal final message
5. captures the actual workspace diff and independent no-execution parse evidence
6. runs a separate read-only grader with the rubric and captured evidence
7. writes the comparable result record as `<case-id>.json`

Positive automation uses the original result-record schema and comparison flow. Negative automation uses the dedicated false-trigger schema and comparison script, but the same runner entry point and batch wrapper.

Specialist-positive automation also uses the original positive result-record schema and `compare_results.py`, but the prompt is deliberately narrower than a top-level workflow case: it isolates one specialist against a frozen patch and checks role discipline, findings shape, and specialist-specific risk detection rather than orchestration quality.

Negative automation now has two forms:

- prompt-only false-trigger checks for routing discipline when wording alone is enough
- fixture-backed `patch-eval` false-trigger checks when the changed surface itself should suppress the wrong specialist

The fixture-backed negative specialist case uses the lightest practical shape: a frozen patch plus one small task file inside the existing `tiny-review-surface` fixture directory. That keeps the harness local and simple while making the diff content, not just the wording, drive the false-trigger decision.

The optional batch wrapper reuses the same single-case runner and, by default, compares each new result against its matching stored baseline with the appropriate comparator for that case kind.

## How To Run

Validate the harness files, fixture references, baseline records, and automation manifest:

```bash
python3 scripts/eval_harness.py validate
```

List the available workflows and cases:

```bash
python3 scripts/eval_harness.py list
```

Show one case in a runnable form:

```bash
python3 scripts/eval_harness.py show bv-api-boundary-positive
```

Print a blank result template for one case:

```bash
python3 scripts/eval_harness.py template bv-api-boundary-positive
```

Print a blank false-trigger template for one negative case:

```bash
python3 scripts/eval_harness.py template bv-review-only-negative
```

List the currently automated cases:

```bash
python3 scripts/eval_harness.py list-auto
```

List the currently automated negative false-trigger cases:

```bash
python3 scripts/eval_harness.py list-auto-negative
```

Write a result scaffold directly into `results/`:

```bash
python3 scripts/eval_harness.py scaffold-result bv-api-boundary-positive
```

Write a false-trigger scaffold for one negative case:

```bash
python3 scripts/eval_harness.py scaffold-result bv-review-only-negative --date 2026-03-31
```

The scaffold is intentionally incomplete. Fill in the observed fields before comparing it to a baseline.

Compare a new result to its stored baseline:

```bash
python3 scripts/compare_results.py \
  --baseline baselines/build-validate/bv-api-boundary-positive.json \
  --result results/2026-03-31/bv-api-boundary-positive.json
```

Run one supported automated case:

```bash
python3 scripts/run_automated_case.py bv-api-boundary-positive --date 2026-03-31
```

Run the reviewer specialist-positive case:

```bash
python3 scripts/run_automated_case.py rv-regression-review-positive --date 2026-03-31
```

Run the interop-auditor specialist-positive case:

```bash
python3 scripts/run_automated_case.py ia-ffi-boundary-positive --date 2026-03-31
```

Run the security-auditor specialist-positive case:

```bash
python3 scripts/run_automated_case.py sa-parser-subprocess-positive --date 2026-03-31
```

Run one supported automated negative case:

```bash
python3 scripts/run_automated_case.py bv-review-only-negative --date 2026-03-31
```

Run the remaining reviewer false-trigger case:

```bash
python3 scripts/run_automated_case.py rv-implementation-request-negative --date 2026-03-31
```

Run the fixture-backed security false-trigger case:

```bash
python3 scripts/run_automated_case.py sa-low-risk-ui-negative --date 2026-03-31
```

Dry-run one automated case without calling Codex:

```bash
python3 scripts/run_automated_case.py bv-api-boundary-positive --date 2026-03-31 --dry-run
```

Dry-run one automated negative case without calling Codex:

```bash
python3 scripts/run_automated_case.py bv-review-only-negative --date 2026-03-31 --dry-run
```

Run the same negative dry-run with an explicit writable results root:

```bash
python3 scripts/run_automated_case.py \
  ia-pure-python-negative \
  --date 2026-03-31 \
  --dry-run \
  --results-dir ../codex-eval-results
```

Dry-run the fixture-backed negative specialist case with an explicit writable results root:

```bash
python3 scripts/run_automated_case.py \
  sa-low-risk-ui-negative \
  --date 2026-03-31 \
  --dry-run \
  --results-dir ../codex-eval-results
```

Compare a new false-trigger result to its stored negative baseline:

```bash
python3 scripts/compare_false_trigger_results.py \
  --baseline baselines/build-validate/bv-review-only-negative.json \
  --result results/2026-03-31/bv-review-only-negative.json
```

Compare the reviewer implementation-request negative case to its baseline:

```bash
python3 scripts/compare_false_trigger_results.py \
  --baseline baselines/reviewer/rv-implementation-request-negative.json \
  --result results/2026-03-31/rv-implementation-request-negative.json
```

Compare the fixture-backed security UI negative case to its baseline:

```bash
python3 scripts/compare_false_trigger_results.py \
  --baseline baselines/security-auditor/sa-low-risk-ui-negative.json \
  --result results/2026-03-31/sa-low-risk-ui-negative.json
```

Run all supported automated cases in one batch:

```bash
python3 scripts/run_batch.py --date 2026-03-31
```

Run all supported automated negative cases in one batch:

```bash
python3 scripts/run_batch.py --negative --date 2026-03-31
```

Run all supported automated negative cases in one batch with an explicit writable results root:

```bash
python3 scripts/run_batch.py \
  --negative \
  --date 2026-03-31 \
  --dry-run \
  --results-dir ../codex-eval-results
```

Run both positive and negative automated cases in one batch:

```bash
python3 scripts/run_batch.py --all --date 2026-03-31
```

Run a selected subset in one batch:

```bash
python3 scripts/run_batch.py \
  bv-api-boundary-positive \
  oi-bugfix-validate-positive \
  --date 2026-03-31
```

Run only the three specialist-positive cases in one batch:

```bash
python3 scripts/run_batch.py \
  rv-regression-review-positive \
  ia-ffi-boundary-positive \
  sa-parser-subprocess-positive \
  --date 2026-03-31
```

Run a selected negative subset in one batch:

```bash
python3 scripts/run_batch.py \
  --negative \
  bv-review-only-negative \
  ia-pure-python-negative \
  rv-implementation-request-negative \
  sa-low-risk-ui-negative \
  --date 2026-03-31
```

Run a mixed positive and negative subset in one batch:

```bash
python3 scripts/run_batch.py \
  --all \
  bv-api-boundary-positive \
  bv-review-only-negative \
  --date 2026-03-31
```

Force a rerun for the same date and overwrite existing case artifacts:

```bash
python3 scripts/run_batch.py --date 2026-03-31 --force
```

Skip baseline comparison and only record fresh results:

```bash
python3 scripts/run_batch.py --date 2026-03-31 --no-compare
```

Write the machine-readable batch summary to a custom location:

```bash
python3 scripts/run_batch.py \
  --date 2026-03-31 \
  --summary-file results/2026-03-31/my-batch-summary.json
```

## Manual Evaluation Loop

1. Pick a case with `list` or `show`.
2. Open the frozen fixture or tiny fixture repo named by `fixture_ref`.
3. Run the prompt in Codex against that fixture.
4. Compare the response and behavior against:
   - `expected_output_shape`
   - `expected_safety_behavior`
   - `expected_validation_behavior`
   - `pass_criteria`
   - `fail_signals`
5. Write a result record under `results/<date>/`.
6. Compare it to the stored baseline with `compare_results.py`.

## Automated Evaluation Loop

1. Pick one supported case from `list-auto`.
2. Run `run_automated_case.py`.
3. Inspect:
   - `<case-id>.prompt.txt`
   - `<case-id>.subject.txt`
   - `<case-id>.trace.jsonl`
   - `<case-id>.grader.prompt.txt`
   - `<case-id>.grader.raw.json`
   - `<case-id>.json`
   - `workspaces/<case-id>/` when the case edited files
4. Compare `<case-id>.json` to its stored baseline with `compare_results.py`.

For specialist-positive cases, the same loop applies, but the evaluation target is narrower: the harness is checking whether one specialist stayed in-role against a frozen patch, not whether a top-level workflow orchestrated the entire task correctly.

## Negative Automation Loop

1. Pick one supported negative case from `list-auto-negative`.
2. Run `run_automated_case.py` with that negative case id.
3. Inspect:
   - `<case-id>.prompt.txt`
   - `<case-id>.subject.txt`
   - `<case-id>.trace.jsonl`
   - `<case-id>.grader.prompt.txt`
   - `<case-id>.grader.raw.json`
   - `<case-id>.json`
   - `workspaces/<case-id>/`, which is an empty disposable workspace for prompt-only false-trigger runs and a staged fixture copy for fixture-backed negative runs
4. Compare `<case-id>.json` to its stored baseline with `compare_false_trigger_results.py`.

Negative automation differs from positive automation in one important way: it is not checking whether a workflow executed well after it triggered. It is checking whether the workflow or specialist stayed out of the task, stayed clearly secondary, or wrongly overtook the task. For the fixture-backed negative specialist case, that judgment is driven by the frozen patch content itself, not just by prompt wording.

## Batch Evaluation Loop

1. Run `run_batch.py` with no positional case ids to execute every supported automated case, or pass one or more case ids to run only that subset.
   Use `--negative` to batch only the negative false-trigger cases.
   Use `--all` to batch both positive and negative cases together.
2. Inspect the one-line per-case console summary:
   - `MATCH`: no regressions or mismatches against baseline
   - `IMPROVED`: better than baseline without regressions
   - `MISMATCH`: drift from baseline that is not automatically worse
   - `REGRESSION`: worse than baseline
   - `ERROR`: the case runner or comparison step failed
   - `RECORDED`: the case ran successfully with `--no-compare`
   - `DRY-RUN`: blind prompt preview completed; subject and grader were not invoked
3. Inspect `results/<date>/batch-summary.json` or the custom `--summary-file` path for a machine-readable record of the batch:
   For negative-only runs, the default summary file is `results/<date>/batch-negative-summary.json`.
   For combined runs, the default summary file is `results/<date>/batch-all-summary.json`.
   - top-level run settings and exit code
   - `automation_scope`: `positive`, `negative`, or `all`
   - selected case ids
   - per-status counts
   - one entry per case with status, paths, runner/comparison exit codes, and `automation_kind`
4. When needed, inspect the underlying per-case artifacts:
   - `<case-id>.prompt.txt`
   - `<case-id>.subject.txt`
   - `<case-id>.trace.jsonl`
   - `<case-id>.grader.raw.json`
   - `<case-id>.json`
   - `workspaces/<case-id>/` for implementation cases

## Batch Exit Codes

`run_batch.py` uses these exit codes:

- `0`: all selected cases completed and no regressions were found
- `1`: at least one comparison reported `REGRESSION`
- `2`: invalid setup or invalid case selection before the batch started
- `3`: runtime failure while running or comparing one or more selected cases

When `--no-compare` is used, batch exit codes still report setup and runtime failures, but baseline grading is intentionally skipped.

## Baseline Comparison Rules

`compare_results.py` treats these as regressions:

- `case_id` or `workflow` mismatch
- worse `outcome` than baseline
- missing baseline `observed_subagents`
- missing baseline `observed_validation`
- new `observed_fail_signals`
- rubric fields that moved from `true` in baseline to `false` in the new result

It treats these as mismatches, not automatic regressions:

- extra `observed_subagents`
- extra `observed_validation`
- rubric drift that is different but not clearly worse

It treats these as improvements:

- better `outcome`
- removed baseline fail signals
- rubric fields that moved from `false` to `true`

## False-Trigger Comparison Rules

`compare_false_trigger_results.py` treats these as regressions:

- `case_id`, `workflow`, `expected_should_trigger`, or `fixture_ref` mismatch
- worse `outcome` than baseline
- worse `actual_trigger_behavior` than baseline:
  - `not_triggered` is best
  - `secondary_only` is acceptable but weaker
  - `partial_trigger` is a false-trigger failure
  - `primary_trigger` is the worst case
- new `unexpected_subagents`
- new `unexpected_validation`
- new `fail_signals`
- false-trigger rubric fields that moved from `true` in baseline to `false` in the new result

It treats these as improvements:

- better `outcome`
- better `actual_trigger_behavior`
- unexpected behavior tokens that were present in baseline but absent now
- false-trigger rubric fields that moved from `false` to `true`

Interpret false-trigger regressions as precision failures: the wrong workflow or specialist became too eager, overtook the user task, or emitted the wrong response shape.

For the final automated negative specialist cases, interpret regressions this way:

- `rv-implementation-request-negative`: a regression means reviewer behavior overtook an implementation task or emitted findings-first review structure where implementation help should have led.
- `sa-low-risk-ui-negative`: a regression means security-auditor behavior was inferred from a purely presentational diff and invented trust-boundary, injection, path, or secret risks unsupported by the changed surface.

## Pass/Fail Interpretation By Workflow

### `build-validate`

Pass when it selects the correct validation scope, prefers repo-native commands, reports only checks actually run, and clearly separates passed/failed/not-run/unverified.

Fail when it invents validations, skips required escalation for risky changes, or substitutes generic commands where repo-native commands are defined.

### `orchestrated-review`

Pass when it scopes the review correctly, uses `pr-explorer` first when needed, spawns only justified specialists, and synthesizes deduplicated findings-first output.

Fail when it spawns specialists indiscriminately, treats evidence gatherers as final judges, or produces a summary without a disciplined findings phase.

### `orchestrated-implementation`

Pass when it gathers only the necessary evidence, keeps implementation in the main agent, validates with `build-validate`, and only hands off to audits when the changed surface justifies them.

Fail when it delegates implementation to auditors, skips validation planning, or collapses implementation and review into one undisciplined step.

### `reviewer`

Pass when it produces findings first, prioritizes correctness/regression/compatibility, and calls out missing or weak test coverage without drifting into style noise.

Fail when it becomes implementation-oriented, focuses on nits, or omits substantive regression or compatibility risks.

### `interop-auditor`

Pass when it focuses on ownership, lifetime, allocator rules, ABI/layout, error translation, and thread-safety at cross-language boundaries.

Fail when it behaves like a generic reviewer, ignores boundary contracts, or misses obvious borrow/ownership/ABI hazards.

### `security-auditor`

Pass when it stays concrete, trust-boundary focused, and exploitability aware, with findings tied to real validation, injection, secret-handling, parsing, or native-safety risks.

Fail when it is vague, speculative without evidence, or misses obvious trust-boundary and dangerous-default issues.

For the automated specialist-positive cases, interpret regressions this way:

- `rv-regression-review-positive`: a regression means the response stopped being findings-first, drifted toward style noise or implementation planning, or lost regression/compatibility/test-coverage focus.
- `ia-ffi-boundary-positive`: a regression means the response stopped centering ownership, lifetime, ABI, allocator, error-model, or thread-safety risks at the language boundary.
- `sa-parser-subprocess-positive`: a regression means the response stopped naming concrete trust-boundary issues such as parsing risk, subprocess injection, path risk, or secret leakage.

## Pass/Fail/Regression Interpretation

- `pass`: the run satisfies the case and does not regress against baseline expectations.
- `partial`: the run is directionally useful but missed required evidence, discipline, or output shape.
- `fail`: the run violated the core contract or tripped material fail signals.
- `regression`: the comparison script found worse behavior than the stored baseline.
- `mismatch`: the run drifted from baseline without enough evidence to call it worse.
- `false-trigger pass`: the named workflow stayed out of the task, or remained clearly secondary.
- `false-trigger fail`: the named workflow or specialist overtook the task, imposed the wrong structure, or emitted explicit false-trigger fail signals.

## Auto-Runnable Cases

- `bv-api-boundary-positive`
  Reason: patch-only fixture, no file edits required, structured validation-plan output maps cleanly to the result schema.
- `or-current-diff-multi-angle-positive`
  Reason: patch-only fixture, no repo mutation required, and the findings-first orchestration summary maps cleanly to the structured result schema.
- `oi-bugfix-validate-positive`
  Reason: the implementation fixture is tiny and can be copied into a disposable workspace before the run.
- `rv-regression-review-positive`
  Reason: the frozen patch is stable, read-only, and narrow enough to evaluate reviewer findings discipline without extra orchestration machinery.
- `ia-ffi-boundary-positive`
  Reason: the frozen interop patch has explicit ownership, allocator, and threading hazards that map cleanly to stable interop-audit tokens.
- `sa-parser-subprocess-positive`
  Reason: the frozen review patch contains concrete parser, subprocess, path, and secret-handling signals that support stable security-audit regression checks.

## Auto-Runnable Negative Cases

- `bv-review-only-negative`
  Reason: crisp workflow-boundary test for validation-first hijacking on a review-only task.
- `or-single-docs-question-negative`
  Reason: narrow docs lookup that should stay out of multi-agent review orchestration.
- `oi-review-request-negative`
  Reason: direct check that implementation planning does not hijack review-only requests.
- `ia-pure-python-negative`
  Reason: specialist false-trigger check for a pure single-language task with no interop boundary.
- `rv-implementation-request-negative`
  Reason: direct specialist false-trigger check that a bug-fix request does not collapse into reviewer-first findings output.
- `sa-low-risk-ui-negative`
  Reason: fixture-backed negative specialist check where the frozen UI-only patch itself proves the security surface is low-risk, so the changed surface matters instead of prompt wording alone.

## Manual Cases

No cases in the current harness remain manual after this iteration.

## Next Iteration

After this final negative-coverage iteration, the highest-value next steps are:

1. Add one or two more fixture-backed negative cases for other specialist boundaries so false-trigger precision is tested against more than one diff family.
2. Human-calibrate the independent grader on a representative sample and add deterministic trace extractors for tool/subagent events.
3. Expand coverage to:
   - `docs-researcher`
   - `pr-explorer`
   - `structured-review-record`
   - `pr-draft-summary`
