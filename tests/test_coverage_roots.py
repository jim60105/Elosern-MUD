"""Tests for combined coverage source-root verification."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.verify_coverage_roots import missing_roots


class CoverageRootTests(unittest.TestCase):
    def test_every_configured_root_is_required(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pyproject = root / "pyproject.toml"
            report = root / "coverage.json"
            pyproject.write_text(
                '[tool.coverage.run]\nsource = ["commands", "world"]\n',
                encoding="utf-8",
            )
            report.write_text(
                json.dumps({"files": {"commands/example.py": {}}}),
                encoding="utf-8",
            )

            self.assertEqual(missing_roots(report, pyproject), {"world"})

    def test_report_with_every_configured_root_passes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pyproject = root / "pyproject.toml"
            report = root / "coverage.json"
            pyproject.write_text(
                '[tool.coverage.run]\nsource = ["commands", "world"]\n',
                encoding="utf-8",
            )
            report.write_text(
                json.dumps(
                    {
                        "files": {
                            "commands/example.py": {},
                            "world/example.py": {},
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertFalse(missing_roots(report, pyproject))


if __name__ == "__main__":
    unittest.main()
