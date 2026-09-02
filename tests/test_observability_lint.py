"""Contract tests for the observability lint gate (top-level, stdlib unittest)."""

import ast
import json
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.observability_lint import FREEZE_PATH, REPO_ROOT, _scan_file, check_repo


def scan(source: str, rel: str = "world/rules/sample.py") -> list[tuple[str, int]]:
    report = _scan_file(rel, textwrap.dedent(source))
    return [(item.rule, item.line) for item in report.violations]


class R1Tests(unittest.TestCase):
    def test_each_bypass_form_is_caught(self) -> None:
        forms = [
            "from evennia import logger\n",
            "from evennia.utils import logger\n",
            "from evennia.utils import logger as log\n",
            "from evennia.utils.logger import log_warn\n",
            "import evennia.utils.logger\n",
            "import logging\n",
        ]
        for source in forms:
            with self.subTest(source=source.strip()):
                rules = [rule for rule, _ in scan(source)]
                self.assertIn("R1", rules)

    def test_attribute_access_after_root_import(self) -> None:
        rules = scan("import evennia\n\nevennia.logger.log_info('x')\n")
        self.assertIn("R1", [rule for rule, _ in rules])

    def test_clean_imports_pass(self) -> None:
        self.assertEqual(
            scan("from world.observability import log_warn\n\nlog_warn('e', context={})\n"),
            [],
        )

    def test_reasoned_exemption_on_import_line(self) -> None:
        rules = scan(
            "from evennia import logger  # observability: ignore R1: bootstrap only\n"
        )
        self.assertEqual(rules, [])

    def test_unparseable_file_is_a_violation(self) -> None:
        rules = scan("def broken(:\n")
        self.assertEqual([rule for rule, _ in rules], ["parse"])

    def test_facade_package_is_whitelisted(self) -> None:
        rules = scan(
            "from evennia.utils import logger\n", rel="world/observability/api.py"
        )
        self.assertEqual(rules, [])


class R2Tests(unittest.TestCase):
    ADOPT = "from world.observability import log_warn\n\n"

    def test_silent_handler_in_adopter_fails(self) -> None:
        source = self.ADOPT + "try:\n    f()\nexcept Exception:\n    pass\n"
        self.assertIn("R2", [rule for rule, _ in scan(source)])

    def test_legacy_non_adopter_is_outside_r2(self) -> None:
        source = "try:\n    f()\nexcept Exception:\n    pass\n"
        self.assertEqual(scan(source), [])

    def test_raise_in_with_block_satisfies(self) -> None:
        source = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception:\n    with lock:\n        raise\n"
        )
        self.assertEqual(scan(source), [])

    def test_facade_call_in_handler_satisfies(self) -> None:
        source = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception as exc:\n    log_warn('e', exc=exc, context={})\n"
        )
        self.assertEqual(scan(source), [])

    def test_nested_function_def_without_raise_does_not_satisfy(self) -> None:
        source = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception:\n"
            "    def helper():\n        raise\n"
        )
        self.assertIn("R2", [rule for rule, _ in scan(source)])

    def test_reasoned_exemption_counts_and_passes(self) -> None:
        source = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception:  # observability: ignore R2: bounded cache reset\n"
            "    pass\n"
        )
        report = _scan_file("world/rules/sample.py", textwrap.dedent(source))
        self.assertEqual(report.violations, ())
        self.assertEqual(report.exemptions, 1)

    def test_empty_reason_is_a_violation(self) -> None:
        source = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception:  # observability: ignore R2:\n    pass\n"
        )
        self.assertIn("R2", [rule for rule, _ in scan(source)])

    def test_package_form_import_is_an_adopter(self) -> None:
        # ``from world import observability`` reaches the same facade; the
        # file must be inside R2/R3 scope, not escape it.
        source = (
            "from world import observability\n\n"
            "try:\n    f()\nexcept Exception:\n    pass\n"
        )
        rules = [rule for rule, _ in scan(source)]
        self.assertIn("R2", rules)
        aliased = (
            "from world import observability as obs\n\nobs.log_info('e')\n"
        )
        self.assertIn("R3", [rule for rule, _ in scan(aliased)])
        satisfied = (
            "from world import observability as obs\n\n"
            "obs.log_info('e', context={'a': 1})\n"
        )
        self.assertEqual(scan(satisfied), [])


class R3Tests(unittest.TestCase):
    ADOPT = "from world.observability import log_info, log_error\n\n"

    def test_contextless_call_fails(self) -> None:
        self.assertIn("R3", [rule for rule, _ in scan(self.ADOPT + "log_info('e')\n")])

    def test_literal_none_context_fails(self) -> None:
        self.assertIn(
            "R3", [rule for rule, _ in scan(self.ADOPT + "log_info('e', context=None)\n")]
        )

    def test_context_passes(self) -> None:
        self.assertEqual(scan(self.ADOPT + "log_info('e', context={'a': 1})\n"), [])

    def test_log_error_needs_exc_or_raise(self) -> None:
        source = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception as exc:\n    log_error('e', context={'a': 1})\n"
        )
        self.assertIn("R3", [rule for rule, _ in scan(source)])
        with_exc = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception as exc:\n"
            "    log_error('e', exc=exc, context={'a': 1})\n"
        )
        self.assertEqual(scan(with_exc), [])
        re_raise = (
            self.ADOPT
            + "try:\n    f()\nexcept Exception:\n"
            "    log_error('e', context={'a': 1})\n    raise\n"
        )
        self.assertEqual(scan(re_raise), [])

    def test_unknown_rule_id_is_flagged(self) -> None:
        source = "# observability: ignore R9: waiting on refactor\n"
        self.assertIn("R3", [rule for rule, _ in scan(source)])


class FreezeRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="obs-lint-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.tmp = Path(self._tmp)

    def _repo(self, files: dict[str, str], freeze: list[str]) -> Path:
        tmp = self.tmp
        for rel, source in files.items():
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(source), encoding="utf-8")
        (tmp / FREEZE_PATH).parent.mkdir(parents=True, exist_ok=True)
        (tmp / FREEZE_PATH).write_text(json.dumps(freeze), encoding="utf-8")
        return tmp

    def test_frozen_r1_file_passes_but_zombie_fails(self) -> None:
        files = {"world/rules/debt.py": "from evennia import logger\n"}
        report = check_repo(self._repo(files, ["world/rules/debt.py"]))
        self.assertTrue(report.ok, msg=report.violations)
        # Migrate the file (keep a facade call so R2/R3 stay silent-clean):
        files["world/rules/debt.py"] = (
            "from world.observability import log_warn\n\nlog_warn('e', context={})\n"
        )
        report = check_repo(self._repo(files, ["world/rules/debt.py"]))
        self.assertIn(
            "stale entry", " ".join(item.message for item in report.violations)
        )

    def test_freeze_suppresses_r1_only(self) -> None:
        files = {
            "world/rules/debt.py": (
                "from evennia import logger\n"
                "from world.observability import log_warn\n\n"
                "try:\n    f()\nexcept Exception:\n    pass\n"
                "log_warn('e')\n"
            )
        }
        report = check_repo(self._repo(files, ["world/rules/debt.py"]))
        rules = {item.rule for item in report.violations}
        self.assertNotIn("R1", rules)
        self.assertIn("R2", rules)
        self.assertIn("R3", rules)

    def test_duplicate_and_missing_entries_fail(self) -> None:
        report = check_repo(
            self._repo(
                {"world/rules/clean.py": "x = 1\n"},
                ["world/rules/gone.py", "world/rules/gone.py"],
            )
        )
        messages = " ".join(item.message for item in report.violations)
        self.assertIn("non-existent path", messages)
        self.assertIn("duplicate entry", messages)

    def test_out_of_scope_existing_entry_is_a_violation(self) -> None:
        # An existing file outside the scanned production set (tests, tools)
        # can never carry detectable R1 debt — freezing it defeats the
        # shrink-only ratchet, so it must fail.
        files = {
            "world/rules/debt.py": "from evennia import logger\n",
            "tests/helpers/fixture.py": "x = 1\n",
        }
        report = check_repo(
            self._repo(files, ["world/rules/debt.py", "tests/helpers/fixture.py"])
        )
        messages = " ".join(item.message for item in report.violations)
        self.assertIn("not a scanned production file", messages)


class RepoIntegrationTests(unittest.TestCase):
    def test_repository_passes_with_committed_freeze(self) -> None:
        report = check_repo(REPO_ROOT)
        self.assertTrue(report.ok, msg=report.violations[:20])

    def test_freeze_manifest_equals_generated_r1_inventory(self) -> None:
        from tools.observability_lint import _production_files, _scan_r1, _whitelisted

        debt: set[str] = set()
        for path in _production_files(REPO_ROOT):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if _whitelisted(rel):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            if _scan_r1(tree, rel):
                debt.add(rel)
        committed = set(
            json.loads((REPO_ROOT / FREEZE_PATH).read_text(encoding="utf-8"))
        )
        # Every file with live R1 debt must be frozen (entries for migrated
        # files would fail check_repo as zombies, covered by the test above).
        self.assertEqual(
            sorted(debt - committed),
            [],
            msg="files with R1 debt must be listed in the freeze manifest",
        )


if __name__ == "__main__":
    unittest.main()
