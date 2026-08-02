"""Repository contract tests for the traceability and coverage quality gate."""

from pathlib import Path
import tomllib
import unittest

import yaml

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]


class QualityGateContractTests(unittest.TestCase):
    @covers_requirement(
        "spec-test-traceability::continuous-integration-enforces-both-quality-dimensions"
    )
    def test_workflow_runs_every_required_gate_on_pushes_and_pull_requests(self):
        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        triggers = workflow.get("on", workflow.get(True))
        self.assertEqual(set(triggers), {"push", "pull_request"})

        job = workflow["jobs"]["quality-gate"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        steps = {step["name"]: step for step in job["steps"]}
        self.assertEqual(
            steps["Prepare Evennia runtime directories"]["run"],
            "mkdir -p server/db server/logs",
        )
        self.assertEqual(
            steps["Configure traceability evidence path"]["run"],
            'echo "OPENSPEC_TEST_EVIDENCE=$RUNNER_TEMP/spec-test-evidence.jsonl" >> "$GITHUB_ENV"',
        )
        step_names = [step["name"] for step in job["steps"]]
        self.assertLess(
            step_names.index("Prepare Evennia runtime directories"),
            step_names.index("Run full Evennia suite with coverage"),
        )
        self.assertIn("openspec validate --all --strict", steps["Validate OpenSpec"]["run"])
        self.assertIn("tools.spec_traceability check", steps["Validate static requirement traceability"]["run"])
        self.assertIn("tools.spec_traceability verify", steps["Verify successful requirement execution"]["run"])
        self.assertIn("evennia test --settings settings.py .", steps["Run full Evennia suite with coverage"]["run"])
        self.assertIn("unittest discover tests", steps["Run top-level regression suite with coverage"]["run"])
        self.assertIn("coverage report --fail-under=90", steps["Enforce aggregate coverage threshold"]["run"])

    @covers_requirement(
        "spec-test-traceability::coverage-configuration-is-reproducible-and-project-scoped"
    )
    def test_coverage_config_and_workflow_use_the_exact_aggregate_scope(self):
        config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        coverage = config["tool"]["coverage"]
        self.assertTrue(coverage["run"]["branch"])
        self.assertEqual(
            coverage["run"]["source"],
            ["commands", "server", "typeclasses", "web", "world"],
        )
        self.assertEqual(coverage["report"]["omit"], ["*/tests/*"])
        self.assertEqual(coverage["report"]["fail_under"], 90)

        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        steps = {step["name"]: step for step in workflow["jobs"]["quality-gate"]["steps"]}
        self.assertEqual(
            steps["Run full Evennia suite with coverage"]["env"]["COVERAGE_FILE"],
            ".coverage.evennia",
        )
        self.assertEqual(
            steps["Run top-level regression suite with coverage"]["env"]["COVERAGE_FILE"],
            ".coverage.top-level",
        )
        self.assertEqual(
            steps["Combine coverage data"]["run"],
            "uv run --locked coverage combine .coverage.evennia .coverage.top-level",
        )
        self.assertIn("tools.verify_coverage_roots", steps["Verify coverage source roots"]["run"])


if __name__ == "__main__":
    unittest.main()
