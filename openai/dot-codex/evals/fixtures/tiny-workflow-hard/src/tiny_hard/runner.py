"""Run sync jobs from parsed job specs."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from subprocess import CompletedProcess
from typing import Any

from tiny_hard.parser import parse_job_spec

LOGGER = logging.getLogger(__name__)
Runner = Callable[..., CompletedProcess[str]]


def build_sync_command(job: dict[str, str], token: str) -> str:
    return (
        f"sync-tool --name {job['name']} --path {job['path']} "
        f"--mode {job['mode']} --token {token}"
    )


def run_sync_job(
    spec_line: str,
    token: str,
    *,
    runner: Runner = subprocess.run,
) -> CompletedProcess[str]:
    job = parse_job_spec(spec_line)
    command = build_sync_command(job, token)
    LOGGER.info("running sync job=%s token=%s", job["name"], token)
    return runner(command, shell=True, check=True, capture_output=True, text=True)
