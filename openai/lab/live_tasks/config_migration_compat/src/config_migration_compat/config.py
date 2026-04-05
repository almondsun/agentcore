"""Load job dispatch configuration from JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JobConfig:
    """Job configuration used by the dispatcher."""

    job_name: str
    source: str
    retries: int
    timeout_seconds: int
    retry_backoff_seconds: int = 0


def _require_str(data: dict[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_int(data: dict[str, Any], field_name: str, *, minimum: int) -> int:
    value = data.get(field_name)
    if type(value) is not int or value < minimum:
        raise ValueError(f"{field_name} must be an integer >= {minimum}")
    return value


def _load_retry_settings(data: dict[str, Any]) -> tuple[int, int]:
    legacy_retries = data.get("retries")
    retry_policy = data.get("retry_policy")

    if retry_policy is None:
        return _require_int(data, "retries", minimum=0), 0

    if not isinstance(retry_policy, dict):
        raise ValueError("retry_policy must be an object")

    max_attempts = _require_int(retry_policy, "max_attempts", minimum=0)
    backoff_seconds = _require_int(retry_policy, "backoff_seconds", minimum=0)

    if legacy_retries is None:
        return max_attempts, backoff_seconds

    if type(legacy_retries) is not int or legacy_retries < 0:
        raise ValueError("retries must be an integer >= 0")

    if legacy_retries != max_attempts:
        raise ValueError("retries conflicts with retry_policy.max_attempts")

    return max_attempts, backoff_seconds


def load_job_config(path: Path) -> JobConfig:
    """Load the current config shape from disk."""

    data = json.loads(path.read_text())
    retries, retry_backoff_seconds = _load_retry_settings(data)
    return JobConfig(
        job_name=_require_str(data, "job_name"),
        source=_require_str(data, "source"),
        retries=retries,
        timeout_seconds=_require_int(data, "timeout_seconds", minimum=1),
        retry_backoff_seconds=retry_backoff_seconds,
    )
