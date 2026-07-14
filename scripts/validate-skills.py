#!/usr/bin/env python3
"""Validate the structure and local references of maintained Codex skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - reported by main.
    yaml = None

YAML_ERROR = yaml.YAMLError if yaml is not None else ValueError


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "openai" / "dot-agents" / "skills"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


if yaml is not None:
    class UniqueKeyLoader(yaml.SafeLoader):
        pass


    def construct_unique_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "mapping key must be a scalar value",
                    key_node.start_mark,
                ) from exc
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping


    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_unique_mapping,
    )


def load_yaml(text: str):
    if yaml is None:
        raise RuntimeError("PyYAML is required; install pyyaml==6.0.3")
    return yaml.load(text, Loader=UniqueKeyLoader)


def frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"{path}: cannot read UTF-8 text: {exc}"]
    if not lines or lines[0] != "---":
        return {}, [f"{path}: missing opening YAML frontmatter delimiter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, [f"{path}: missing closing YAML frontmatter delimiter"]

    try:
        parsed = load_yaml("\n".join(lines[1:end]))
    except (RuntimeError, YAML_ERROR) as exc:
        return {}, [f"{path}: invalid YAML frontmatter: {exc}"]
    if not isinstance(parsed, dict):
        return {}, [f"{path}: YAML frontmatter must be a mapping"]
    values = {key: parsed.get(key) for key in ("name", "description")}
    for key in ("name", "description"):
        if not isinstance(values.get(key), str) or not values[key].strip():
            errors.append(f"{path}: missing or invalid {key!r} frontmatter value")
    return {key: value for key, value in values.items() if isinstance(value, str)}, errors


def yaml_file_errors(path: Path) -> list[str]:
    try:
        parsed = load_yaml(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, RuntimeError) as exc:
        return [f"{path}: cannot read YAML: {exc}"]
    except YAML_ERROR as exc:
        return [f"{path}: invalid YAML: {exc}"]
    return [] if isinstance(parsed, dict) else [f"{path}: YAML root must be a mapping"]


def local_link_errors(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for raw_target in LINK_RE.findall(text):
        stripped = raw_target.strip()
        if stripped.startswith("<") and ">" in stripped:
            target = stripped[1:stripped.index(">")]
        else:
            target = stripped.split(maxsplit=1)[0]
        parsed = urlparse(target)
        if not target or target.startswith("#") or parsed.scheme or parsed.netloc:
            continue
        relative = unquote(parsed.path)
        if relative and not (path.parent / relative).exists():
            errors.append(f"{path}: broken local link {raw_target!r}")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    if not SKILLS_ROOT.is_dir():
        return [f"missing skills directory: {SKILLS_ROOT}"]

    seen_names: set[str] = set()
    skill_dirs = sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
    if not skill_dirs:
        return [f"no skills found under {SKILLS_ROOT}"]
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{skill_dir}: missing SKILL.md")
            continue
        values, file_errors = frontmatter(skill_file)
        errors.extend(file_errors)
        name = values.get("name", "")
        if name:
            if not NAME_RE.fullmatch(name):
                errors.append(f"{skill_file}: invalid skill name {name!r}")
            if name != skill_dir.name:
                errors.append(
                    f"{skill_file}: skill name {name!r} does not match directory {skill_dir.name!r}"
                )
            if name in seen_names:
                errors.append(f"{skill_file}: duplicate skill name {name!r}")
            seen_names.add(name)
        errors.extend(local_link_errors(skill_file))
        for metadata_file in sorted(skill_dir.rglob("*.yaml")):
            errors.extend(yaml_file_errors(metadata_file))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("skill validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"skill validation passed ({len(list(SKILLS_ROOT.glob('*/SKILL.md')))} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
