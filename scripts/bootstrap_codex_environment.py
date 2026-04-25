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
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
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
    "projects.",
    "plugins.",
)

CONFIG_LOCAL_TABLES = {
    "tui.model_availability_nux",
}


class Plan:
    """Collects actions and applies them unless running in dry-run mode."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.backup_dir = BACKUP_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")
        self.actions: list[str] = []
        self.backed_up: list[Path] = []

    def note(self, message: str) -> None:
        self.actions.append(message)

    def ensure_dir(self, path: Path, mode: int | None = None) -> None:
        self.note(f"ensure directory {path}")
        if self.dry_run:
            return
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
        if dst.exists() and files_equal(src, dst):
            self.note(f"unchanged file {dst}")
            return
        self.backup(dst)
        self.note(f"copy file {src} -> {dst}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if mode is not None:
            chmod_best_effort(dst, mode)

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

    for dirname in ("agents", "rules", "templates", "evals", "hooks"):
        copy_tree_contents(SRC_CODEX / dirname, LIVE_CODEX / dirname, plan)

    for name in ("AGENTS.md", "README.md", "hooks.json"):
        src = SRC_CODEX / name
        if src.exists():
            plan.replace_file(src, LIVE_CODEX / name)

    install_version_json(plan)
    copy_tree_contents(SRC_AGENTS / "skills", LIVE_AGENTS / "skills", plan)
    agents_readme = SRC_AGENTS / "README.md"
    if agents_readme.exists():
        plan.replace_file(agents_readme, LIVE_AGENTS / "README.md")

    merged_config = build_merged_config()
    plan.write_text_atomic(LIVE_CODEX / "config.toml", merged_config, 0o600)


def install_version_json(plan: Plan) -> None:
    src = SRC_CODEX / "version.json"
    dst = LIVE_CODEX / "version.json"
    if not src.exists():
        return
    if not dst.exists():
        plan.replace_file(src, dst)
        return
    if version_tuple(src) >= version_tuple(dst):
        plan.replace_file(src, dst)
    else:
        plan.note(f"preserve newer live version file {dst}")


def copy_tree_contents(src_dir: Path, dst_dir: Path, plan: Plan) -> None:
    if not src_dir.exists():
        return
    plan.ensure_dir(dst_dir)
    for src in sorted(src_dir.rglob("*")):
        rel = src.relative_to(src_dir)
        if should_skip(rel):
            continue
        dst = dst_dir / rel
        if src.is_dir():
            plan.ensure_dir(dst)
        elif src.is_file():
            plan.replace_file(src, dst)


def build_merged_config() -> str:
    baseline_path = SRC_CODEX / "config.toml"
    baseline_text = baseline_path.read_text(encoding="utf-8")
    live_text = ""
    live_data: dict[str, Any] = {}
    if (LIVE_CODEX / "config.toml").exists():
        live_text = (LIVE_CODEX / "config.toml").read_text(encoding="utf-8")
        live_data = load_toml(LIVE_CODEX / "config.toml")

    writable_roots = list_existing_strings(
        live_data.get("sandbox_workspace_write", {}).get("writable_roots", [])
    )
    tmp_root = str(LIVE_CODEX / "tmp")
    if tmp_root not in writable_roots:
        writable_roots.append(tmp_root)

    runtime_grants = detect_codex_runtime_read_grants()
    text = replace_table_key(
        baseline_text,
        "sandbox_workspace_write",
        "writable_roots",
        format_toml_string_array(writable_roots),
    )
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


def ensure_filesystem_grants(text: str, grants: list[str]) -> str:
    grants = [grant for grant in grants if grant]
    if not grants:
        return text
    lines = text.splitlines()
    out: list[str] = []
    in_table = False
    inserted = False
    existing_lines = set(lines)
    for line in lines:
        if line.strip() == "[permissions.workspace.filesystem]":
            in_table = True
            out.append(line)
            for grant in grants:
                grant_line = f'"{escape_toml_basic_string(grant)}" = "read"'
                if grant_line not in existing_lines:
                    out.append(grant_line)
            inserted = True
            continue
        if in_table and line.startswith("[") and line.strip().endswith("]"):
            in_table = False
        out.append(line)
    if not inserted:
        out.append("")
        out.append("[permissions.workspace.filesystem]")
        for grant in grants:
            out.append(f'"{escape_toml_basic_string(grant)}" = "read"')
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


def replace_table_key(text: str, table: str, key: str, value: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_table = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"[{table}]":
            in_table = True
            out.append(line)
            continue
        if in_table and stripped.startswith("[") and stripped.endswith("]"):
            if not replaced:
                out.append(f"{key} = {value}")
                replaced = True
            in_table = False
        if in_table and stripped.startswith(f"{key} "):
            out.append(f"{key} = {value}")
            replaced = True
            continue
        out.append(line)
    if in_table and not replaced:
        out.append(f"{key} = {value}")
    return "\n".join(out) + "\n"


def validate() -> list[str]:
    failures: list[str] = []
    for path in (SRC_CODEX / "config.toml", LIVE_CODEX / "config.toml"):
        if path.exists():
            try:
                load_toml(path)
            except Exception as exc:  # noqa: BLE001 - validation should report all parse errors.
                failures.append(f"{path}: TOML parse failed: {exc}")

    for json_path in list(SRC_CODEX.rglob("*.json")) + list(LIVE_CODEX.rglob("*.json")):
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
        LIVE_CODEX / "templates",
        LIVE_CODEX / "evals",
        LIVE_CODEX / "hooks",
        LIVE_AGENTS / "skills",
    ):
        forbidden.extend(find_forbidden_runtime_files(managed_root))
    for path in forbidden:
        failures.append(f"forbidden runtime/private file present in managed mirror path: {path}")
    return failures


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


def format_toml_string_array(values: list[str]) -> str:
    return "[" + ", ".join(f'"{escape_toml_basic_string(value)}"' for value in values) + "]"


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


def version_tuple(path: Path) -> tuple[int, ...]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        version = str(data.get("version", "0"))
    except Exception:
        return (0,)
    result: list[int] = []
    for part in version.replace("-", ".").split("."):
        if part.isdigit():
            result.append(int(part))
        else:
            break
    return tuple(result) or (0,)


def chmod_best_effort(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
