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
        self.assertEqual(workflow["permissions"], {"contents": "read"})

        jobs = workflow["jobs"]
        preflight = jobs["preflight"]
        self.assertEqual(preflight["runs-on"], "ubuntu-latest")
        self.assertIn("Validate OpenSpec", [s["name"] for s in preflight["steps"]])
        self.assertIn(
            "Validate static requirement traceability", [s["name"] for s in preflight["steps"]]
        )
        self.assertIn(
            "Run Node DOM-independent test suite", [s["name"] for s in preflight["steps"]]
        )
        self.assertEqual(preflight["outputs"]["browser-shards"], "${{ steps.shards.outputs.matrix }}")

        evennia_job = jobs["evennia"]
        self.assertEqual(evennia_job["needs"], "preflight")
        evennia_steps = {step["name"]: step for step in evennia_job["steps"]}
        self.assertEqual(
            evennia_steps["Prepare Evennia runtime directories"]["run"],
            "mkdir -p server/db server/logs",
        )
        self.assertIn(
            "openspec validate --all --strict",
            preflight["steps"][
                [s["name"] for s in preflight["steps"]].index("Validate OpenSpec")
            ]["run"],
        )
        self.assertIn(
            "tools.spec_traceability check",
            preflight["steps"][
                [s["name"] for s in preflight["steps"]].index(
                    "Validate static requirement traceability"
                )
            ]["run"],
        )
        self.assertIn(
            "tools.spec_traceability verify",
            jobs["gate"]["steps"][
                [s["name"] for s in jobs["gate"]["steps"]].index(
                    "Verify successful requirement execution"
                )
            ]["run"],
        )
        evennia_step = evennia_steps["Run full non-browser Evennia suite with coverage"]
        evennia_command = evennia_step["run"]
        self.assertIn(
            "coverage run",
            evennia_command,
        )
        self.assertIn("--concurrency=multiprocessing --parallel-mode", evennia_command)
        self.assertIn("--parallel 4", evennia_command)
        self.assertIn("commands server typeclasses world web.webclient", evennia_command)
        self.assertEqual(evennia_step["env"]["MUD_TEST_SETTINGS"], "1")
        self.assertNotIn("evennia test --settings test_settings.py .", evennia_command)

        top_level_job = jobs["top-level"]
        top_level_step = next(
            step for step in top_level_job["steps"]
            if step["name"] == "Run top-level regression suite with coverage"
        )
        self.assertIn("unittest discover -s tests -t .", top_level_step["run"])

        gate = jobs["gate"]
        gate_step_names = [step["name"] for step in gate["steps"]]
        gate_steps = {step["name"]: step for step in gate["steps"]}
        self.assertIn("coverage report --fail-under=80", gate_steps["Enforce aggregate coverage threshold"]["run"])
        self.assertLess(
            gate_step_names.index("Enforce aggregate coverage threshold"),
            gate_step_names.index("Generate aggregate coverage XML"),
        )
        self.assertLess(
            gate_step_names.index("Generate aggregate coverage XML"),
            gate_step_names.index("Upload coverage reports to Codecov"),
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
        self.assertEqual(coverage["report"]["fail_under"], 80)

        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        jobs = workflow["jobs"]
        evennia_step = next(
            step for step in jobs["evennia"]["steps"]
            if step["name"] == "Run full non-browser Evennia suite with coverage"
        )
        self.assertEqual(evennia_step["env"]["COVERAGE_FILE"], "coverage-evennia")
        browser_jobs = [job for name, job in jobs.items() if name.startswith("browser")]
        browser_step = next(
            step for step in browser_jobs[0]["steps"]
            if step["name"].startswith("Run browser shard")
        )
        self.assertIn("COVERAGE_FILE", browser_step["env"])
        top_level_step = next(
            step for step in jobs["top-level"]["steps"]
            if step["name"] == "Run top-level regression suite with coverage"
        )
        self.assertEqual(top_level_step["env"]["COVERAGE_FILE"], "coverage-top-level")
        gate_steps = {step["name"]: step for step in jobs["gate"]["steps"]}
        self.assertIn("coverage combine", gate_steps["Combine coverage data"]["run"])
        self.assertIn("coverage-evennia*", gate_steps["Combine coverage data"]["run"])
        self.assertIn("tools.verify_coverage_roots", gate_steps["Verify coverage source roots"]["run"])
        self.assertEqual(
            gate_steps["Generate aggregate coverage XML"]["run"],
            "uv run --locked coverage xml -o coverage.xml",
        )

    @covers_requirement(
        "spec-test-traceability::continuous-integration-enforces-both-quality-dimensions"
    )
    def test_coverage_target_is_documented_but_gate_enforces_80(self):
        config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        gate_steps = {step["name"]: step for step in workflow["jobs"]["gate"]["steps"]}
        self.assertEqual(config["tool"]["coverage"]["report"]["fail_under"], 80)
        self.assertIn(
            "coverage report --fail-under=80",
            gate_steps["Enforce aggregate coverage threshold"]["run"],
        )
        traceability_doc = (REPO_ROOT / "docs/development/spec-test-traceability.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("hard gate is 80%", traceability_doc)
        self.assertIn("targets 90%", traceability_doc)
        self.assertIn("targeting 90%", (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    @covers_requirement("spec-test-traceability::aggregate-coverage-is-published-to-codecov")
    def test_codecov_upload_is_explicit_and_immutable(self):
        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        upload = next(
            step for step in workflow["jobs"]["gate"]["steps"]
            if step["name"] == "Upload coverage reports to Codecov"
        )
        self.assertEqual(
            upload["uses"],
            "codecov/codecov-action@fb8b3582c8e4def4969c97caa2f19720cb33a72f",
        )
        self.assertRegex(upload["uses"], r"codecov/codecov-action@[0-9a-f]{40}$")
        self.assertEqual(upload["with"]["token"], "${{ secrets.CODECOV_TOKEN }}")
        self.assertEqual(upload["with"]["files"], "./coverage.xml")
        self.assertTrue(upload["with"]["disable_search"])
        self.assertTrue(upload["with"]["fail_ci_if_error"])

    @covers_requirement("spec-test-traceability::aggregate-coverage-is-published-to-codecov")
    def test_readme_contains_the_private_codecov_badge_without_upload_secret(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        badge = "[![codecov](https://codecov.io/gh/jim60105/Elosern-MUD/graph/badge.svg?token=ysbLT6R5c7)](https://codecov.io/gh/jim60105/Elosern-MUD)"
        self.assertIn(badge, readme)
        self.assertIn("/gh/jim60105/Elosern-MUD/graph/badge.svg?token=ysbLT6R5c7", readme)
        self.assertNotIn("CODECOV_TOKEN", readme)
        self.assertNotIn("secrets.", readme)


if __name__ == "__main__":
    unittest.main()
