"""Behavioral contracts for the OMP Evennia test guard extension.

The guard ships as a TypeScript extension (``.omp/extensions/evennia-test-guard``)
loaded by the OMP runtime. Following the subprocess node-parity precedent from
``web/webclient/presentation/tests/test_gallery_panel.py``, these tests drive the
real extension module under Node 24 (type-stripped natively) through a tiny fake
``ExtensionAPI`` harness, and exercise the Python count runner through a bounded
``evennia test --testrunner=...CountOnlyRunner`` subprocess against the project's
own test settings.

Everything is deterministic and offline: the guard half never executes a real
discovery (the fake ``pi.exec`` returns canned results), and the count-runner
half discovers a two-test module without touching any database.

Scope note: the fake harness certifies the guard's own logic (detection,
discovery-command construction, marker parsing, block/allow decisions). The
60-second discovery timeout is passed as an option and its enforcement belongs
to the OMP runtime's ``pi.exec``, which the fake cannot exercise; runtime
integration was manually verified before the extension landed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_DIR = REPO_ROOT / ".omp" / "extensions" / "evennia-test-guard"
GUARD_ENTRY = GUARD_DIR / "index.ts"
COUNT_RUNNER_MODULE = "omp_evennia_count_runner.CountOnlyRunner"
COUNT_MARKER = "__OMP_EVENNIA_TEST_COUNT_V1__="

#: Cheap label used by the bounded count-runner subprocess: two tests, no DB.
COUNT_PROBE_LABEL = "tests.test_coverage_roots"

#: Re-export appended to a byte copy of index.ts so the harness can reach the
#: internal classifier and the exported default extension function.
_HARNESS_EXPORT = "export { analyzeCommand, MAX_TESTS };\n"

_DRIVER_JS = """\
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const guard = await import(pathToFileURL(process.argv[3]).href);

const results = [];

for (const testCase of cases) {
  const execCalls = [];
  const notifications = [];
  let handler;

  const api = {
    on: (_event, fn) => {
      handler = fn;
    },
    exec: async (command, args, options) => {
      execCalls.push({ command, args, options });
      const discovery = testCase.discovery ?? {
        code: 0,
        stdout: "",
        stderr: "",
      };
      if (discovery.throw) {
        throw new Error(discovery.throw);
      }
      return {
        code: discovery.code ?? 0,
        stdout: discovery.stdout ?? "",
        stderr: discovery.stderr ?? "",
      };
    },
  };

  guard.default(api);

  const ctx = {
    cwd: testCase.cwd ?? "/repo",
    hasUI: testCase.hasUI ?? false,
    ui: {
      notify: (message, level) => {
        notifications.push({ message, level });
      },
    },
  };

  let decision = null;
  let error = null;

  try {
    const outcome = await handler(
      {
        toolName: testCase.toolName ?? "bash",
        input: testCase.input ?? {},
      },
      ctx,
    );
    decision = outcome === undefined ? null : outcome;
  } catch (cause) {
    error = String(cause);
  }

  results.push({ id: testCase.id, decision, execCalls, notifications, error });
}

process.stdout.write(JSON.stringify({ max: guard.MAX_TESTS, results }));
"""


def _shutil_require_node() -> str:
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is required to exercise the guard extension")
    parts = (
        subprocess.run([node, "--version"], text=True, capture_output=True, check=True)
        .stdout.strip().lstrip("v").split(".")
    )
    major, minor = int(parts[0]), int(parts[1])
    if (int(major), int(minor)) < (24, 0):
        raise unittest.SkipTest(
            f"node >= 24 is required for native TypeScript type-stripping (found v{major}.{minor})"
        )
    return node


class _GuardHarnessTestCase(unittest.TestCase):
    """Base that stages the Node harness once per class."""

    harness_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.node = _shutil_require_node()
        cls.harness_dir = Path(tempfile.mkdtemp(prefix="evennia-test-guard-harness-"))

        source = GUARD_ENTRY.read_text(encoding="utf-8")
        impl = cls.harness_dir / "guard_impl.ts"
        impl.write_text(source + _HARNESS_EXPORT, encoding="utf-8")

        driver = cls.harness_dir / "driver.mjs"
        driver.write_text(_DRIVER_JS, encoding="utf-8")

        cls.impl_path = str(impl)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.harness_dir, ignore_errors=True)

    def _run_cases(self, cases: list[dict]) -> dict:
        cases_file = self.harness_dir / "cases.json"
        cases_file.write_text(json.dumps(cases), encoding="utf-8")

        result = subprocess.run(
            [self.node, str(self.harness_dir / "driver.mjs"), str(cases_file), self.impl_path],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, f"node harness failed: {result.stderr}")
        payload = json.loads(result.stdout)
        by_id = {entry["id"]: entry for entry in payload["results"]}
        self.assertEqual(len(by_id), len(cases))
        return payload["max"], by_id

    @staticmethod
    def _exec_script(exec_call: dict) -> str:
        return exec_call["args"][1]

    @staticmethod
    def _marker_discovery(count: int | str) -> dict:
        value = f"{count}"
        return {"code": 0, "stdout": f"{COUNT_MARKER}{value}", "stderr": ""}


class GuardInterceptionTests(_GuardHarnessTestCase):
    @covers_requirement("evennia-test-guard::guard-intercepts-evennia-test-commands-before-execution")
    def test_only_bash_evennia_test_invocations_reach_the_guard(self):
        """Non-bash tools and non-test commands pass through with zero discovery work."""
        _, by_id = self._run_cases(
            [
                {"id": "other-tool", "toolName": "read", "input": {"command": "evennia test world.tests"}},
                {"id": "no-test-text", "toolName": "bash", "input": {"command": "uv run --locked evennia start"}},
                {"id": "unrelated", "toolName": "bash", "input": {"command": "git status"}},
                {
                    "id": "intercepted",
                    "toolName": "bash",
                    "input": {"command": "evennia test world.tests"},
                    "discovery": self._marker_discovery(42),
                },
            ]
        )

        for case_id in ("other-tool", "no-test-text", "unrelated"):
            entry = by_id[case_id]
            self.assertIsNone(entry["error"])
            self.assertIsNone(entry["decision"], f"{case_id} must not produce a decision")
            self.assertEqual(entry["execCalls"], [], f"{case_id} must not spawn discovery")

        # The intercepted invocation performs count-only discovery first and is
        # allowed only afterwards (decision None = allow the original command).
        intercepted = by_id["intercepted"]
        self.assertIsNone(intercepted["error"])
        self.assertIsNone(intercepted["decision"])
        self.assertEqual(len(intercepted["execCalls"]), 1, "exactly one discovery subprocess")
        call = intercepted["execCalls"][0]
        self.assertEqual(call["command"], "bash")
        self.assertEqual(call["args"][0], "-lc")
        self.assertIn(f"--testrunner={COUNT_RUNNER_MODULE}", self._exec_script(call))
        self.assertNotIn("evennia test world.tests\n", self._exec_script(call) + "\n")

    @covers_requirement("evennia-test-guard::guard-intercepts-evennia-test-commands-before-execution")
    def test_inert_quoted_mentions_are_ignored_but_composite_mentions_stay_guarded(self):
        """Commit messages/grep patterns merely mentioning the words run untouched."""
        _, by_id = self._run_cases(
            [
                {
                    "id": "commit-message",
                    "input": {"command": 'git commit -m "docs: align evennia test examples"'},
                },
                {"id": "grep-pattern", "input": {"command": 'grep -rn "evennia test" docs/'}},
                {"id": "echo-line", "input": {"command": "echo 'run evennia test first'"}},
                {
                    "id": "composite",
                    "input": {"command": "git commit -m 'evennia test docs' && evennia test world.tests"},
                    "discovery": self._marker_discovery(7),
                },
            ]
        )

        for case_id in ("commit-message", "grep-pattern", "echo-line"):
            entry = by_id[case_id]
            self.assertIsNone(entry["error"])
            self.assertIsNone(entry["decision"], f"{case_id} is inert and must not be decided")
            self.assertEqual(entry["execCalls"], [], f"{case_id} must not spawn discovery")

        composite = by_id["composite"]
        # The spec allows counting or failing closed here; this guard blocks the
        # non-cd `git commit` prefix fail-closed — either way the mention never
        # runs unguarded.
        self.assertIsNotNone(composite["decision"], "composite mention must not pass unguarded")
        self.assertTrue(composite["decision"]["block"])
        self.assertEqual(composite["execCalls"], [], "nothing runs before the decision")


class RecognizedInvocationFormTests(_GuardHarnessTestCase):
    @covers_requirement("evennia-test-guard::recognized-invocation-forms")
    def test_supported_grammar_counts_with_the_same_runner_wrapper(self):
        """uv/poetry wrappers, run flags, and cd prefixes are all supported forms."""
        commands = {
            "plain": "evennia test world.tests",
            "uv": "uv run evennia test world.tests",
            "uv-locked": "uv run --locked evennia test world.tests",
            "poetry": "poetry run evennia test world.tests",
            "cd": "cd mygame && evennia test world.tests",
            "cd-cd": "cd projects && cd mygame && evennia test world.tests",
        }
        cases = [
            {"id": case_id, "input": {"command": command}, "discovery": self._marker_discovery(3)}
            for case_id, command in commands.items()
        ]
        _, by_id = self._run_cases(cases)

        for case_id, command in commands.items():
            entry = by_id[case_id]
            self.assertIsNone(entry["error"])
            self.assertIsNone(entry["decision"], f"{command!r} is supported and must be allowed")
            self.assertEqual(len(entry["execCalls"]), 1, f"{command!r} must count first")

            script = self._exec_script(entry["execCalls"][0])

            # Discovery is the count-only substitution of the original command...
            self.assertIn(f"--testrunner={COUNT_RUNNER_MODULE}", script)
            self.assertIn("world.tests", script)
            self.assertNotIn("evennia test world.tests", script, "the real runner is never replayed")

            # ...wrapped by the same prefix as the original invocation.
            expected_prefix = command.replace("evennia test", f"evennia test --testrunner={COUNT_RUNNER_MODULE}")
            self.assertIn(expected_prefix, script)

            # cd prefixes survive into the replayed discovery command.
            for prefix in command.split("&& ")[:-1]:
                self.assertIn(prefix.strip(), script)

    @covers_requirement("evennia-test-guard::count-only-discovery-without-executing-tests")
    def test_discovery_runs_directly_with_preserved_env_and_extension_pythonpath(self):
        """Discovery is a direct subprocess keeping caller env + runner importable."""
        _, by_id = self._run_cases(
            [
                {
                    "id": "env",
                    "cwd": "/srv/game",
                    "input": {
                        "command": "uv run --locked evennia test world.tests",
                        "cwd": "sub",
                        "env": {"MUD_TEST_SETTINGS": "1", "BAD-NAME": "ignored", "COUNT": 5},
                    },
                    "discovery": self._marker_discovery(2),
                }
            ]
        )
        entry = by_id["env"]
        self.assertIsNone(entry["error"])
        self.assertIsNone(entry["decision"])
        self.assertEqual(len(entry["execCalls"]), 1)

        call = entry["execCalls"][0]
        # Direct exec through the extension runtime, never back through Bash.
        self.assertEqual(call["command"], "bash")

        options = call["options"]
        self.assertEqual(options["cwd"], os.path.join("/srv/game", "sub"), "relative cwd resolved against session cwd")
        self.assertLessEqual(options["timeout"], 60_000, "discovery timeout is bounded")

        script = self._exec_script(call)
        self.assertIn("set -e", script)
        # Caller-supplied environment is preserved verbatim...
        self.assertIn("export MUD_TEST_SETTINGS='1'", script)
        # ...while invalid identifier keys and non-string values are dropped.
        self.assertNotIn("BAD-NAME", script)
        self.assertNotIn("export COUNT=", script)
        # The extension directory is injected into PYTHONPATH so the count
        # runner module is importable ('.' absorbs evennia's sys.path rewrite).
        self.assertRegex(
            script,
            r"export PYTHONPATH='\.:" + re.escape(str(self.harness_dir)) + r"(:[^']*)?'",
        )
        # The count-only runner replaces plain `evennia test`.
        self.assertIn("uv run --locked evennia test --testrunner=omp_evennia_count_runner.CountOnlyRunner", script)


class CountRunnerSubprocessTests(unittest.TestCase):
    @covers_requirement("evennia-test-guard::count-only-discovery-without-executing-tests")
    def test_count_runner_discovers_marker_without_touching_databases(self):
        """The real CountOnlyRunner emits the marker and never creates databases."""
        env = os.environ.copy()
        env["MUD_TEST_SETTINGS"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(GUARD_DIR)])

        test_db = REPO_ROOT / "server" / "db" / "evennia-test.sqlite3"
        game_db = REPO_ROOT / "server" / "db" / "evennia.db3"
        # The retained test database may legitimately pre-exist from earlier
        # --keepdb runs; the contract is that count-only discovery never
        # creates or modifies it, so snapshot the before-state.
        test_db_existed = test_db.exists()
        test_db_mtime_ns = test_db.stat().st_mtime_ns if test_db_existed else None
        game_db_mtime_ns = game_db.stat().st_mtime_ns if game_db.exists() else None

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "evennia",
                "test",
                "--settings",
                "test_settings.py",
                "--keepdb",
                f"--testrunner={COUNT_RUNNER_MODULE}",
                COUNT_PROBE_LABEL,
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, combined[-3000:])

        marker_lines = [line for line in combined.splitlines() if COUNT_MARKER in line]
        self.assertEqual(len(marker_lines), 1, f"exactly one marker expected, got: {marker_lines}")
        _, _, reported = marker_lines[0].partition(COUNT_MARKER)
        self.assertTrue(reported.isdigit() and int(reported) > 0, f"unexpected marker value: {reported!r}")

        # No database is created or modified and no test method can have run.
        self.assertEqual(
            test_db.exists(), test_db_existed,
            "count-only discovery must not create the test database",
        )
        if test_db_mtime_ns is not None:
            self.assertEqual(
                test_db.stat().st_mtime_ns, test_db_mtime_ns,
                "count-only discovery must not modify the test database",
            )
        if game_db_mtime_ns is not None:
            self.assertEqual(game_db.stat().st_mtime_ns, game_db_mtime_ns, "game database must be untouched")


class MarkerProtocolTests(_GuardHarnessTestCase):
    @covers_requirement("evennia-test-guard::discovery-count-marker-protocol")
    def test_last_marker_wins_and_missing_or_invalid_marker_blocks(self):
        """Combined output is parsed from the final marker; garbage blocks closed."""
        _, by_id = self._run_cases(
            [
                {
                    "id": "last-wins",
                    "input": {"command": "evennia test world.tests"},
                    "hasUI": True,
                    "discovery": {
                        "code": 0,
                        "stdout": (
                            f"{COUNT_MARKER}480\nsome runner noise\n{COUNT_MARKER}42\n"
                        ),
                        "stderr": "",
                    },
                },
                {
                    "id": "missing",
                    "input": {"command": "evennia test world.tests"},
                    "discovery": {"code": 0, "stdout": "Found 3 test(s).\n", "stderr": ""},
                },
                {
                    "id": "unsafe-integer",
                    "input": {"command": "evennia test world.tests"},
                    "discovery": self._marker_discovery("99" * 40),
                },
                {
                    "id": "non-numeric",
                    "input": {"command": "evennia test world.tests"},
                    "discovery": {"code": 0, "stdout": f"{COUNT_MARKER}NaN\n", "stderr": ""},
                },
            ]
        )

        last_wins = by_id["last-wins"]
        self.assertIsNone(last_wins["error"])
        self.assertIsNone(last_wins["decision"], "final marker 42 <= max must allow")
        self.assertEqual(
            [note["message"] for note in last_wins["notifications"]],
            ["Evennia test guard: 42/100 tests — allowed"],
            "UI must surface the last marker's count",
        )

        missing = by_id["missing"]
        self.assertTrue(missing["decision"]["block"])
        reason = missing["decision"]["reason"]
        self.assertIn("could not determine", reason)
        self.assertIn("blocked", reason.lower())
        self.assertIn("Run Focus Test", reason)

        # A non-numeric marker never matches the digit grammar, so it is also a
        # failed discovery (missing marker), and an out-of-safe-range digit run
        # trips the safe-integer check. Both must block.
        for case_id in ("unsafe-integer", "non-numeric"):
            entry = by_id[case_id]
            self.assertTrue(entry["decision"]["block"], f"{case_id} marker must block")
        self.assertIn("invalid test count", by_id["unsafe-integer"]["decision"]["reason"])
        self.assertIn("could not determine", by_id["non-numeric"]["decision"]["reason"])


class CountBoundaryTests(_GuardHarnessTestCase):
    @covers_requirement("evennia-test-guard::allow-at-or-below-the-maximum")
    def test_counts_at_or_below_maximum_are_allowed_with_ui_notice(self):
        """0, 42 and exactly MAX tests run unchanged; the UI reports n/MAX."""
        max_, by_id = self._run_cases(
            [
                {
                    "id": f"count-{count}",
                    "input": {"command": f"evennia test world.tests.TestSomething{n}"},
                    "hasUI": True,
                    "discovery": self._marker_discovery(count),
                }
                for n, count in ((0, 0), (1, 42), (2, 100))
            ]
        )
        self.assertEqual(max_, 100, "the guard's documented maximum")

        for count in (0, 42, 100):
            entry = by_id[f"count-{count}"]
            self.assertIsNone(entry["error"])
            self.assertIsNone(entry["decision"], f"{count} tests must be allowed unchanged")
            self.assertEqual([], [c for c in entry["execCalls"][1:]], "only one discovery run")
            self.assertEqual(
                [note["message"] for note in entry["notifications"]],
                [f"Evennia test guard: {count}/100 tests — allowed"],
            )

    @covers_requirement("evennia-test-guard::block-above-the-maximum-with-run-focus-test-guidance")
    def test_counts_above_maximum_block_with_focus_guidance(self):
        """101 and 480 block, naming count, max, Run Focus Test, and narrowing."""
        _, by_id = self._run_cases(
            [
                {
                    "id": f"count-{count}",
                    "input": {"command": "evennia test" if count == 480 else "evennia test world"},
                    "discovery": self._marker_discovery(count),
                }
                for count in (101, 480)
            ]
        )

        for count in (101, 480):
            entry = by_id[f"count-{count}"]
            self.assertIsNone(entry["error"])
            self.assertTrue(entry["decision"]["block"], f"{count} tests must block")
            reason = entry["decision"]["reason"]
            self.assertIn(str(count), reason, "reason states discovered count")
            self.assertIn("100", reason, "reason states the maximum")
            self.assertIn("Run Focus Test", reason)
            # Progressively narrowed label examples: package, class, method.
            self.assertIn("evennia test world.tests\n", reason)
            self.assertIn("world.tests.TestSomething\n", reason)
            self.assertIn("world.tests.TestSomething.test_specific_behavior", reason)
            self.assertIn("Do not retry", reason)


class FailClosedCompositionTests(_GuardHarnessTestCase):
    @covers_requirement("evennia-test-guard::fail-closed-policy-for-unsupported-shell-composition")
    def test_supported_single_command_is_not_blocked(self):
        """Control: the standalone supported form is never among the blocked set."""
        _, by_id = self._run_cases(
            [
                {
                    "id": "control",
                    "input": {"command": "uv run --locked evennia test world.tests"},
                    "discovery": self._marker_discovery(5),
                }
            ]
        )
        entry = by_id["control"]
        self.assertIsNone(entry["decision"])
        self.assertEqual(len(entry["execCalls"]), 1)

    @covers_requirement("evennia-test-guard::fail-closed-policy-for-unsupported-shell-composition")
    def test_unsupported_shell_composition_blocks_fail_closed(self):
        """Every mentioned-but-unprovable construct blocks with an actionable reason."""
        constructs = {
            "semicolon": "evennia test world.tests; echo done",
            "pipe": "evennia test world.tests | tee out.log",
            "redirect": "evennia test world.tests > out.log",
            "stdin-redirect": "evennia test world.tests < labels.txt",
            "newline": "evennia test world.tests\necho done",
            "background": "evennia test world.tests &",
            "backtick": "echo `evennia test world.tests`",
            "dollar-paren": "echo $(evennia test world.tests)",
            "quoted-substitution": 'echo "hello $(evennia test world.tests)"',
            "bash-wrap": "bash -lc 'evennia test'",
            "trailing-segment": "evennia test world.tests && do-something",
            "leading-segment": "evennia test && echo after",
            "non-cd-prefix": "make lint && evennia test world.tests",
            "inline-env": "MUD_TEST_SETTINGS=1 evennia test world.tests",
            "caller-testrunner": "evennia test --testrunner=some.OtherRunner world.tests",
            "quoted-obscured": "evennia 'test' world.tests",
            "unterminated-quote": 'evennia test "world.tests',
            "trailing-empty-segment": "evennia test &&",
            "leading-empty-segment": "&& evennia test",
            "double-test": "evennia test a && evennia test b",
        }
        cases = [{"id": case_id, "input": {"command": command}} for case_id, command in constructs.items()]
        _, by_id = self._run_cases(cases)

        for case_id, command in constructs.items():
            entry = by_id[case_id]
            self.assertIsNone(entry["error"], command)
            self.assertIsNotNone(entry["decision"], f"{command!r} must not pass unguarded")
            self.assertTrue(entry["decision"]["block"], f"{command!r} must block fail-closed")
            self.assertEqual(entry["execCalls"], [], f"{command!r} must block before any discovery")
            reason = entry["decision"]["reason"]
            self.assertIn("blocked", reason.lower(), command)
            self.assertIn("Run Focus Test", reason, "reason points at a standalone focused command")

        self.assertIn("environment-assignment prefix", by_id["inline-env"]["decision"]["reason"])
        self.assertIn("env input", by_id["inline-env"]["decision"]["reason"])
        self.assertIn("--testrunner is reserved", by_id["caller-testrunner"]["decision"]["reason"])
        self.assertIn("final shell command", by_id["trailing-segment"]["decision"]["reason"])
        self.assertIn("background", by_id["background"]["decision"]["reason"])
        self.assertIn("command substitution", by_id["backtick"]["decision"]["reason"])
        self.assertIn("multi-line", by_id["newline"]["decision"]["reason"])
        self.assertIn("quoting", by_id["quoted-obscured"]["decision"]["reason"])


class DiscoveryFailureTests(_GuardHarnessTestCase):
    @covers_requirement("evennia-test-guard::discovery-failure-blocks-the-command")
    def test_discovery_crash_timeout_and_nonzero_exit_block_the_original_command(self):
        """Raise, non-zero exit, and (bounded) timeout all fail closed with output."""
        _, by_id = self._run_cases(
            [
                {
                    "id": "raise",
                    "input": {"command": "evennia test world.tests"},
                    "discovery": {"throw": "TimeoutError: discovery timed out after 60000ms"},
                },
                {
                    "id": "nonzero",
                    "input": {"command": "evennia test world.tests"},
                    "discovery": {
                        "code": 3,
                        "stdout": "",
                        "stderr": "ImproperlyConfigured: settings fail to import",
                    },
                },
            ]
        )

        crashed = by_id["raise"]
        self.assertTrue(crashed["decision"]["block"])
        self.assertIn("failed while discovering", crashed["decision"]["reason"])
        self.assertIn("discovery timed out", crashed["decision"]["reason"], "failure detail surfaced")
        self.assertIn("Run Focus Test", crashed["decision"]["reason"])

        nonzero = by_id["nonzero"]
        self.assertTrue(nonzero["decision"]["block"])
        self.assertIn("exited with code 3", nonzero["decision"]["reason"])
        self.assertIn("settings fail to import", nonzero["decision"]["reason"], "discovery output included")
        self.assertIn("was not executed", nonzero["decision"]["reason"])
        self.assertIn("Run Focus Test", nonzero["decision"]["reason"])


if __name__ == "__main__":
    unittest.main()
