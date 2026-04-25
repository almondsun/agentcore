# lab

`lab` is the durable workspace for Codex evaluation, tuning, and real-task verification.

Use this directory for:

- small eval harnesses and case notes
- real task sandboxes used to judge Codex on actual work
- scorecards, run outputs, and result summaries
- tuning notes and operational lessons
- snapshots or artifacts worth keeping beyond a disposable session

Do not use this directory as a generic scratch space.
Keep disposable experiments in external scratch space.

## Structure

- `evals/`: local test cases, harness helpers, scorecards, and comparison artifacts specific to your own tuning work.
- `live_tasks/`: real or realistic repo sandboxes used to test Codex on meaningful engineering tasks.
- `notes/`: conclusions, tuning notes, failure taxonomies, and operating decisions.
- `results/`: saved outputs from runs you want to keep, including summaries and exported artifacts.
- `snapshots/`: prompts, transcripts, reference outputs, or other preserved evidence worth keeping.

## Operating pattern

Use this repeatable loop for future work:

1. Start outside this repository for disposable exploration, scratch repos, and one-off experiments.
2. Promote a task into `lab` only when it is durable enough to rerun, compare, or reference later.
3. Keep the active repo or sandbox in `live_tasks/` or `evals/`, never in `results/` or `snapshots/`.
4. Save durable outputs in `results/`, preserve important prompt/response evidence in `snapshots/`, and record only durable lessons or decisions in `notes/`.
5. When a task stops being scratch and starts affecting future evaluation practice, move the smallest useful artifact set into `lab`.

Directory boundaries:

- `live_tasks/`: the repo or sandbox itself. Keep source, tests, task framing, and any small task-local docs that explain why it exists.
- `results/`: outputs produced from running evals or tasks that you want to compare later, such as summaries, scorecards, exported JSON, and preserved run bundles.
- `snapshots/`: prompts, final responses, transcripts, or validation excerpts worth preserving as evidence for an important run.
- `notes/`: decisions, repeated failure modes, tuning conclusions, and workflow changes you expect to use again.

Promotion rule:

- promote from external scratch space when the artifact is representative, reusable, or evidence-bearing
- keep it out of this repository when it is just setup churn, temporary debugging, or something you would not reopen later
- if you are preserving a real task, preserve the repo in `live_tasks/`, not a zip or result dump in `results/`
- if you are preserving a run, keep the output in `results/` and the prompt/response evidence in `snapshots/`
- if you learned something that changes future behavior, write it down once in `notes/` instead of burying it in a result bundle

Lightweight rule of thumb:

- `live_tasks` holds the thing you run
- `results` holds what the run produced
- `snapshots` holds what Codex and the operator said or saw
- `notes` holds what you want to remember next time
