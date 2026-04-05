from __future__ import annotations

from subprocess import CompletedProcess
from typing import Any

from tiny_hard.parser import parse_job_spec
from tiny_hard.runner import run_sync_job


def test_parse_job_spec_accepts_basic_spec() -> None:
    assert parse_job_spec("name=nightly; path=exports/report.csv; mode=push") == {
        "name": "nightly",
        "path": "exports/report.csv",
        "mode": "push",
    }


def test_run_sync_job_invokes_runner() -> None:
    captured: dict[str, Any] = {}

    def fake_runner(command: str, **kwargs: Any) -> CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    result = run_sync_job(
        "name=nightly; path=exports/report.csv; mode=push",
        "secret-token",
        runner=fake_runner,
    )

    assert result.returncode == 0
    assert "sync-tool" in captured["command"]
    assert captured["kwargs"]["shell"] is True
