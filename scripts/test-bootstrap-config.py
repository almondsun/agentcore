#!/usr/bin/env python3
"""Focused regression tests for Codex bootstrap config handling."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = REPO_ROOT / "scripts" / "bootstrap_codex_environment.py"


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("bootstrap_codex_environment", BOOTSTRAP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load bootstrap module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PermissionProfileValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bootstrap = load_bootstrap_module()

    def test_missing_literal_workspace_read_grant_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text(
                """
[permissions.agentcore_workspace]
extends = ":workspace"

[permissions.agentcore_workspace.filesystem.":workspace_roots"]
"missing-dir" = "read"
"**/*.pem" = "deny"
""".lstrip(),
                encoding="utf-8",
            )
            old_root = self.bootstrap.REPO_ROOT
            self.bootstrap.REPO_ROOT = root
            try:
                failures = self.bootstrap.validate_portable_permission_profile(config)
            finally:
                self.bootstrap.REPO_ROOT = old_root

        self.assertEqual(
            failures,
            [f"{config}: workspace-root read grant points at missing path: missing-dir"],
        )

    def test_existing_literal_workspace_read_grant_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "present-dir").mkdir()
            config = root / "config.toml"
            config.write_text(
                """
[permissions.agentcore_workspace]
extends = ":workspace"

[permissions.agentcore_workspace.filesystem.":workspace_roots"]
"present-dir" = "read"
""".lstrip(),
                encoding="utf-8",
            )
            old_root = self.bootstrap.REPO_ROOT
            self.bootstrap.REPO_ROOT = root
            try:
                failures = self.bootstrap.validate_portable_permission_profile(config)
            finally:
                self.bootstrap.REPO_ROOT = old_root

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
