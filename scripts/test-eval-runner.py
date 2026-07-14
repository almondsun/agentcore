#!/usr/bin/env python3
"""Regression checks for blind prompts and independent eval evidence helpers."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPTS = REPO_ROOT / "openai" / "dot-codex" / "evals" / "scripts"
RUNNER_PATH = EVAL_SCRIPTS / "run_automated_case.py"
PREFLIGHT_PATH = EVAL_SCRIPTS / "live_run_preflight.py"


def load_script(path: Path, name: str):
    sys.path.insert(0, str(EVAL_SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load eval runner")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(EVAL_SCRIPTS))


class EvalRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_script(RUNNER_PATH, "run_automated_case")
        cls.preflight = load_script(PREFLIGHT_PATH, "live_run_preflight")

    def test_positive_prompts_do_not_expose_rubrics(self) -> None:
        _, catalog = self.runner.load_automation_manifest()
        for case_id, automation in catalog.items():
            case = self.runner.find_case(case_id)
            prompt = self.runner.build_blind_prompt(case, automation)
            self.assertNotIn("pass_criteria", prompt)
            self.assertNotIn("expected_subagents", prompt)
            self.assertNotIn("observed_validation", prompt)
            self.assertNotIn("outcome=pass", prompt)
            self.assertNotIn("What a strong run should do", prompt)
            self.assertNotIn("What this tier is testing", prompt)
            self.assertNotIn("intentionally includes", prompt)

    def test_negative_prompts_do_not_name_workflow_under_test(self) -> None:
        _, catalog = self.runner.load_automation_manifest(kind="negative")
        for case_id, automation in catalog.items():
            case = self.runner.find_case(case_id)
            prompt = self.runner.build_blind_negative_prompt(case, automation)
            self.assertNotIn(case["_workflow"], prompt)
            self.assertNotIn("expected_should_trigger", prompt)
            self.assertNotIn("false-trigger", prompt)
            self.assertNotIn("low-risk control", prompt)
            self.assertNotIn("What a strong run should do", prompt)

    def test_workspace_diff_uses_actual_file_changes(self) -> None:
        before = {"a.txt": "old\n", "removed.txt": "gone\n"}
        after = {"a.txt": "new\n", "added.txt": "here\n"}
        diff = self.runner.workspace_diff(before, after)
        self.assertIn("-old", diff)
        self.assertIn("+new", diff)
        self.assertIn("after/added.txt", diff)
        self.assertIn("before/removed.txt", diff)

    def test_grader_receives_evidence_and_rubric_separately(self) -> None:
        case = self.runner.find_case("wr-easy-local-bugfix")
        prompt = self.runner.build_grader_prompt(
            case,
            "subject closeout",
            "trace evidence",
            "diff evidence",
            "exit_code=0",
            negative=False,
        )
        self.assertIn("The subject never saw this rubric", prompt)
        self.assertIn("subject closeout", prompt)
        self.assertIn("pass_criteria", prompt)

    def test_static_validation_never_executes_subject_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "executed"
            (root / "conftest.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
                encoding="utf-8",
            )
            evidence = self.runner.run_independent_validation(root, "repo-bugfix")
            self.assertFalse(marker.exists())
            self.assertIn("static_parse_status=ok", evidence)

    def test_snapshot_ignores_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "workspace"
            root.mkdir()
            outside = base / "outside-eval-secret.txt"
            outside.write_text("do-not-collect", encoding="utf-8")
            link = root / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            snapshot = self.runner.snapshot_workspace(root)
            self.assertNotIn("linked.txt", snapshot)
            self.assertNotIn("do-not-collect", repr(snapshot))

    def test_run_date_rejects_path_syntax(self) -> None:
        for value in ("../outside", "/tmp/outside", "2026-7-1", "not-a-date"):
            with self.assertRaises(ValueError):
                self.runner.validate_run_date(value)

    def test_artifact_path_rejects_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run_root = base / "results" / "2026-07-14"
            run_root.mkdir(parents=True)
            outside = base / "outside"
            outside.mkdir()
            try:
                (run_root / "workspaces").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            with self.assertRaises(ValueError):
                self.runner.contained_child(run_root, "workspaces", "case")

    def test_preflight_results_probe_is_random_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            outcome = self.preflight.check_results_dir(results)
            self.assertTrue(outcome["ok"], outcome)
            self.assertFalse((results / ".preflight").exists())

    def test_preflight_results_probe_rejects_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            outside = base / "outside"
            outside.mkdir()
            linked = base / "linked"
            try:
                linked.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            outcome = self.preflight.check_results_dir(linked / "results")
            self.assertFalse(outcome["ok"], outcome)
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
