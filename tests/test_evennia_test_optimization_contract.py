"""Repository contracts for the optimized Evennia test profiles."""

from pathlib import Path
import ast
import os
import subprocess
import sys
import unittest

import yaml

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = REPO_ROOT / "server" / "db" / "evennia-test.sqlite3"


class TestSettingsContractTests(unittest.TestCase):
    def _load_settings(
        self, *, enabled: bool, arguments: list[str]
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if enabled:
            env["MUD_TEST_SETTINGS"] = "1"
        else:
            env.pop("MUD_TEST_SETTINGS", None)
        source = (
            "import sys; "
            f"sys.argv = {['evennia', *arguments]!r}; "
            "import server.conf.test_settings as settings; "
            "print(settings.PASSWORD_HASHERS[0]); "
            "print(settings.DATABASES['default']['TEST']['NAME'])"
        )
        return subprocess.run(
            [sys.executable, "-c", source],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    @covers_requirement(
        "evennia-test-optimization::test-only-settings-are-explicit-and-isolated"
    )
    def test_explicit_test_context_selects_isolated_fast_settings(self):
        result = self._load_settings(enabled=True, arguments=["test"])
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn("django.contrib.auth.hashers.MD5PasswordHasher", lines)
        self.assertIn(str(TEST_DATABASE), lines)
        self.assertNotEqual(TEST_DATABASE, REPO_ROOT / "server" / "db" / "evennia.db3")

    def test_missing_opt_in_and_non_test_commands_are_rejected(self):
        missing_opt_in = self._load_settings(enabled=False, arguments=["test"])
        server_command = self._load_settings(enabled=True, arguments=["start"])
        disguised_server = self._load_settings(
            enabled=True, arguments=["start", "test"]
        )
        disguised_migration = self._load_settings(
            enabled=True, arguments=["migrate", "test"]
        )
        self.assertNotEqual(missing_opt_in.returncode, 0)
        self.assertNotEqual(server_command.returncode, 0)
        self.assertNotEqual(disguised_server.returncode, 0)
        self.assertNotEqual(disguised_migration.returncode, 0)
        self.assertIn("restricted to test commands", missing_opt_in.stderr)
        self.assertIn("restricted to test commands", server_command.stderr)

    def test_production_and_browser_settings_do_not_enable_test_profile(self):
        production = (REPO_ROOT / "server/conf/settings.py").read_text(encoding="utf-8")
        browser = (REPO_ROOT / "server/conf/browser_settings.py").read_text(encoding="utf-8")
        for source in (production, browser):
            self.assertNotIn("MD5PasswordHasher", source)
            self.assertNotIn("evennia-test.sqlite3", source)


class TestOwnershipContractTests(unittest.TestCase):
    @covers_requirement(
        "evennia-test-optimization::supported-execution-profiles-preserve-suite-ownership"
    )
    def test_every_web_python_test_has_exactly_one_owner(self):
        non_browser = set((REPO_ROOT / "web/webclient").rglob("test*.py"))
        browser = set((REPO_ROOT / "web/tests/browser").glob("test*.py"))
        all_web_tests = set((REPO_ROOT / "web").rglob("test*.py"))
        self.assertTrue(non_browser)
        self.assertTrue(browser)
        self.assertFalse(non_browser & browser)
        self.assertEqual(non_browser | browser, all_web_tests)

    @covers_requirement(
        "evennia-test-optimization::existing-quality-gates-remain-authoritative",
        "evennia-test-optimization::parallel-execution-is-gated-by-equivalence",
    )
    def test_workflow_uses_three_disjoint_coverage_owners(self):
        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        jobs = workflow["jobs"]
        self.assertEqual(jobs["evennia"]["needs"], "preflight")
        self.assertEqual(jobs["top-level"]["needs"], "preflight")
        self.assertEqual(
            jobs["gate"]["needs"], ["evennia", "browser", "top-level"]
        )

        browser_jobs = [job for name, job in jobs.items() if name.startswith("browser")]
        self.assertTrue(browser_jobs)
        browser_strategy = browser_jobs[0]["strategy"]
        self.assertFalse(browser_strategy.get("fail-fast", False))
        self.assertIn(
            "needs.preflight.outputs.browser-shards",
            browser_strategy["matrix"]["include"],
        )
        shards_step = next(
            step for step in workflow["jobs"]["preflight"]["steps"]
            if step["name"] == "Compute browser shard matrix"
        )
        self.assertIn("['shards']", shards_step["run"])

        evennia_step = next(
            step
            for step in jobs["evennia"]["steps"]
            if step["name"] == "Run full non-browser Evennia suite with coverage"
        )
        self.assertEqual(evennia_step["env"]["COVERAGE_FILE"], "coverage-evennia")
        self.assertIn("commands server typeclasses world web.webclient", evennia_step["run"])
        self.assertIn("--noinput", evennia_step["run"])
        self.assertIn("--parallel 4", evennia_step["run"])
        self.assertIn("--concurrency=multiprocessing --parallel-mode", evennia_step["run"])
        self.assertNotIn(" commands server typeclasses web world", evennia_step["run"])
        self.assertNotIn("web.tests.browser", evennia_step["run"])

        top_level_step = next(
            step
            for step in jobs["top-level"]["steps"]
            if step["name"] == "Run top-level regression suite with coverage"
        )
        self.assertEqual(top_level_step["env"]["COVERAGE_FILE"], "coverage-top-level")
        self.assertIn("unittest discover -s tests -t .", top_level_step["run"])

        browser_run = next(
            step
            for step in browser_jobs[0]["steps"]
            if step["name"].startswith("Run browser shard")
        )["run"]
        self.assertIn("matrix.files", browser_run)
        self.assertNotIn("--parallel", browser_run)
        self.assertNotIn("discover -s web/tests/browser", browser_run)

        gate = jobs["gate"]
        gate_steps = {step["name"]: step for step in gate["steps"]}
        self.assertIn("coverage combine", gate_steps["Combine coverage data"]["run"])
        self.assertIn("coverage-evennia*", gate_steps["Combine coverage data"]["run"])
        self.assertIn(
            "spec_traceability verify",
            gate_steps["Verify successful requirement execution"]["run"],
        )
        self.assertIn(
            "fail-under=80",
            gate_steps["Enforce aggregate coverage threshold"]["run"],
        )

        all_commands = []
        for job in jobs.values():
            for step in job.get("steps", []):
                all_commands.append(step.get("run", ""))
        browser_discovery = "unittest discover -s web/tests/browser -t ."
        self.assertEqual(sum(command.count(browser_discovery) for command in all_commands), 0)

    @covers_requirement(
        "evennia-test-optimization::existing-quality-gates-remain-authoritative"
    )
    def test_browser_shard_manifest_owns_every_browser_test_file_exactly_once(self):
        import json

        manifest = json.loads(
            (REPO_ROOT / ".github/browser-shards.json").read_text(encoding="utf-8")
        )
        shards = manifest["shards"]
        self.assertGreaterEqual(len(shards), 2)
        indices = [shard["index"] for shard in shards]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(len(indices), len(set(indices)), "shard indices must be unique")

        browser_dir = REPO_ROOT / "web/tests/browser"
        discovered = {path.stem for path in browser_dir.glob("test_*.py")}
        self.assertTrue(discovered)
        owned: set[str] = set()
        for shard in shards:
            for dotted in shard["files"]:
                module = dotted.rsplit(".", 1)[-1]
                self.assertIn(module, discovered, f"{dotted} is not a discovered file")
                self.assertNotIn(
                    module, owned, f"{module} is assigned to more than one shard"
                )
                owned.add(module)
        self.assertEqual(
            owned, discovered, "every discovered browser test file must be in a shard"
        )

        workflow = yaml.safe_load(
            (REPO_ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        )
        evennia = workflow["jobs"]["evennia"]
        evennia_step = next(
            step for step in evennia["steps"]
            if step["name"] == "Run full non-browser Evennia suite with coverage"
        )
        self.assertIn("web.webclient", evennia_step["run"])
        self.assertNotIn("web.tests.browser", evennia_step["run"])


class TestOptimizationEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "evennia-test-optimization::optimization-is-based-on-reproducible-measurements"
    )
    def test_performance_report_contains_comparable_runs_and_passing_threshold(self):
        report = (REPO_ROOT / "docs/development/evennia-test-performance.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Baseline commit:", report)
        self.assertIn("Optimized revision identity:", report)
        self.assertIn("Measured 3", report)
        self.assertIn("520.285 seconds", report)
        self.assertIn("354.432 seconds", report)
        self.assertIn("31.9% reduction", report)
        self.assertIn("storage difference is an intentional optimization variable", report)

    @covers_requirement(
        "evennia-test-optimization::fixture-optimization-preserves-the-tested-boundary"
    )
    def test_pure_candidates_use_unittest_while_integration_fixture_remains(self):
        expectations = {
            "world/rules/tests/test_guild_registration.py": {
                "RegistrationBoundaryScanTests": {"unittest.TestCase"},
            },
            "world/maps/tests/test_instance_spawn.py": {
                "InstanceYamlTests": {"unittest.TestCase"},
            },
            "world/rules/tests/test_combat_session.py": {
                "CombatSessionRecordTests": {"unittest.TestCase"},
                "CombatSessionIdTests": {"EvenniaTest"},
            },
            "world/rules/tests/test_guild_exams.py": {
                "ExamRecordTests": {"unittest.TestCase"},
                "ExamStartTests": {"ExamRegistryIsolation", "EvenniaTest"},
            },
        }
        for relative_path, classes in expectations.items():
            tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
            actual = {
                node.name: {ast.unparse(base) for base in node.bases}
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.bases
            }
            for class_name, expected_bases in classes.items():
                with self.subTest(path=relative_path, class_name=class_name):
                    self.assertEqual(actual[class_name], expected_bases)


if __name__ == "__main__":
    unittest.main()
