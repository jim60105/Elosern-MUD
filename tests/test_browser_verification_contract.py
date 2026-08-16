"""Repository contract tests for the WebClient verification gates (section 7.3).

These top-level tests assert the committed quality workflow installs Chromium
before any Python runner, runs the Node suite and the explicit browser command
before traceability evidence verification, keeps the Playwright dependency
locked, requires a supported Node version, and that the browser harness is
isolated, repeatable, and free of failure suppression or remote fixtures.
"""

from pathlib import Path
import re
import tomllib
import unittest

import yaml

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


class BrowserVerificationContractTests(unittest.TestCase):
    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_workflow_installs_chromium_runs_node_and_browser_before_evidence(self):
        workflow = yaml.safe_load(_read(".github/workflows/quality-gate.yml"))
        jobs = workflow["jobs"]
        preflight = jobs["preflight"]
        preflight_names = [step["name"] for step in preflight["steps"]]
        preflight_steps = {step["name"]: step for step in preflight["steps"]}

        self.assertLess(
            preflight_names.index("Run Node DOM-independent test suite"),
            preflight_names.index("Compute browser shard matrix"),
            "the Node suite runs in preflight before any execution job starts",
        )
        self.assertIn(
            "playwright install --with-deps chromium",
            jobs["browser"]["steps"][
                [step["name"] for step in jobs["browser"]["steps"]].index(
                    "Install Chromium for browser acceptance"
                )
            ]["run"],
        )
        self.assertEqual(
            preflight_steps["Run Node DOM-independent test suite"]["run"],
            "node --test web/static/webclient/js/tests/*.test.js",
        )

        browser_jobs = [job for name, job in jobs.items() if name.startswith("browser")]
        browser_steps = browser_jobs[0]["steps"]
        checkout_paths = [
            step.get("with", {}).get("path")
            for step in browser_steps
            if step["name"].startswith("Check out repository")
        ]
        self.assertEqual(checkout_paths, ["w-a", "w-b"])
        browser_run = next(
            step for step in browser_steps
            if step["name"].startswith("Run browser shard")
        )["run"]
        self.assertIn("coverage run", browser_run)
        self.assertIn("matrix.files_a", browser_run)
        self.assertIn("matrix.files_b", browser_run)

        gate_names = [step["name"] for step in jobs["gate"]["steps"]]
        self.assertLess(
            gate_names.index("Verify successful requirement execution"),
            gate_names.index("Enforce aggregate coverage threshold"),
        )
        gate_steps = {step["name"]: step for step in jobs["gate"]["steps"]}
        self.assertIn(
            "coverage report --fail-under=80",
            gate_steps["Enforce aggregate coverage threshold"]["run"],
        )

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_browser_evidence_uses_a_per_shard_evidence_path(self):
        workflow = yaml.safe_load(_read(".github/workflows/quality-gate.yml"))
        browser_jobs = [job for name, job in workflow["jobs"].items() if name.startswith("browser")]
        browser_step = next(
            step for step in browser_jobs[0]["steps"]
            if step["name"].startswith("Run browser shard")
        )
        self.assertIn(
            "evidence.browser-shard-",
            browser_step["env"].get("OPENSPEC_TEST_EVIDENCE", ""),
        )
        self.assertIn("COVERAGE_FILE", browser_step["env"])
        browser_run = browser_step["run"]
        self.assertNotIn("--parallel", browser_run)
        self.assertNotIn("discover -s web/tests/browser", browser_run)
        self.assertIn(
            'COVERAGE_FILE="coverage-browser-shard-${{ matrix.index }}-p1"',
            browser_run,
        )
        self.assertIn(
            'OPENSPEC_TEST_EVIDENCE="evidence.browser-shard-${{ matrix.index }}-p1.jsonl"',
            browser_run,
        )
        self.assertIn(
            'COVERAGE_FILE="coverage-browser-shard-${{ matrix.index }}-p2"',
            browser_run,
        )
        self.assertIn(
            'OPENSPEC_TEST_EVIDENCE="evidence.browser-shard-${{ matrix.index }}-p2.jsonl"',
            browser_run,
        )
        self.assertIn('wait "$pid1" || status1=$?', browser_run)
        self.assertIn('wait "$pid2" || status2=$?', browser_run)
        self.assertIn(
            "cat w-a/evidence.browser-shard-${{ matrix.index }}-p1.jsonl "
            "w-b/evidence.browser-shard-${{ matrix.index }}-p2.jsonl "
            "> evidence.browser-shard-${{ matrix.index }}.jsonl",
            browser_run,
        )
        self.assertIn(
            'test "$status1" -eq 0 && test "$status2" -eq 0',
            browser_run,
        )

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_existing_gates_remain_required_without_failure_suppression(self):
        workflow = yaml.safe_load(_read(".github/workflows/quality-gate.yml"))
        jobs = workflow["jobs"]
        required = {
            "preflight": (
                "Validate OpenSpec",
                "Validate static requirement traceability",
            ),
            "evennia": ("Run evennia shard ${{ matrix.index }}",),
            "top-level": ("Run top-level regression suite with coverage",),
            "gate": (
                "Verify successful requirement execution",
                "Verify coverage source roots",
                "Enforce aggregate coverage threshold",
                "Upload coverage reports to Codecov",
            ),
        }
        for job_name, names in required.items():
            step_names = [step["name"] for step in jobs[job_name]["steps"]]
            for required_name in names:
                self.assertIn(required_name, step_names, f"gate {required_name!r} is missing")
        combined = " ".join(
            step.get("run", "") + str(step.get("uses", ""))
            for job in jobs.values()
            for step in job["steps"]
        )
        self.assertNotIn("continue-on-error", combined)
        self.assertNotIn("|| true", combined)

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_playwright_is_a_locked_dev_dependency(self):
        pyproject = tomllib.loads(_read("pyproject.toml"))
        dev = pyproject["dependency-groups"]["dev"]
        self.assertTrue(
            any("playwright" in entry for entry in dev),
            "playwright must be a synchronized dev dependency",
        )
        lock = _read("uv.lock")
        self.assertIn('name = "playwright"', lock)

    @covers_requirement(
        "webclient-browser-verification::dom-independent-client-behavior-has-an-executable-node-test-gate"
    )
    def test_node_suite_requires_no_npm_package(self):
        npm_require = re.compile(
            r'require\(\s*["\'](?!node:|\.{1,2}/)[^"\']+["\']'
        )
        for path in (REPO_ROOT / "web/static/webclient/js").rglob("*.js"):
            source = path.read_text(encoding="utf-8")
            match = npm_require.search(source)
            self.assertIsNone(
                match,
                f"{path} must not require an npm package (found {match.group(0) if match else None})",
            )
        self.assertFalse((REPO_ROOT / "package.json").exists())

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_harness_uses_dynamic_ports_and_temporary_roots(self):
        fixtures_source = _read("web/tests/browser/fixtures.py")
        self.assertIn("allocate_ports", fixtures_source)
        self.assertIn("tempfile.mkdtemp", fixtures_source)
        self.assertIn("ELOSERN_BROWSER_DB", fixtures_source)
        self.assertIn("ELOSERN_BROWSER_HTTP_PORT", fixtures_source)
        # The word 4001 appears only in the comment stating the runtime never
        # collides with the developer ports; the code must not bind it.
        self.assertNotIn("bind((\"127.0.0.1\", 4001", fixtures_source)
        self.assertNotIn('= 4001', fixtures_source)

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-uses-an-isolated-managed-evennia-runtime"
    )
    def test_harness_owns_and_stops_only_its_processes(self):
        harness_source = _read("web/tests/browser/harness.py")
        self.assertIn("recorded portal/server PIDs", harness_source)
        self.assertIn("os.kill(pid, signal.SIGTERM)", harness_source)
        self.assertIn("os.kill(pid, signal.SIGKILL)", harness_source)
        self.assertIn("runtime.cleanup()", harness_source)

    @covers_requirement(
        "webclient-browser-verification::browser-tests-are-localhost-only-and-deterministic"
    )
    def test_browser_helpers_block_non_local_requests(self):
        helpers_source = _read("web/tests/browser/browser_helpers.py")
        self.assertIn("guard_local_only", helpers_source)
        self.assertIn("abort", helpers_source)

    @covers_requirement(
        "webclient-browser-verification::browser-tests-are-localhost-only-and-deterministic"
    )
    def test_no_browser_fixture_invokes_external_services(self):
        for path in (REPO_ROOT / "web/tests/browser").glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("ollama", source.lower())
            self.assertNotIn("stable_diffusion", source.lower())
            self.assertNotIn("sd-webui", source.lower())

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
    )
    def test_workflow_pins_a_supported_node_version(self):
        workflow = yaml.safe_load(_read(".github/workflows/quality-gate.yml"))
        steps = {
            step["name"]: step for step in workflow["jobs"]["preflight"]["steps"]
        }
        self.assertEqual(
            steps["Install Node.js"]["with"]["node-version"], "24"
        )


if __name__ == "__main__":
    unittest.main()
