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
        self.assertEqual(workflow["permissions"], {"contents": "read"})
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
        evennia_command = steps["Run full Evennia suite with coverage"]["run"]
        self.assertEqual(
            evennia_command,
            "uv run --locked coverage run -m evennia test --settings settings.py commands server typeclasses web world",
        )
        self.assertNotIn("evennia test --settings settings.py .", evennia_command)
        self.assertEqual(
            steps["Run top-level regression suite with coverage"]["run"],
            "uv run --locked coverage run -m unittest discover -s tests -t .",
        )
        self.assertIn("coverage report --fail-under=90", steps["Enforce aggregate coverage threshold"]["run"])
        self.assertLess(
            step_names.index("Enforce aggregate coverage threshold"),
            step_names.index("Generate aggregate coverage XML"),
        )
        self.assertLess(
            step_names.index("Generate aggregate coverage XML"),
            step_names.index("Upload coverage reports to Codecov"),
        )

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
        self.assertEqual(
            steps["Generate aggregate coverage XML"]["run"],
            "uv run --locked coverage xml -o coverage.xml",
        )

    @covers_requirement("spec-test-traceability::aggregate-coverage-is-published-to-codecov")
    def test_codecov_upload_is_explicit_and_immutable(self):
        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        upload = next(
            step for step in workflow["jobs"]["quality-gate"]["steps"]
            if step["name"] == "Upload coverage reports to Codecov"
        )
        self.assertEqual(
            upload["uses"],
            "codecov/codecov-action@0fb7174895f61a3b6b78fc075e0cd60383518dac",
        )
        self.assertRegex(upload["uses"], r"codecov/codecov-action@[0-9a-f]{40}$")
        self.assertEqual(upload["with"]["token"], "${{ secrets.CODECOV_TOKEN }}")
        self.assertEqual(upload["with"]["files"], "./coverage.xml")
        self.assertTrue(upload["with"]["disable_search"])
        self.assertTrue(upload["with"]["fail_ci_if_error"])

    @covers_requirement("spec-test-traceability::aggregate-coverage-is-published-to-codecov")
    def test_readme_contains_the_private_codecov_badge_without_upload_secret(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        badge = "[![codecov](https://codecov.io/gh/jim60105/MUD/graph/badge.svg?token=ysbLT6R5c7)](https://codecov.io/gh/jim60105/MUD)"
        self.assertIn(badge, readme)
        self.assertIn("/gh/jim60105/MUD/graph/badge.svg?token=ysbLT6R5c7", readme)
        self.assertNotIn("CODECOV_TOKEN", readme)
        self.assertNotIn("secrets.", readme)


if __name__ == "__main__":
    unittest.main()
