#!/usr/bin/env python3
"""Focused regression tests for Codex bootstrap config handling."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path, PureWindowsPath


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


class BootstrapFilesystemSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bootstrap = load_bootstrap_module()

    def test_replace_file_replaces_symlink_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("managed\n", encoding="utf-8")
            target = root / "target.txt"
            target.write_text("preserve\n", encoding="utf-8")
            destination = root / "destination.txt"
            try:
                destination.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = root / "backups"
            try:
                plan = self.bootstrap.Plan(dry_run=False)
                plan.replace_file(source, destination)
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertFalse(destination.is_symlink())
            self.assertEqual(destination.read_text(encoding="utf-8"), "managed\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve\n")

    def test_windows_hook_commands_render_an_absolute_interpreter(self) -> None:
        rendered = json.loads(self.bootstrap.build_rendered_hooks_config())
        expected = str(Path(self.bootstrap.sys.executable).resolve())
        for groups in rendered["hooks"].values():
            for group in groups:
                for hook in group["hooks"]:
                    command = hook["commandWindows"].strip('"')
                    self.assertTrue(command.startswith(expected), command)
                    self.assertNotIn("{{PYTHON_EXECUTABLE}}", command)
                    self.assertIn(expected, hook["command"])
                    self.assertNotIn("{{PYTHON_EXECUTABLE_POSIX}}", hook["command"])

    def test_windows_hook_rendering_json_escapes_windows_paths(self) -> None:
        for executable in (
            r"C:\Users\alice\python.exe",
            r"C:\Program Files\Python\python.exe",
        ):
            rendered = self.bootstrap.build_rendered_hooks_config(executable)
            config = json.loads(rendered)
            commands = [
                hook["commandWindows"]
                for groups in config["hooks"].values()
                for group in groups
                for hook in group["hooks"]
            ]
            self.assertTrue(all(executable in command for command in commands))

        posix_executable = "/opt/Python 3/bin/python3"
        rendered = json.loads(
            self.bootstrap.build_rendered_hooks_config(posix_executable)
        )
        commands = [
            hook["command"]
            for groups in rendered["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertTrue(all("'/opt/Python 3/bin/python3'" in command for command in commands))

    def test_ensure_dir_replaces_symlink_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "external"
            target.mkdir()
            destination = root / "managed"
            try:
                destination.symlink_to(target, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = root / "backups"
            try:
                plan = self.bootstrap.Plan(dry_run=False)
                plan.ensure_dir(destination)
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertFalse(destination.is_symlink())
            self.assertTrue(destination.is_dir())
            self.assertTrue(target.is_dir())

    def test_sync_tree_backs_up_and_removes_stale_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "kept.txt").write_text("new\n", encoding="utf-8")
            stale = destination / "stale.txt"
            stale.write_text("old\n", encoding="utf-8")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = root / "backups"
            try:
                plan = self.bootstrap.Plan(dry_run=False)
                installed = self.bootstrap.sync_tree_contents(
                    source, destination, plan, {"stale.txt"}
                )
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertFalse(stale.exists())
            self.assertEqual((destination / "kept.txt").read_text(), "new\n")
            self.assertEqual(installed, ["kept.txt"])
            self.assertTrue(any("stale.txt" in str(path) for path in plan.backup_dir.rglob("*")))

    def test_sync_tree_preserves_unowned_destination_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "managed.txt").write_text("managed\n", encoding="utf-8")
            unowned = destination / "external.txt"
            unowned.write_text("external\n", encoding="utf-8")
            plan = self.bootstrap.Plan(dry_run=False)

            self.bootstrap.sync_tree_contents(source, destination, plan, set())

            self.assertEqual(unowned.read_text(encoding="utf-8"), "external\n")

    def test_manifest_paths_cannot_escape_managed_root(self) -> None:
        self.assertFalse(self.bootstrap.safe_manifest_relative_path(Path("../outside")))
        self.assertFalse(self.bootstrap.safe_manifest_relative_path(Path("/outside")))
        self.assertTrue(self.bootstrap.safe_manifest_relative_path(Path("nested/file")))
        self.assertFalse(
            self.bootstrap.safe_manifest_relative_path(PureWindowsPath(r"\outside"))
        )
        self.assertFalse(
            self.bootstrap.safe_manifest_relative_path(PureWindowsPath(r"C:outside"))
        )
        self.assertFalse(
            self.bootstrap.safe_manifest_relative_path(PureWindowsPath(r"C:\outside"))
        )

    def test_stale_manifest_entry_does_not_follow_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            external = root / "external"
            source.mkdir()
            destination.mkdir()
            external.mkdir()
            protected = external / "protected.txt"
            protected.write_text("preserve\n", encoding="utf-8")
            try:
                (destination / "old-dir").symlink_to(external, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            plan = self.bootstrap.Plan(dry_run=False)

            self.bootstrap.sync_tree_contents(
                source, destination, plan, {"old-dir/protected.txt"}
            )

            self.assertEqual(protected.read_text(encoding="utf-8"), "preserve\n")
            self.assertTrue(
                any(
                    "through symlinked directory" in item or "outside root" in item
                    for item in plan.actions
                )
            )

    def test_sync_tree_handles_directory_to_file_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            destination.mkdir()
            (source / "node").write_text("new file\n", encoding="utf-8")
            old_dir = destination / "node"
            old_dir.mkdir()
            (old_dir / "old.txt").write_text("old\n", encoding="utf-8")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = root / "backups"
            try:
                plan = self.bootstrap.Plan(dry_run=False)
                self.bootstrap.sync_tree_contents(
                    source, destination, plan, {"node/old.txt"}
                )
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertTrue((destination / "node").is_file())
            self.assertEqual((destination / "node").read_text(), "new file\n")

    def test_sync_tree_handles_file_to_directory_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            destination = root / "destination"
            (source / "node").mkdir(parents=True)
            (source / "node" / "new.txt").write_text("new\n", encoding="utf-8")
            destination.mkdir()
            (destination / "node").write_text("old file\n", encoding="utf-8")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = root / "backups"
            try:
                plan = self.bootstrap.Plan(dry_run=False)
                self.bootstrap.sync_tree_contents(source, destination, plan, {"node"})
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertTrue((destination / "node").is_dir())
            self.assertEqual((destination / "node" / "new.txt").read_text(), "new\n")

    def test_profile_manifest_entry_must_be_single_config_basename(self) -> None:
        self.assertTrue(self.bootstrap.safe_profile_manifest_name("edit.config.toml"))
        self.assertFalse(
            self.bootstrap.safe_profile_manifest_name("linked/outside.config.toml")
        )
        self.assertFalse(self.bootstrap.safe_profile_manifest_name("../outside.config.toml"))
        self.assertFalse(self.bootstrap.safe_profile_manifest_name("notes.toml"))


if __name__ == "__main__":
    unittest.main()
