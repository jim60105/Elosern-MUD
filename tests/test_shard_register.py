"""The shard registrar gives every test one CI owner without reshuffling the manifests."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools import shard_register


class ShardRegisterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self._write("world/alpha/tests/test_one.py", "def test_a(): pass\n")
        self._write("world/beta/tests/test_two.py", "def test_a(): pass\ndef test_b(): pass\n")
        self._write("server/conf/tests/test_boot.py", "def test_a(): pass\n")
        self._write("tests/test_contract.py", "def test_a(): pass\n")
        self._write(
            "web/tests/browser/test_shell.py",
            "class ShellTests:\n    def test_open(self): pass\n    def helper(self): pass\n"
            "class OtherTests:\n    def test_close(self): pass\n",
        )
        self._manifest(
            "evennia-shards",
            [
                {"index": 0, "name": "alpha", "labels": ["world.alpha.tests.test_one"]},
                {"index": 1, "name": "beta", "labels": ["world.beta.tests.test_two"]},
                {"index": 2, "name": "server", "labels": ["server"]},
            ],
        )
        self._manifest(
            "top-level-shards",
            [{"index": 0, "name": "top", "labels": ["tests.test_contract"]}],
            indent=1,
        )
        self._manifest(
            "browser-shards",
            [
                {
                    "index": 0,
                    "name": "packed",
                    "files_a": ["web.tests.browser.test_shell.ShellTests.test_open"],
                    "files_b": ["web.tests.browser.test_shell.OtherTests.test_close"],
                }
            ],
        )

    def _write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _manifest(self, name: str, shards: list, indent: int = 2) -> None:
        self._write(f".github/{name}.json", json.dumps({"shards": shards}, indent=indent) + "\n")

    def _shards(self, name: str) -> list:
        return json.loads((self.root / ".github" / f"{name}.json").read_text(encoding="utf-8"))["shards"]

    def _main(self, command: str) -> int:
        self.output = io.StringIO()
        with contextlib.redirect_stdout(self.output):
            return shard_register.main([command, "--root", str(self.root)])

    def _fix(self) -> int:
        return self._main("fix")

    def _check(self) -> int:
        return self._main("check")

    def test_a_consistent_tree_passes_and_is_left_byte_identical(self):
        before = {path: path.read_bytes() for path in (self.root / ".github").iterdir()}
        self.assertEqual(self._check(), 0)
        self.assertEqual(self._fix(), 0)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_check_reports_drift_without_writing(self):
        self._write("world/beta/tests/test_new.py", "def test_a(): pass\n")
        before = (self.root / ".github/evennia-shards.json").read_bytes()
        self.assertEqual(self._check(), 1)
        self.assertIn(shard_register.FIX_COMMAND, self.output.getvalue())
        self.assertEqual((self.root / ".github/evennia-shards.json").read_bytes(), before)

    def test_new_module_joins_the_shard_owning_its_directory_at_the_end(self):
        self._write("world/beta/tests/test_new.py", "def test_a(): pass\n")
        self.assertEqual(self._fix(), 0)
        shards = self._shards("evennia-shards")
        self.assertEqual(shards[0]["labels"], ["world.alpha.tests.test_one"])
        self.assertEqual(shards[1]["labels"], ["world.beta.tests.test_two", "world.beta.tests.test_new"])
        self.assertEqual(self._check(), 0)

    def test_module_under_a_package_label_is_already_owned(self):
        self._write("server/conf/tests/test_more.py", "def test_a(): pass\n")
        self.assertEqual(self._check(), 0)
        self.assertEqual(self._shards("evennia-shards")[2]["labels"], ["server"])

    def test_module_without_relatives_joins_the_lightest_shard(self):
        self._write("commands/tests/test_cmd.py", "def test_a(): pass\n")
        self.assertEqual(self._fix(), 0)
        # alpha owns one test, beta two, server one: alpha wins the tie by index.
        self.assertIn("commands.tests.test_cmd", self._shards("evennia-shards")[0]["labels"])

    def test_renamed_module_drops_the_stale_label_and_registers_the_new_one(self):
        self._write("world/alpha/tests/test_extra.py", "def test_a(): pass\n")
        self.assertEqual(self._fix(), 0)
        (self.root / "world/alpha/tests/test_extra.py").rename(self.root / "world/alpha/tests/test_renamed.py")
        self.assertEqual(self._fix(), 0)
        self.assertEqual(
            self._shards("evennia-shards")[0]["labels"],
            ["world.alpha.tests.test_one", "world.alpha.tests.test_renamed"],
        )

    def test_a_shard_is_never_emptied_automatically(self):
        (self.root / "world/alpha/tests/test_one.py").unlink()
        self.assertEqual(self._fix(), 1)
        self.assertEqual(self._shards("evennia-shards")[0]["labels"], ["world.alpha.tests.test_one"])

    def test_double_ownership_is_reported_not_repaired(self):
        shards = self._shards("evennia-shards")
        shards[1]["labels"].append("world.alpha.tests.test_one")
        self._manifest("evennia-shards", shards)
        self.assertEqual(self._check(), 1)
        self.assertEqual(self._fix(), 1)
        self.assertEqual(self._shards("evennia-shards"), shards)

    def test_new_browser_method_joins_the_process_list_of_its_class(self):
        self._write(
            "web/tests/browser/test_shell.py",
            "class ShellTests:\n    def test_open(self): pass\n"
            "class OtherTests:\n    def test_close(self): pass\n    def test_again(self): pass\n",
        )
        self.assertEqual(self._fix(), 0)
        shard = self._shards("browser-shards")[0]
        self.assertEqual(shard["files_a"], ["web.tests.browser.test_shell.ShellTests.test_open"])
        self.assertEqual(
            shard["files_b"],
            [
                "web.tests.browser.test_shell.OtherTests.test_close",
                "web.tests.browser.test_shell.OtherTests.test_again",
            ],
        )

    def test_class_label_owns_methods_added_to_that_class(self):
        shards = self._shards("browser-shards")
        shards[0]["files_a"] = ["web.tests.browser.test_shell.ShellTests"]
        self._manifest("browser-shards", shards)
        self._write(
            "web/tests/browser/test_shell.py",
            "class ShellTests:\n    def test_open(self): pass\n    def test_more(self): pass\n"
            "class OtherTests:\n    def test_close(self): pass\n",
        )
        self.assertEqual(self._check(), 0)

    def test_new_top_level_module_is_registered_keeping_the_file_indentation(self):
        self._write("tests/test_added.py", "def test_a(): pass\n")
        self.assertEqual(self._fix(), 0)
        text = (self.root / ".github/top-level-shards.json").read_text(encoding="utf-8")
        self.assertEqual(json.loads(text)["shards"][0]["labels"], ["tests.test_contract", "tests.test_added"])
        self.assertTrue(text.startswith('{\n "shards"'))
        self.assertTrue(text.endswith("}\n"))

    def test_committed_manifests_are_in_step_with_the_repository(self):
        reports = shard_register.run(shard_register.REPO_ROOT, write=False)
        self.assertEqual(
            [(report.added, report.removed, report.manual) for report in reports],
            [([], [], [])] * 3,
            f"run: {shard_register.FIX_COMMAND}",
        )


if __name__ == "__main__":
    unittest.main()
