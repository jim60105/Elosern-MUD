"""Validate CLI tests for the prompt library (prompt-library).

Runs the CLI exactly as an admin would — a fresh Python process loading the
library from ``PROMPT_ROOT`` — and asserts the exit codes and the per-key
summary / named-error output.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.spec_traceability import covers_requirement

from world.prompts.tests.fixtures import REPO_PROMPTS, REPO_ROOT



def _run_cli(prompt_root: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "DJANGO_SETTINGS_MODULE"}
    env["PROMPT_ROOT"] = prompt_root
    return subprocess.run(
        [sys.executable, "-m", "world.prompts.validate"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class ValidateCliTests(unittest.TestCase):
    @covers_requirement("prompt-library::a-validate-cli-checks-the-library-without-starting-the-server")
    def test_valid_library_prints_per_key_summary_and_exits_zero(self):
        result = _run_cli(str(REPO_PROMPTS))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prompt library OK", result.stdout)
        for key in (
            "narrator.system",
            "npc_dialogue.system",
            "scenario_director.system",
            "npc.thinking",
            "art.style",
            "art.character_description",
            "art.monster_description",
            "character_creation.system",
        ):
            self.assertIn(f"ok {key}", result.stdout)

    @covers_requirement("prompt-library::a-validate-cli-checks-the-library-without-starting-the-server")
    def test_broken_library_prints_every_named_error_and_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(REPO_PROMPTS, root, dirs_exist_ok=True)
            (root / "narrator.yaml").write_text(
                "schema_version: 1\nprompts:\n  narrator.system: 旁白 {nmme}。\n",
                encoding="utf-8",
            )
            result = _run_cli(str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("narrator.yaml", result.stdout)
            self.assertIn("narrator.system", result.stdout)
            self.assertIn("nmme", result.stdout)

    @covers_requirement("prompt-library::a-validate-cli-checks-the-library-without-starting-the-server")
    def test_broken_library_reports_every_error_not_just_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(REPO_PROMPTS, root, dirs_exist_ok=True)
            (root / "narrator.yaml").write_text(
                "schema_version: 1\nprompts:\n  narrator.system: 旁白 {nmme}。\n",
                encoding="utf-8",
            )
            (root / "npc.yaml").write_text(
                "schema_version: 1\nprompts:\n  npc.thinking: （{name} {oops}）\n",
                encoding="utf-8",
            )
            result = _run_cli(str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("narrator.system", result.stdout)
            self.assertIn("npc.thinking", result.stdout)
            self.assertIn("nmme", result.stdout)
            self.assertIn("oops", result.stdout)


if __name__ == "__main__":
    unittest.main()
