# AGENTS.md

## Purpose

This workspace is for Codex evaluation, tuning, and real-task verification.

Optimize for:

1. clear separation between synthetic evals and real task repos
2. preserved evidence of behavior, not vague recollection
3. honest scoring and explicit uncertainty
4. reproducible validation paths
5. durable notes over throwaway scratch output

## Local structure

Use these boundaries:

- `evals/`: local evaluation assets and scorecards
- `live_tasks/`: self-contained task repos or sandboxes used to test Codex on real work
- `notes/`: conclusions, tuning notes, repeated failure modes, and operating decisions
- `results/`: saved run outputs, summaries, exported JSON, and scorecards
- `snapshots/`: prompts, transcripts, and preserved artifacts worth keeping

Do not mix active task repos with result dumps.
Do not use this workspace as a generic scratch directory.

## Working rules

- keep one clear purpose per subdirectory
- prefer adding short README notes when a task or result would be unclear later
- when a live task is security-sensitive or contract-sensitive, preserve the final prompt, final response, and validation evidence
- when scoring Codex, distinguish real behavior failures from environment or harness noise
- when a result is worth keeping, move it out of disposable locations and into this workspace
- for Python validation in durable repos kept under `live_tasks/` or `evals/`, default to non-bytecode-writing invocation forms when practical, usually `python3 -B ...` for repo-native validation commands
- examples of the expected default in those durable repos include `python3 -B -m unittest ...`, `python3 -B -m pytest ...`, and `python3 -B tests/contracts/validate_contract_artifacts.py`
- treat plain `python3 ...` validation in those durable repos as the exception, not the norm, and only use it when there is a concrete repo-specific reason
- if Python validation in those durable repos still creates transient runtime artifacts such as `__pycache__/` directories or `.pyc` files, remove them before final closeout
- treat this hygiene rule as specific to durable `lab` repos, not to disposable scratch work outside this repository

## Definition of done for this workspace

A new asset belongs here only if it is durable enough to matter later:

- a reusable eval
- a representative live-task sandbox
- a scorecard or comparison worth referencing
- a note that changes future operating decisions

Temporary experiments still belong outside this repository.
