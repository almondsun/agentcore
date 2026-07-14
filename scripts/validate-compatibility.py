#!/usr/bin/env python3
"""Validate checked-in Codex compatibility metadata against the base config."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "openai" / "dot-codex" / "compatibility.json"
CONFIG = ROOT / "openai" / "dot-codex" / "config.toml"
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def version_tuple(value: str) -> tuple[int, int, int]:
    if not VERSION_RE.fullmatch(value):
        raise ValueError(f"invalid semantic version: {value!r}")
    major, minor, patch = (int(part) for part in value.split("."))
    return major, minor, patch


def main() -> int:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "minimum_codex_cli",
        "tested_codex_cli",
        "default_model",
        "verified_at",
    }
    missing = sorted(required - metadata.keys())
    if missing:
        raise ValueError(f"compatibility metadata missing fields: {', '.join(missing)}")
    if metadata["schema_version"] != 1:
        raise ValueError("unsupported compatibility schema_version")
    minimum = version_tuple(metadata["minimum_codex_cli"])
    tested = version_tuple(metadata["tested_codex_cli"])
    if tested < minimum:
        raise ValueError("tested_codex_cli must be at least minimum_codex_cli")
    verified_at = metadata["verified_at"]
    if not isinstance(verified_at, str) or date.fromisoformat(verified_at).isoformat() != verified_at:
        raise ValueError("verified_at must be an ISO date in YYYY-MM-DD format")
    if metadata["default_model"] != config.get("model"):
        raise ValueError(
            "compatibility default_model does not match config.toml model: "
            f"{metadata['default_model']!r} != {config.get('model')!r}"
        )
    print("compatibility metadata matches config.toml")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"compatibility validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
