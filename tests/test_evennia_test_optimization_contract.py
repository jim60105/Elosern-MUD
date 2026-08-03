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
        steps = {step["name"]: step for step in workflow["jobs"]["quality-gate"]["steps"]}
        browser = steps["Run browser acceptance suite"]
        evennia = steps["Run full non-browser Evennia suite with coverage"]
        top_level = steps["Run top-level regression suite with coverage"]

        self.assertEqual(browser["env"]["COVERAGE_FILE"], ".coverage.browser")
        self.assertIn("unittest discover -s web/tests/browser -t .", browser["run"])
        self.assertNotIn("--parallel", browser["run"])
        self.assertEqual(evennia["env"]["COVERAGE_FILE"], ".coverage.evennia")
        self.assertIn("commands server typeclasses world web.webclient", evennia["run"])
        self.assertIn("--noinput", evennia["run"])
        self.assertNotIn(" commands server typeclasses web world", evennia["run"])
        self.assertEqual(top_level["env"]["COVERAGE_FILE"], ".coverage.top-level")
        self.assertEqual(
            steps["Combine coverage data"]["run"],
            "uv run --locked coverage combine .coverage.evennia .coverage.browser .coverage.top-level",
        )
        for step in (browser, evennia, top_level):
            self.assertEqual(
                step["env"]["OPENSPEC_TEST_EVIDENCE"],
                "${{ env.OPENSPEC_TEST_EVIDENCE }}",
            )

        all_commands = [step.get("run", "") for step in workflow["jobs"]["quality-gate"]["steps"]]
        browser_discovery = "unittest discover -s web/tests/browser -t ."
        self.assertEqual(sum(command.count(browser_discovery) for command in all_commands), 1)
        self.assertFalse(
            any(
                "evennia test" in command
                and (" typeclasses web world" in command or command.rstrip().endswith(" web"))
                for command in all_commands
            )
        )


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
