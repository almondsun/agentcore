"""Build worker-facing dispatch payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import JobConfig, load_job_config


def build_dispatch_payload(config: JobConfig) -> dict[str, Any]:
    """Build the JSON payload expected by the downstream worker."""

    return {
        "job_name": config.job_name,
        "retry_count": config.retries,
        "source": config.source,
        "timeout_seconds": config.timeout_seconds,
    }


def render_dispatch_plan(config_path: Path) -> str:
    """Render a stable JSON preview for operators."""

    payload = build_dispatch_payload(load_job_config(config_path))
    return json.dumps(payload, sort_keys=True)
