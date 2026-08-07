#!/usr/bin/env python3
"""Focused regression tests for Codex bootstrap config handling."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import unittest.mock
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

    def require_safe_retirement(self) -> None:
        if not self.bootstrap.safe_retirement_supported():
            self.skipTest("descriptor-relative no-follow retirement is unavailable")

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

    def test_retire_tree_removes_only_owned_files_and_leaves_empty_parents(self) -> None:
        self.require_safe_retirement()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            managed = root / "evals"
            (managed / "owned").mkdir(parents=True)
            owned = managed / "owned" / "result.json"
            owned.write_text("{}\n", encoding="utf-8")
            unowned = managed / "local.json"
            unowned.write_text("local\n", encoding="utf-8")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = root / "backups"
            try:
                plan = self.bootstrap.Plan(dry_run=False)
                unresolved = self.bootstrap.retire_managed_tree(
                    managed, plan, ["owned/result.json"]
                )
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertEqual(unresolved, [])
            self.assertFalse(owned.exists())
            self.assertTrue((managed / "owned").is_dir())
            self.assertEqual(unowned.read_text(encoding="utf-8"), "local\n")
            self.assertTrue(any("result.json" in str(path) for path in plan.backup_dir.rglob("*")))

    def test_retire_tree_keeps_unsafe_and_directory_entries_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "templates"
            (root / "became-dir").mkdir(parents=True)
            plan = self.bootstrap.Plan(dry_run=False)

            unresolved = self.bootstrap.retire_managed_tree(
                root,
                plan,
                ["../outside", r"C:\outside", "became-dir"],
            )

            self.assertEqual(unresolved, ["../outside", r"C:\outside", "became-dir"])
            self.assertTrue((root / "became-dir").is_dir())

    def test_retire_tree_does_not_follow_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "evals"
            external = base / "external"
            root.mkdir()
            external.mkdir()
            protected = external / "result.json"
            protected.write_text("preserve\n", encoding="utf-8")
            try:
                (root / "linked").symlink_to(external, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            unresolved = self.bootstrap.retire_managed_tree(
                root,
                self.bootstrap.Plan(dry_run=False),
                ["linked/result.json"],
            )

            self.assertEqual(unresolved, ["linked/result.json"])
            self.assertEqual(protected.read_text(encoding="utf-8"), "preserve\n")

    def test_retire_tree_rejects_symlinked_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            external = base / "external"
            external.mkdir()
            protected = external / "result.json"
            protected.write_text("preserve\n", encoding="utf-8")
            root = base / "evals"
            try:
                root.symlink_to(external, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            unresolved = self.bootstrap.retire_managed_tree(
                root,
                self.bootstrap.Plan(dry_run=False),
                ["result.json"],
            )

            self.assertEqual(unresolved, ["result.json"])
            self.assertEqual(protected.read_text(encoding="utf-8"), "preserve\n")

    def test_retire_tree_unlinks_leaf_symlink_without_touching_target(self) -> None:
        self.require_safe_retirement()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "templates"
            root.mkdir()
            target = base / "target.md"
            target.write_text("preserve\n", encoding="utf-8")
            leaf = root / "owned.md"
            try:
                leaf.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.BACKUP_ROOT = base / "backups"
            try:
                unresolved = self.bootstrap.retire_managed_tree(
                    root,
                    self.bootstrap.Plan(dry_run=False),
                    ["owned.md"],
                )
            finally:
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertEqual(unresolved, [])
            self.assertFalse(leaf.exists())
            self.assertFalse(leaf.is_symlink())
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve\n")

    def test_retire_tree_dry_run_changes_nothing(self) -> None:
        self.require_safe_retirement()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evals"
            root.mkdir()
            owned = root / "owned.json"
            owned.write_text("{}\n", encoding="utf-8")
            plan = self.bootstrap.Plan(dry_run=True)

            self.bootstrap.retire_managed_tree(root, plan, ["owned.json"])

            self.assertTrue(owned.exists())
            self.assertTrue(any("remove stale managed path" in item for item in plan.actions))

    def test_retire_tree_backup_failure_leaves_owned_file(self) -> None:
        self.require_safe_retirement()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evals"
            root.mkdir()
            owned = root / "owned.json"
            owned.write_text("{}\n", encoding="utf-8")
            plan = self.bootstrap.Plan(dry_run=False)

            with unittest.mock.patch.object(
                self.bootstrap,
                "backup_retired_leaf",
                side_effect=OSError("backup failed"),
            ):
                unresolved = self.bootstrap.retire_managed_tree(
                    root, plan, ["owned.json"]
                )

            self.assertEqual(unresolved, ["owned.json"])
            self.assertTrue(owned.exists())

    def test_retire_tree_never_recursively_deletes_swapped_leaf(self) -> None:
        self.require_safe_retirement()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evals"
            root.mkdir()
            owned = root / "owned.json"
            owned.write_text("{}\n", encoding="utf-8")

            def swap_to_directory(*_args) -> None:
                owned.unlink()
                owned.mkdir()
                (owned / "unowned.txt").write_text("preserve\n", encoding="utf-8")

            with unittest.mock.patch.object(
                self.bootstrap,
                "backup_retired_leaf",
                side_effect=swap_to_directory,
            ):
                unresolved = self.bootstrap.retire_managed_tree(
                    root,
                    self.bootstrap.Plan(dry_run=False),
                    ["owned.json"],
                )

            self.assertEqual(unresolved, ["owned.json"])
            quarantined = next(root.glob(".agentcore-retired-*"))
            self.assertEqual((quarantined / "unowned.txt").read_text(), "preserve\n")

    def test_manifest_loader_rejects_malformed_and_symlinked_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manifest = base / "agentcore-manifest.json"
            old_manifest = self.bootstrap.MANIFEST_PATH
            self.bootstrap.MANIFEST_PATH = manifest
            try:
                manifest.write_text("not json", encoding="utf-8")
                self.assertEqual(self.bootstrap.load_install_manifest_state(), ({}, False))
                target = base / "target.json"
                target.write_text('{"schema_version": 1, "managed_trees": {}}', encoding="utf-8")
                manifest.unlink()
                try:
                    manifest.symlink_to(target)
                except OSError as exc:
                    self.skipTest(f"symlink creation is unavailable: {exc}")
                self.assertEqual(self.bootstrap.load_install_manifest_state(), ({}, False))
            finally:
                self.bootstrap.MANIFEST_PATH = old_manifest

    def test_manifest_loader_requires_schema_but_retains_unsafe_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "agentcore-manifest.json"
            old_manifest = self.bootstrap.MANIFEST_PATH
            self.bootstrap.MANIFEST_PATH = manifest
            try:
                manifest.write_text(
                    '{"schema_version": 2, "managed_trees": {}}\n',
                    encoding="utf-8",
                )
                self.assertEqual(
                    self.bootstrap.load_install_manifest_state(),
                    ({}, False),
                )

                manifest.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "managed_trees": {
                                ".codex/evals": [r"C:\\outside", "owned.json"]
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(
                    self.bootstrap.load_install_manifest_state(),
                    (
                        {".codex/evals": [r"C:\\outside", "owned.json"]},
                        True,
                    ),
                )
            finally:
                self.bootstrap.MANIFEST_PATH = old_manifest

    def test_manifest_loader_rejects_insecure_or_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "agentcore-manifest.json"
            old_manifest = self.bootstrap.MANIFEST_PATH
            self.bootstrap.MANIFEST_PATH = manifest
            try:
                manifest.write_text(
                    '{"schema_version": 1, "managed_trees": {}}\n',
                    encoding="utf-8",
                )
                manifest.chmod(0o666)
                self.assertEqual(
                    self.bootstrap.load_install_manifest_state(),
                    ({}, self.bootstrap.os.name != "posix"),
                )
                manifest.chmod(0o600)
                with unittest.mock.patch.object(self.bootstrap, "MAX_MANIFEST_BYTES", 1):
                    self.assertEqual(
                        self.bootstrap.load_install_manifest_state(),
                        ({}, False),
                    )
            finally:
                self.bootstrap.MANIFEST_PATH = old_manifest

    def test_manifest_loader_does_not_apply_posix_modes_on_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "agentcore-manifest.json"
            manifest.write_text(
                '{"schema_version": 1, "managed_trees": {}}\n',
                encoding="utf-8",
            )
            manifest.chmod(0o666)
            old_manifest = self.bootstrap.MANIFEST_PATH
            self.bootstrap.MANIFEST_PATH = manifest
            try:
                with unittest.mock.patch.object(self.bootstrap.os, "name", "nt"):
                    self.assertEqual(
                        self.bootstrap.load_install_manifest_state(),
                        ({}, True),
                    )
            finally:
                self.bootstrap.MANIFEST_PATH = old_manifest

    def test_manifest_write_replaces_symlink_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "target.json"
            target.write_text("preserve\n", encoding="utf-8")
            manifest = base / "agentcore-manifest.json"
            try:
                manifest.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            old_manifest = self.bootstrap.MANIFEST_PATH
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.MANIFEST_PATH = manifest
            self.bootstrap.BACKUP_ROOT = base / "backups"
            try:
                self.bootstrap.write_install_manifest(
                    self.bootstrap.Plan(dry_run=False), {".codex/hooks": ["guard.py"]}
                )
            finally:
                self.bootstrap.MANIFEST_PATH = old_manifest
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertFalse(manifest.is_symlink())
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve\n")
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["managed_trees"], {".codex/hooks": ["guard.py"]})

    def test_manifest_replace_failure_preserves_old_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manifest = base / "agentcore-manifest.json"
            original = '{"schema_version": 1, "managed_trees": {}}\n'
            manifest.write_text(original, encoding="utf-8")
            old_manifest = self.bootstrap.MANIFEST_PATH
            old_backup_root = self.bootstrap.BACKUP_ROOT
            self.bootstrap.MANIFEST_PATH = manifest
            self.bootstrap.BACKUP_ROOT = base / "backups"
            try:
                with unittest.mock.patch.object(self.bootstrap.os, "replace", side_effect=OSError("replace failed")):
                    with self.assertRaisesRegex(OSError, "replace failed"):
                        self.bootstrap.write_install_manifest(
                            self.bootstrap.Plan(dry_run=False), {".codex/hooks": ["guard.py"]}
                        )
            finally:
                self.bootstrap.MANIFEST_PATH = old_manifest
                self.bootstrap.BACKUP_ROOT = old_backup_root

            self.assertEqual(manifest.read_text(encoding="utf-8"), original)
            self.assertEqual(list(base.glob("tmp*")), [])

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

    def test_install_retires_owned_files_and_persists_unresolved_entries(self) -> None:
        self.require_safe_retirement()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source_codex = base / "source-codex"
            source_agents = base / "source-agents"
            live_codex = base / "live-codex"
            live_agents = base / "live-agents"
            for dirname in self.bootstrap.ACTIVE_CODEX_TREES:
                (source_codex / dirname).mkdir(parents=True)
            (source_codex / "agents" / "active.toml").write_text(
                "name = 'active'\n", encoding="utf-8"
            )
            (source_agents / "skills").mkdir(parents=True)
            retired = live_codex / "evals"
            retired.mkdir(parents=True)
            (retired / "owned.json").write_text("{}\n", encoding="utf-8")
            (retired / "unowned.json").write_text("local\n", encoding="utf-8")
            (retired / "became-directory").mkdir()
            manifest = live_codex / "agentcore-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "managed_trees": {
                            ".codex/evals": ["owned.json", "became-directory"]
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest.chmod(0o600)

            names = (
                "SRC_CODEX",
                "SRC_AGENTS",
                "LIVE_CODEX",
                "LIVE_AGENTS",
                "BACKUP_ROOT",
                "MANIFEST_PATH",
            )
            old = {name: getattr(self.bootstrap, name) for name in names}
            self.bootstrap.SRC_CODEX = source_codex
            self.bootstrap.SRC_AGENTS = source_agents
            self.bootstrap.LIVE_CODEX = live_codex
            self.bootstrap.LIVE_AGENTS = live_agents
            self.bootstrap.BACKUP_ROOT = base / "backups"
            self.bootstrap.MANIFEST_PATH = manifest
            try:
                with unittest.mock.patch.object(
                    self.bootstrap, "build_rendered_hooks_config", return_value="{}\n"
                ), unittest.mock.patch.object(
                    self.bootstrap, "build_merged_config", return_value="model = 'test'\n"
                ):
                    self.bootstrap.install(self.bootstrap.Plan(dry_run=False))
            finally:
                for name, value in old.items():
                    setattr(self.bootstrap, name, value)

            payload = json.loads(manifest.read_text(encoding="utf-8"))
            trees = payload["managed_trees"]
            self.assertFalse((retired / "owned.json").exists())
            self.assertEqual(
                (retired / "unowned.json").read_text(encoding="utf-8"), "local\n"
            )
            self.assertEqual(trees[".codex/evals"], ["became-directory"])
            self.assertEqual(trees[".codex/agents"], ["active.toml"])

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
