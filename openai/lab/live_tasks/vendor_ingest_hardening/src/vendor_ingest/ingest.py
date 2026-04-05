"""Ingest ZIP bundles from external vendors."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from subprocess import CompletedProcess
from typing import Any

LOGGER = logging.getLogger(__name__)
Runner = Callable[..., CompletedProcess[str]]
SCAN_TOKEN_ENV_VAR = "VENDOR_SCAN_API_TOKEN"
WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _sanitize_for_log(value: str) -> str:
    return "".join(char if char.isprintable() and char not in "\r\n\t" else "_" for char in value)


def _resolve_member_target(staging_dir: Path, member_name: str) -> Path:
    if WINDOWS_DRIVE_PATH_RE.match(member_name) or PureWindowsPath(member_name).is_absolute():
        msg = f"absolute ZIP member path is not allowed: {_sanitize_for_log(member_name)}"
        raise ValueError(msg)

    normalized_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized_name)
    if member_path.is_absolute():
        msg = f"absolute ZIP member path is not allowed: {_sanitize_for_log(member_name)}"
        raise ValueError(msg)
    if ".." in member_path.parts:
        msg = f"ZIP member escapes staging directory: {_sanitize_for_log(member_name)}"
        raise ValueError(msg)

    staging_root = staging_dir.resolve()
    target = (staging_root / member_path.as_posix()).resolve()
    try:
        target.relative_to(staging_root)
    except ValueError as exc:
        msg = f"ZIP member escapes staging directory: {_sanitize_for_log(member_name)}"
        raise ValueError(msg) from exc
    return target


def extract_vendor_bundle(bundle_zip: Path, staging_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    with zipfile.ZipFile(bundle_zip) as archive:
        for member in archive.infolist():
            target = _resolve_member_target(staging_dir, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
            extracted.append(target)
    return extracted


def build_scan_command(bundle_id: str, staging_dir: Path, api_token: str) -> list[str]:
    del api_token
    return [
        "vendor-scan",
        "--bundle",
        bundle_id,
        "--staging-dir",
        str(staging_dir),
    ]


def scan_staged_bundle(
    bundle_id: str,
    staging_dir: Path,
    api_token: str,
    *,
    runner: Runner = subprocess.run,
) -> CompletedProcess[str]:
    command = build_scan_command(bundle_id, staging_dir, api_token)
    safe_bundle_id = _sanitize_for_log(bundle_id)
    env = os.environ.copy()
    env[SCAN_TOKEN_ENV_VAR] = api_token
    LOGGER.info("running vendor scan bundle=%s", safe_bundle_id)
    return runner(command, shell=False, check=True, capture_output=True, text=True, env=env)


def emit_ingest_summary(bundle_id: str, extracted: list[Path], api_token: str) -> str:
    del api_token
    safe_bundle_id = _sanitize_for_log(bundle_id)
    joined = ", ".join(_sanitize_for_log(path.name) for path in extracted)
    return f"bundle={safe_bundle_id} extracted=[{joined}]"
