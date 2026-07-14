#!/usr/bin/env python3
"""Regression tests for static custom-skill validation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-skills.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_skills", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load skill validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def validate_tree(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            old_root = self.validator.SKILLS_ROOT
            self.validator.SKILLS_ROOT = root
            try:
                return self.validator.validate()
            finally:
                self.validator.SKILLS_ROOT = old_root

    def test_valid_skill_and_auxiliary_metadata_pass(self) -> None:
        errors = self.validate_tree(
            {
                "sample/SKILL.md": "---\nname: sample\ndescription: Useful.\n---\n",
                "sample/agents/openai.yaml": "interface:\n  display_name: Sample\n",
            }
        )
        self.assertEqual(errors, [])

    def test_malformed_and_duplicate_frontmatter_fail(self) -> None:
        malformed = self.validate_tree(
            {"sample/SKILL.md": "---\nname: sample\ndescription: [broken\n---\n"}
        )
        duplicate = self.validate_tree(
            {
                "sample/SKILL.md": (
                    "---\nname: sample\nname: other\ndescription: Useful.\n---\n"
                )
            }
        )
        self.assertTrue(any("invalid YAML frontmatter" in error for error in malformed))
        self.assertTrue(any("duplicate key" in error for error in duplicate))

    def test_name_mismatch_and_broken_link_fail(self) -> None:
        errors = self.validate_tree(
            {
                "sample/SKILL.md": (
                    "---\nname: other\ndescription: Useful.\n---\n"
                    "[missing](references/missing.md)\n"
                )
            }
        )
        self.assertTrue(any("does not match directory" in error for error in errors))
        self.assertTrue(any("broken local link" in error for error in errors))

    def test_angle_bracket_link_with_space_and_anchor_passes(self) -> None:
        errors = self.validate_tree(
            {
                "sample/SKILL.md": (
                    "---\nname: sample\ndescription: Useful.\n---\n"
                    "[reference](<references/my file.md#section>)\n"
                ),
                "sample/references/my file.md": "# Section\n",
            }
        )
        self.assertEqual(errors, [])

    def test_duplicate_names_and_missing_skill_file_fail(self) -> None:
        errors = self.validate_tree(
            {
                "first/SKILL.md": "---\nname: first\ndescription: Useful.\n---\n",
                "second/SKILL.md": "---\nname: first\ndescription: Useful.\n---\n",
                "empty/placeholder.txt": "x\n",
            }
        )
        self.assertTrue(any("duplicate skill name" in error for error in errors))
        self.assertTrue(any("missing SKILL.md" in error for error in errors))

    def test_invalid_auxiliary_yaml_fails(self) -> None:
        errors = self.validate_tree(
            {
                "sample/SKILL.md": "---\nname: sample\ndescription: Useful.\n---\n",
                "sample/agents/openai.yaml": "interface: [broken\n",
            }
        )
        self.assertTrue(any("invalid YAML" in error for error in errors))

    def test_unhashable_yaml_key_is_reported_instead_of_crashing(self) -> None:
        errors = self.validate_tree(
            {
                "sample/SKILL.md": "---\nname: sample\ndescription: Useful.\n---\n",
                "sample/agents/openai.yaml": "? [a, b]\n: value\n",
            }
        )
        self.assertTrue(any("mapping key must be a scalar" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
