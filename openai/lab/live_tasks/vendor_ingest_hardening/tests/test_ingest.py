from __future__ import annotations

import zipfile
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

from vendor_ingest.ingest import (
    SCAN_TOKEN_ENV_VAR,
    emit_ingest_summary,
    extract_vendor_bundle,
    scan_staged_bundle,
)


def _write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_extract_vendor_bundle_writes_nested_files(tmp_path: Path) -> None:
    bundle = tmp_path / "vendor.zip"
    staging = tmp_path / "staging"
    _write_zip(bundle, {"reports/output.csv": "ok"})

    extracted = extract_vendor_bundle(bundle, staging)

    assert [path.relative_to(staging).as_posix() for path in extracted] == [
        "reports/output.csv"
    ]
    assert (staging / "reports" / "output.csv").read_text() == "ok"


def test_extract_vendor_bundle_rejects_path_traversal(tmp_path: Path) -> None:
    bundle = tmp_path / "vendor.zip"
    staging = tmp_path / "staging"
    _write_zip(bundle, {"../escape.txt": "nope"})

    with pytest.raises(ValueError, match="escapes staging directory"):
        extract_vendor_bundle(bundle, staging)


def test_extract_vendor_bundle_rejects_absolute_path(tmp_path: Path) -> None:
    bundle = tmp_path / "vendor.zip"
    staging = tmp_path / "staging"
    _write_zip(bundle, {"/etc/passwd": "nope"})

    with pytest.raises(ValueError, match="absolute ZIP member path"):
        extract_vendor_bundle(bundle, staging)


@pytest.mark.parametrize("member_name", ["C:/windows/system32/drivers/etc/hosts", r"C:\windows\system32\drivers\etc\hosts"])
def test_extract_vendor_bundle_rejects_windows_drive_absolute_path(
    tmp_path: Path,
    member_name: str,
) -> None:
    bundle = tmp_path / "vendor.zip"
    staging = tmp_path / "staging"
    _write_zip(bundle, {member_name: "nope"})

    with pytest.raises(ValueError, match="absolute ZIP member path"):
        extract_vendor_bundle(bundle, staging)


def test_scan_staged_bundle_invokes_runner() -> None:
    captured: dict[str, Any] = {}

    def fake_runner(command: list[str], **kwargs: Any) -> CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return CompletedProcess(args=command, returncode=0, stdout="ok", stderr="")

    result = scan_staged_bundle(
        "nightly-drop\nforged",
        Path("/tmp/staging"),
        "secret-token",
        runner=fake_runner,
    )

    assert result.returncode == 0
    assert captured["command"] == [
        "vendor-scan",
        "--bundle",
        "nightly-drop\nforged",
        "--staging-dir",
        "/tmp/staging",
    ]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["env"][SCAN_TOKEN_ENV_VAR] == "secret-token"


def test_emit_ingest_summary_redacts_token_and_sanitizes_values() -> None:
    summary = emit_ingest_summary(
        "bundle-42\nforged",
        [Path("report.csv"), Path("evil\nname.txt")],
        "secret-token",
    )

    assert summary == "bundle=bundle-42_forged extracted=[report.csv, evil_name.txt]"
    assert "secret-token" not in summary
