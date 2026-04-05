from __future__ import annotations

import json
from pathlib import Path

import pytest

from config_migration_compat.cli import main
from config_migration_compat.config import JobConfig, load_job_config
from config_migration_compat.planner import (
    build_dispatch_payload,
    render_dispatch_plan,
)


def _write_config(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data))


def test_load_job_config_reads_legacy_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retries": 3,
            "timeout_seconds": 30,
        },
    )

    config = load_job_config(config_path)

    assert config == JobConfig(
        job_name="nightly-export",
        source="warehouse",
        retries=3,
        timeout_seconds=30,
        retry_backoff_seconds=0,
    )


def test_load_job_config_requires_retry_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "timeout_seconds": 30,
        },
    )

    with pytest.raises(ValueError, match="retries"):
        load_job_config(config_path)


def test_build_dispatch_payload_preserves_worker_field_name() -> None:
    payload = build_dispatch_payload(
        JobConfig(
            job_name="nightly-export",
            source="warehouse",
            retries=3,
            timeout_seconds=30,
            retry_backoff_seconds=5,
        )
    )

    assert payload == {
        "job_name": "nightly-export",
        "retry_count": 3,
        "source": "warehouse",
        "timeout_seconds": 30,
    }


def test_load_job_config_reads_new_retry_policy_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retry_policy": {
                "max_attempts": 4,
                "backoff_seconds": 15,
            },
            "timeout_seconds": 30,
        },
    )

    config = load_job_config(config_path)

    assert config == JobConfig(
        job_name="nightly-export",
        source="warehouse",
        retries=4,
        timeout_seconds=30,
        retry_backoff_seconds=15,
    )


def test_load_job_config_accepts_matching_legacy_and_new_retry_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retries": 3,
            "retry_policy": {
                "max_attempts": 3,
                "backoff_seconds": 10,
            },
            "timeout_seconds": 30,
        },
    )

    config = load_job_config(config_path)

    assert config == JobConfig(
        job_name="nightly-export",
        source="warehouse",
        retries=3,
        timeout_seconds=30,
        retry_backoff_seconds=10,
    )


def test_load_job_config_rejects_conflicting_legacy_and_new_retry_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retries": 2,
            "retry_policy": {
                "max_attempts": 3,
                "backoff_seconds": 10,
            },
            "timeout_seconds": 30,
        },
    )

    with pytest.raises(ValueError, match="conflicts with retry_policy.max_attempts"):
        load_job_config(config_path)


def test_render_dispatch_plan_keeps_worker_payload_contract_for_new_config_shape(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retry_policy": {
                "max_attempts": 4,
                "backoff_seconds": 15,
            },
            "timeout_seconds": 30,
        },
    )

    rendered = render_dispatch_plan(config_path)

    assert (
        rendered
        == '{"job_name": "nightly-export", "retry_count": 4, "source": "warehouse", "timeout_seconds": 30}'
    )


def test_render_dispatch_plan_returns_stable_json(tmp_path: Path) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retries": 3,
            "timeout_seconds": 30,
        },
    )

    rendered = render_dispatch_plan(config_path)

    assert (
        rendered
        == '{"job_name": "nightly-export", "retry_count": 3, "source": "warehouse", "timeout_seconds": 30}'
    )


def test_cli_main_writes_plan_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retries": 3,
            "timeout_seconds": 30,
        },
    )

    exit_code = main([str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        captured.out.strip()
        == '{"job_name": "nightly-export", "retry_count": 3, "source": "warehouse", "timeout_seconds": 30}'
    )


def test_cli_main_preserves_output_contract_for_new_config_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "job.json"
    _write_config(
        config_path,
        {
            "job_name": "nightly-export",
            "source": "warehouse",
            "retry_policy": {
                "max_attempts": 4,
                "backoff_seconds": 15,
            },
            "timeout_seconds": 30,
        },
    )

    exit_code = main([str(config_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        captured.out.strip()
        == '{"job_name": "nightly-export", "retry_count": 4, "source": "warehouse", "timeout_seconds": 30}'
    )
