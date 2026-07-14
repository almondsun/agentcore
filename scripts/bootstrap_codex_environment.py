#!/usr/bin/env python3
"""Install the portable agentcore Codex baseline into the current user home.

This script is intentionally stdlib-only. It treats this repository as the
portable source of truth, then generates machine-local Codex config entries for
the current home directory, current repo checkout, and Codex runtime path.
"""

from __future__ import annotations

import argparse
import filecmp
import fnmatch
import json
import os
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback.
    tomllib = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_CODEX = REPO_ROOT / "openai" / "dot-codex"
SRC_AGENTS = REPO_ROOT / "openai" / "dot-agents"
HOME = Path.home()
LIVE_CODEX = HOME / ".codex"
LIVE_AGENTS = HOME / ".agents"
BACKUP_ROOT = HOME / ".codex-agentcore-backups"
MANIFEST_PATH = LIVE_CODEX / "agentcore-manifest.json"

SKIP_NAMES = {
    ".git",
    ".codex",
    ".tmp",
    "tmp",
    "cache",
    "logs",
    "log",
    "sessions",
    "shell_snapshots",
    "memories",
    "__pycache__",
    ".venv",
    "venv",
}

SKIP_PATTERNS = {
    "*.pyc",
    "*.pyo",
    "*.sqlite",
    "*.sqlite-shm",
    "*.sqlite-wal",
    "auth.json",
    "history.jsonl",
    "models_cache.json",
    ".personality_migration",
}

CONFIG_LOCAL_TABLE_PREFIXES = (
    "hooks.state.",
    "projects.",
    "plugins.",
)

CONFIG_LOCAL_TABLES = {
    "hooks.state",
    "shell_environment_policy.set",
    "tui.model_availability_nux",
}

CONFIG_LOCAL_TOP_LEVEL_KEYS = {
    "file_opener",
}

AGENTCORE_PERMISSION_PROFILE = "agentcore_workspace"
AGENTCORE_PERMISSION_TABLE = f"permissions.{AGENTCORE_PERMISSION_PROFILE}"
PROFILE_CONFIG_GLOB = "*.config.toml"
ACTIVE_CODEX_TREES = ("agents", "rules", "hooks")
RETIRED_CODEX_TREES = ("templates", "evals")
MAX_MANIFEST_BYTES = 1024 * 1024


class Plan:
    """Collects actions and applies them unless running in dry-run mode."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.backup_dir = BACKUP_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.actions: list[str] = []
        self.backed_up: list[Path] = []

    def note(self, message: str) -> None:
        self.actions.append(message)

    def ensure_dir(self, path: Path, mode: int | None = None) -> None:
        self.note(f"ensure directory {path}")
        collision = path.is_symlink() or (path.exists() and not path.is_dir())
        if collision:
            self.backup(path)
            self.note(f"replace non-directory path {path}")
        if self.dry_run:
            return
        if collision:
            path.unlink()
        path.mkdir(parents=True, exist_ok=True)
        if mode is not None:
            chmod_best_effort(path, mode)

    def backup(self, path: Path) -> None:
        if not path.exists() and not path.is_symlink():
            return
        rel = relative_backup_path(path)
        target = self.backup_dir / rel
        self.note(f"backup {path} -> {target}")
        if self.dry_run:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir() and not path.is_symlink():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(path, target, symlinks=True)
        else:
            shutil.copy2(path, target, follow_symlinks=False)
        self.backed_up.append(path)

    def replace_file(self, src: Path, dst: Path, mode: int | None = None) -> None:
        if not dst.is_symlink() and dst.exists() and files_equal(src, dst):
            self.note(f"unchanged file {dst}")
            return
        self.backup(dst)
        self.note(f"copy file {src} -> {dst}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        elif dst.is_symlink():
            dst.unlink()
        with tempfile.NamedTemporaryFile(dir=str(dst.parent), delete=False) as handle:
            tmp_name = handle.name
        try:
            shutil.copy2(src, tmp_name)
            os.replace(tmp_name, dst)
        finally:
            Path(tmp_name).unlink(missing_ok=True)
        if mode is not None:
            chmod_best_effort(dst, mode)

    def remove_path(self, path: Path) -> None:
        if not path.exists() and not path.is_symlink():
            return
        self.backup(path)
        self.note(f"remove stale managed path {path}")
        if self.dry_run:
            return
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    def write_text_atomic(self, dst: Path, content: str, mode: int | None = None) -> None:
        current = dst.read_text(encoding="utf-8") if dst.exists() else None
        if current == content:
            self.note(f"unchanged file {dst}")
            return
        self.backup(dst)
        self.note(f"write file {dst}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(dst.parent), delete=False
        ) as handle:
            handle.write(content)
            tmp_name = handle.name
        os.replace(tmp_name, dst)
        if mode is not None:
            chmod_best_effort(dst, mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned actions and run validation without writing files",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate repository and live Codex files without installing",
    )
    args = parser.parse_args()

    if not SRC_CODEX.exists() or not SRC_AGENTS.exists():
        print("agentcore mirror directories are missing", file=sys.stderr)
        return 2

    plan = Plan(dry_run=args.dry_run or args.validate_only)

    if not args.validate_only:
        install(plan)

    failures = validate()
    for action in plan.actions:
        print(action)
    if plan.backed_up:
        print(f"backup directory: {plan.backup_dir}")
    elif not plan.dry_run:
        print("backup directory: not needed")

    if failures:
        print("validation failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("validation passed")
    return 0


def install(plan: Plan) -> None:
    plan.ensure_dir(LIVE_CODEX, 0o700)
    plan.ensure_dir(LIVE_AGENTS, 0o700)
    plan.ensure_dir(BACKUP_ROOT, 0o700)
    plan.ensure_dir(LIVE_CODEX / "tmp", 0o700)

    previous_manifest, manifest_trusted = load_install_manifest_state()
    installed_trees: dict[str, list[str]] = {}
    for dirname in ACTIVE_CODEX_TREES:
        key = f".codex/{dirname}"
        installed_trees[key] = sync_tree_contents(
            SRC_CODEX / dirname,
            LIVE_CODEX / dirname,
            plan,
            set(previous_manifest.get(key, [])),
        )
    if manifest_trusted:
        for dirname in RETIRED_CODEX_TREES:
            key = f".codex/{dirname}"
            unresolved = retire_managed_tree(
                LIVE_CODEX / dirname,
                plan,
                previous_manifest.get(key, []),
            )
            if unresolved:
                installed_trees[key] = unresolved

    for name in ("AGENTS.md", "README.md"):
        src = SRC_CODEX / name
        if src.exists():
            plan.replace_file(src, LIVE_CODEX / name)

    plan.write_text_atomic(LIVE_CODEX / "hooks.json", build_rendered_hooks_config())

    for src in sorted(SRC_CODEX.glob(PROFILE_CONFIG_GLOB)):
        plan.replace_file(src, LIVE_CODEX / src.name, 0o600)
    profile_key = ".codex/profiles"
    profile_names = {src.name for src in SRC_CODEX.glob(PROFILE_CONFIG_GLOB)}
    for stale_name in sorted(set(previous_manifest.get(profile_key, [])) - profile_names):
        rel = Path(stale_name)
        if not safe_profile_manifest_name(stale_name):
            plan.note(f"skip invalid stale managed profile entry {stale_name}")
            continue
        stale_path = contained_manifest_path(LIVE_CODEX, rel)
        if stale_path is None or path_has_symlink_ancestor(LIVE_CODEX, rel):
            plan.note(f"skip stale managed profile outside root {LIVE_CODEX / rel}")
        elif stale_path.is_dir() and not stale_path.is_symlink():
            plan.note(f"skip stale managed profile that became a directory {stale_path}")
        else:
            plan.remove_path(stale_path)
    installed_trees[profile_key] = sorted(profile_names)

    skills_key = ".agents/skills"
    installed_trees[skills_key] = sync_tree_contents(
        SRC_AGENTS / "skills",
        LIVE_AGENTS / "skills",
        plan,
        set(previous_manifest.get(skills_key, [])),
    )
    agents_readme = SRC_AGENTS / "README.md"
    if agents_readme.exists():
        plan.replace_file(agents_readme, LIVE_AGENTS / "README.md")

    merged_config = build_merged_config()
    plan.write_text_atomic(LIVE_CODEX / "config.toml", merged_config, 0o600)
    write_install_manifest(plan, installed_trees)


def sync_tree_contents(
    src_dir: Path,
    dst_dir: Path,
    plan: Plan,
    previously_managed: set[str] | None = None,
) -> list[str]:
    if not src_dir.exists():
        return []
    plan.ensure_dir(dst_dir)
    source_files = {
        str(src.relative_to(src_dir))
        for src in src_dir.rglob("*")
        if src.is_file() and not should_skip(src.relative_to(src_dir))
    }
    for rel_text in sorted(previously_managed or set()):
        rel = Path(rel_text)
        if not safe_manifest_relative_path(rel) or rel_text in source_files:
            continue
        candidate = contained_manifest_path(dst_dir, rel)
        if candidate is None:
            plan.note(f"skip stale managed path outside root {dst_dir / rel}")
            continue
        if path_has_symlink_ancestor(dst_dir, rel):
            plan.note(f"skip stale managed path through symlinked directory {dst_dir / rel}")
            continue
        if candidate.is_dir() and not candidate.is_symlink():
            plan.note(f"skip stale managed file that became a directory {candidate}")
            continue
        plan.remove_path(candidate)
    for src in sorted(src_dir.rglob("*")):
        rel = src.relative_to(src_dir)
        if should_skip(rel):
            continue
        dst = dst_dir / rel
        if src.is_dir():
            plan.ensure_dir(dst)
        elif src.is_file():
            plan.replace_file(src, dst)
    return sorted(source_files)


def retire_managed_tree(
    root: Path,
    plan: Plan,
    previously_managed: list[str],
) -> list[str]:
    """Retire manifest-owned files without governing unowned sibling content."""

    unresolved: list[str] = []
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        plan.note(f"skip retired managed tree with unsafe root {root}")
        return list(previously_managed)
    if not safe_retirement_supported():
        plan.note(f"skip retired managed tree without safe unlink support {root}")
        return list(previously_managed)

    for rel_text in previously_managed:
        rel = Path(rel_text)
        if not safe_manifest_relative_path(rel):
            plan.note(f"skip invalid retired managed path {rel_text}")
            unresolved.append(rel_text)
            continue
        candidate = contained_manifest_leaf_path(root, rel)
        if candidate is None or path_has_symlink_ancestor(root, rel):
            plan.note(f"skip retired managed path through unsafe parent {root / rel}")
            unresolved.append(rel_text)
            continue
        if not candidate.exists() and not candidate.is_symlink():
            continue
        if candidate.is_dir() and not candidate.is_symlink():
            plan.note(f"skip retired managed file that became a directory {candidate}")
            unresolved.append(rel_text)
            continue

        if not retire_managed_leaf(root, rel, candidate, plan):
            unresolved.append(rel_text)

    return unresolved


def safe_retirement_supported() -> bool:
    return bool(
        getattr(os, "O_DIRECTORY", 0)
        and getattr(os, "O_NOFOLLOW", 0)
        and os.open in os.supports_dir_fd
        and os.readlink in os.supports_dir_fd
        and os.rename in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def retire_managed_leaf(root: Path, rel: Path, candidate: Path, plan: Plan) -> bool:
    """Back up and unlink one pinned, non-directory leaf without following links."""

    target = plan.backup_dir / relative_backup_path(candidate)
    plan.note(f"backup {candidate} -> {target}")
    plan.note(f"remove stale managed path {candidate}")
    if plan.dry_run:
        return True

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    opened: list[int] = []
    try:
        parent_fd = os.open(root, flags)
        opened.append(parent_fd)
        for part in rel.parts[:-1]:
            parent_fd = os.open(part, flags, dir_fd=parent_fd)
            opened.append(parent_fd)

        leaf = rel.parts[-1]
        initial = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISDIR(initial.st_mode) or not (
            stat.S_ISREG(initial.st_mode) or stat.S_ISLNK(initial.st_mode)
        ):
            return False
        backup_retired_leaf(plan, candidate, parent_fd, leaf, initial)
        quarantine = f".agentcore-retired-{secrets.token_hex(16)}"
        os.rename(
            leaf,
            quarantine,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        captured = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
        if file_inode_identity(captured) != file_inode_identity(initial):
            plan.note(
                f"preserve changed retired managed path as {candidate.parent / quarantine}"
            )
            return False
        os.unlink(quarantine, dir_fd=parent_fd)
        return True
    except OSError as exc:
        plan.note(f"skip unsafe retired managed path {candidate}: {exc}")
        return False
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


def backup_retired_leaf(
    plan: Plan,
    candidate: Path,
    parent_fd: int,
    leaf: str,
    metadata: os.stat_result,
) -> None:
    target = plan.backup_dir / relative_backup_path(candidate)
    target.parent.mkdir(parents=True, exist_ok=True)
    if stat.S_ISLNK(metadata.st_mode):
        target.symlink_to(os.readlink(leaf, dir_fd=parent_fd))
    else:
        descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            opened_metadata = os.fstat(descriptor)
            if file_identity(opened_metadata) != file_identity(metadata):
                raise OSError("retired managed file changed before backup")
            with os.fdopen(os.dup(descriptor), "rb") as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            if file_identity(os.fstat(descriptor)) != file_identity(metadata):
                raise OSError("retired managed file changed during backup")
            chmod_best_effort(target, stat.S_IMODE(metadata.st_mode))
            os.utime(target, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        finally:
            os.close(descriptor)
    plan.backed_up.append(candidate)


def file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def file_inode_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode))


def build_rendered_hooks_config(python_executable: str | None = None) -> str:
    template = json.loads((SRC_CODEX / "hooks.json").read_text(encoding="utf-8"))
    executable = python_executable or str(Path(sys.executable).resolve())
    python_command_windows = subprocess.list2cmdline([executable])
    python_command_posix = shlex.quote(executable)
    for groups in template.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("commandWindows")
                if isinstance(command, str):
                    hook["commandWindows"] = command.replace(
                        "{{PYTHON_EXECUTABLE}}", python_command_windows
                    )
                command = hook.get("command")
                if isinstance(command, str):
                    hook["command"] = command.replace(
                        "{{PYTHON_EXECUTABLE_POSIX}}", python_command_posix
                    )
    rendered = json.dumps(template, indent=2) + "\n"
    if "{{PYTHON_EXECUTABLE" in rendered:
        raise ValueError("unresolved Python executable placeholder in hooks.json")
    return rendered


def safe_manifest_relative_path(path: Path) -> bool:
    windows_path = PureWindowsPath(str(path))
    return (
        bool(path.parts)
        and not path.is_absolute()
        and not path.anchor
        and not path.drive
        and not path.root
        and ".." not in path.parts
        and not windows_path.is_absolute()
        and not windows_path.drive
        and not windows_path.root
        and ".." not in windows_path.parts
    )


def safe_profile_manifest_name(value: str) -> bool:
    path = Path(value)
    return (
        path.name == value
        and value.endswith(PROFILE_CONFIG_GLOB.removeprefix("*"))
        and safe_manifest_relative_path(path)
    )


def contained_manifest_path(root: Path, relative: Path) -> Path | None:
    if not safe_manifest_relative_path(relative):
        return None
    resolved_root = root.resolve(strict=False)
    candidate = (root / relative).resolve(strict=False)
    return candidate if candidate.is_relative_to(resolved_root) else None


def contained_manifest_leaf_path(root: Path, relative: Path) -> Path | None:
    """Return a contained leaf path without resolving the leaf symlink itself."""

    if not safe_manifest_relative_path(relative):
        return None
    resolved_root = root.resolve(strict=False)
    candidate = root / relative
    resolved_parent = candidate.parent.resolve(strict=False)
    return candidate if resolved_parent.is_relative_to(resolved_root) else None


def path_has_symlink_ancestor(root: Path, relative: Path) -> bool:
    current = root
    if current.is_symlink():
        return True
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def load_install_manifest_state() -> tuple[dict[str, list[str]], bool]:
    try:
        path_metadata = MANIFEST_PATH.lstat()
    except OSError:
        return {}, False
    if (
        not stat.S_ISREG(path_metadata.st_mode)
        or path_metadata.st_nlink != 1
        or path_metadata.st_size > MAX_MANIFEST_BYTES
        or (
            os.name == "posix"
            and (
                path_metadata.st_uid != os.getuid()
                or bool(path_metadata.st_mode & 0o022)
            )
        )
    ):
        return {}, False
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(MANIFEST_PATH, flags)
        opened_metadata = os.fstat(descriptor)
        expected = (path_metadata.st_dev, path_metadata.st_ino, path_metadata.st_size)
        actual = (opened_metadata.st_dev, opened_metadata.st_ino, opened_metadata.st_size)
        if expected != actual or not stat.S_ISREG(opened_metadata.st_mode):
            return {}, False
        handle = os.fdopen(descriptor, "r", encoding="utf-8")
        descriptor = None
        with handle:
            payload = json.load(handle)
    except (OSError, ValueError, UnicodeError):
        return {}, False
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return {}, False
    trees = payload.get("managed_trees")
    if not isinstance(trees, dict):
        return {}, False
    result: dict[str, list[str]] = {}
    for key, values in trees.items():
        if not isinstance(key, str) or not isinstance(values, list):
            continue
        result[key] = [
            value
            for value in values
            if isinstance(value, str)
        ]
    return result, True


def load_install_manifest() -> dict[str, list[str]]:
    return load_install_manifest_state()[0]


def write_install_manifest(plan: Plan, installed_trees: dict[str, list[str]]) -> None:
    content = json.dumps(
        {"schema_version": 1, "managed_trees": installed_trees},
        indent=2,
        sort_keys=True,
    ) + "\n"
    if (
        not MANIFEST_PATH.is_symlink()
        and MANIFEST_PATH.exists()
        and MANIFEST_PATH.read_text(encoding="utf-8") == content
    ):
        plan.note(f"unchanged file {MANIFEST_PATH}")
        return

    plan.backup(MANIFEST_PATH)
    plan.note(f"write file {MANIFEST_PATH}")
    if plan.dry_run:
        return

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(MANIFEST_PATH.parent),
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            tmp_name = handle.name
        chmod_best_effort(Path(tmp_name), 0o600)
        os.replace(tmp_name, MANIFEST_PATH)
        tmp_name = None
        try:
            directory_fd = os.open(MANIFEST_PATH.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)


def build_merged_config() -> str:
    baseline_path = SRC_CODEX / "config.toml"
    baseline_text = baseline_path.read_text(encoding="utf-8")
    live_text = ""
    live_data: dict[str, Any] = {}
    if (LIVE_CODEX / "config.toml").exists():
        live_text = (LIVE_CODEX / "config.toml").read_text(encoding="utf-8")
        live_data = load_toml(LIVE_CODEX / "config.toml")

    writable_roots = existing_workspace_roots(live_data)
    tmp_root = str(LIVE_CODEX / "tmp")
    if tmp_root not in writable_roots:
        writable_roots.append(tmp_root)

    runtime_grants = detect_codex_runtime_read_grants() + detect_skill_read_grants()
    text = preserve_local_top_level_keys(baseline_text, live_data)
    text = ensure_workspace_roots(text, writable_roots)
    text = ensure_filesystem_grants(text, runtime_grants)

    local_sections = extract_local_config_sections(live_text)
    repo_project = f'[projects."{escape_toml_basic_string(str(REPO_ROOT))}"]\ntrust_level = "trusted"\n'
    repo_project_header = repo_project.splitlines()[0]
    if all(section.splitlines()[0] != repo_project_header for section in local_sections if section.splitlines()):
        local_sections.append(repo_project)
    local_sections = dedupe_sections(local_sections)

    if local_sections:
        text = (
            text.rstrip()
            + "\n\n################################################################################\n"
            + "# Machine-local preserved/generated settings\n"
            + "################################################################################\n\n"
            + "\n\n".join(section.rstrip() for section in local_sections)
            + "\n"
        )
    return text


def detect_codex_runtime_read_grants() -> list[str]:
    codex = shutil.which("codex")
    if not codex:
        return []
    resolved = Path(codex).resolve()
    try:
        resolved.relative_to(HOME)
    except ValueError:
        return []

    parts = resolved.parts
    if "installs" in parts and "node" in parts:
        node_index = parts.index("node")
        return [str(Path(*parts[: node_index + 1]))]
    if "node_modules" in parts:
        node_modules_index = parts.index("node_modules")
        return [str(Path(*parts[: node_modules_index + 1]))]
    if resolved.parent.name == "bin":
        return [str(resolved.parent.parent)]
    return [str(resolved.parent)]


def detect_skill_read_grants() -> list[str]:
    """Return host-local skill roots that Codex sandboxes need to read."""

    grants: list[str] = []
    for path in (LIVE_AGENTS / "skills", LIVE_CODEX / "skills" / ".system"):
        if path.exists():
            grants.append(str(path))

    skills_dir = LIVE_AGENTS / "skills"
    if skills_dir.exists():
        for item in sorted(skills_dir.iterdir()):
            if not item.is_symlink():
                continue
            try:
                target = item.resolve(strict=True)
            except OSError:
                continue
            if (target / "SKILL.md").exists():
                grants.append(str(target))

    return dedupe_strings(grants)


def existing_workspace_roots(data: dict[str, Any]) -> list[str]:
    roots = list_existing_strings(
        data.get("sandbox_workspace_write", {}).get("writable_roots", [])
    )
    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        profile = permissions.get(AGENTCORE_PERMISSION_PROFILE)
        if isinstance(profile, dict):
            workspace_roots = profile.get("workspace_roots")
            if isinstance(workspace_roots, dict):
                roots.extend(
                    str(path)
                    for path, enabled in workspace_roots.items()
                    if enabled is True and isinstance(path, str) and path
                )
    return list_existing_paths(dedupe_strings(roots))


def ensure_workspace_roots(text: str, roots: list[str]) -> str:
    roots = list_existing_paths(roots)
    if not roots:
        return text
    table = f"{AGENTCORE_PERMISSION_TABLE}.workspace_roots"
    return upsert_table_lines(
        text,
        table,
        [f'"{escape_toml_basic_string(root)}" = true' for root in roots],
    )


def ensure_filesystem_grants(text: str, grants: list[str]) -> str:
    grants = [grant for grant in grants if grant]
    if not grants:
        return text
    table = f"{AGENTCORE_PERMISSION_TABLE}.filesystem"
    return upsert_table_lines(
        text,
        table,
        [f'"{escape_toml_basic_string(grant)}" = "read"' for grant in grants],
    )


def upsert_table_lines(text: str, table: str, new_lines: list[str]) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_table = False
    inserted = False
    existing_lines = set(lines)
    for line in lines:
        if line.strip() == f"[{table}]":
            in_table = True
            out.append(line)
            for new_line in new_lines:
                if new_line not in existing_lines:
                    out.append(new_line)
            inserted = True
            continue
        if in_table and line.startswith("[") and line.strip().endswith("]"):
            in_table = False
        out.append(line)
    if not inserted:
        out.append("")
        out.append(f"[{table}]")
        out.extend(new_lines)
    return "\n".join(out) + "\n"


def extract_local_config_sections(text: str) -> list[str]:
    sections: list[str] = []
    current_name: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_name and is_local_table(current_name) and current_lines:
            sections.append("\n".join(current_lines))

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            flush()
            current_name = stripped.strip("[]")
            current_lines = [line]
        elif current_name is not None:
            current_lines.append(line)
    flush()
    return dedupe_sections(sections)


def is_local_table(name: str) -> bool:
    if name in CONFIG_LOCAL_TABLES:
        return True
    return any(name.startswith(prefix) for prefix in CONFIG_LOCAL_TABLE_PREFIXES)


def preserve_local_top_level_keys(text: str, live_data: dict[str, Any]) -> str:
    for key in sorted(CONFIG_LOCAL_TOP_LEVEL_KEYS):
        value = live_data.get(key)
        if isinstance(value, str) and value:
            text = replace_top_level_key(text, key, f'"{escape_toml_basic_string(value)}"')
    return text


def dedupe_sections(sections: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for section in sections:
        header = section.splitlines()[0] if section.splitlines() else section
        if header in seen:
            continue
        seen.add(header)
        result.append(section)
    return result


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def replace_top_level_key(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    replaced = False
    inserted = False
    for line in lines:
        stripped = line.strip()
        if not inserted and stripped.startswith("[") and stripped.endswith("]"):
            if not replaced:
                out.append(f"{key} = {value}")
                replaced = True
            inserted = True
        if not inserted and stripped.startswith(f"{key} "):
            out.append(f"{key} = {value}")
            replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(f"{key} = {value}")
    return "\n".join(out) + "\n"


def validate() -> list[str]:
    failures: list[str] = []
    toml_paths = [SRC_CODEX / "config.toml", LIVE_CODEX / "config.toml"]
    toml_paths.extend(sorted(SRC_CODEX.glob(PROFILE_CONFIG_GLOB)))
    toml_paths.extend(sorted(LIVE_CODEX.glob(PROFILE_CONFIG_GLOB)))
    for path in toml_paths:
        if path.exists():
            try:
                load_toml(path)
            except Exception as exc:  # noqa: BLE001 - validation should report all parse errors.
                failures.append(f"{path}: TOML parse failed: {exc}")

    if (SRC_CODEX / "config.toml").exists():
        try:
            failures.extend(validate_portable_permission_profile(SRC_CODEX / "config.toml"))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{SRC_CODEX / 'config.toml'}: permission validation failed: {exc}")

    live_json_paths = [LIVE_CODEX / "hooks.json", MANIFEST_PATH]
    for dirname in ACTIVE_CODEX_TREES:
        live_json_paths.extend((LIVE_CODEX / dirname).rglob("*.json"))
    json_paths = list(SRC_CODEX.rglob("*.json")) + [
        path for path in live_json_paths if path.exists() and not path.is_symlink()
    ]
    for json_path in json_paths:
        if should_skip(json_path.relative_to(json_path.anchor) if json_path.is_absolute() else json_path):
            continue
        try:
            json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{json_path}: JSON parse failed: {exc}")

    for script in list((SRC_CODEX / "hooks").glob("*.py")) + list((LIVE_CODEX / "hooks").glob("*.py")):
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{script}: Python compile failed: {exc}")

    forbidden = find_forbidden_runtime_files(SRC_CODEX) + find_forbidden_runtime_files(SRC_AGENTS)
    for managed_root in (
        LIVE_CODEX / "agents",
        LIVE_CODEX / "rules",
        LIVE_CODEX / "hooks",
        LIVE_AGENTS / "skills",
    ):
        forbidden.extend(find_forbidden_runtime_files(managed_root))
    for path in forbidden:
        failures.append(f"forbidden runtime/private file present in managed mirror path: {path}")
    return failures


def validate_portable_permission_profile(path: Path) -> list[str]:
    """Reject checked-in filesystem grants that point at missing optional paths."""

    data = load_toml(path)
    profile = (
        data.get("permissions", {})
        .get(AGENTCORE_PERMISSION_PROFILE, {})
    )
    if not isinstance(profile, dict):
        return []
    filesystem = profile.get("filesystem", {})
    if not isinstance(filesystem, dict):
        return []
    workspace_table = filesystem.get(":workspace_roots", {})
    if not isinstance(workspace_table, dict):
        return []

    failures: list[str] = []
    for rel_path, grant in workspace_table.items():
        if grant != "read" or not isinstance(rel_path, str):
            continue
        if has_glob_metachar(rel_path):
            continue
        if not (REPO_ROOT / rel_path).exists():
            failures.append(
                f"{path}: workspace-root read grant points at missing path: {rel_path}"
            )
    return failures


def has_glob_metachar(value: str) -> bool:
    return any(char in value for char in "*?[")


def find_forbidden_runtime_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    results: list[Path] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if should_skip(rel) and path.name not in {"tmp", "memories"}:
            results.append(path)
    return results


def load_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def list_existing_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def list_existing_paths(values: list[str]) -> list[str]:
    results: list[str] = []
    for value in values:
        if path_exists_or_uses_home_convention(value):
            results.append(value)
    return results


def path_exists_or_uses_home_convention(value: str) -> bool:
    if value.startswith(("~/", "~\\", "%USERPROFILE%\\", "%USERPROFILE%/")):
        return True
    return Path(value).expanduser().exists()


def escape_toml_basic_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def relative_backup_path(path: Path) -> Path:
    if path.is_absolute():
        try:
            return path.relative_to(HOME)
        except ValueError:
            return Path("absolute") / Path(*path.parts[1:])
    return path


def should_skip(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & SKIP_NAMES:
        return True
    return any(fnmatch.fnmatch(rel.name, pattern) for pattern in SKIP_PATTERNS)


def files_equal(src: Path, dst: Path) -> bool:
    return dst.exists() and src.is_file() and dst.is_file() and filecmp.cmp(src, dst, shallow=False)


def chmod_best_effort(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        if os.name != "nt":
            raise


if __name__ == "__main__":
    raise SystemExit(main())
