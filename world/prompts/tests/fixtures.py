"""Shared fixture helpers for prompt-library tests.

Tests copy the repo's own ``prompts/`` directory into a throwaway root (so
every other file is valid by construction), corrupt the file under test, and
explicitly load that root. Every test resets the module-level library in
cleanup so one test's fixture root cannot leak into the next.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from world.prompts.loader import load_prompt_library, reset_prompt_library

REPO_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
REPO_ROOT = Path(__file__).resolve().parents[3]


class PromptFixture(unittest.TestCase):
    """Base: a temp prompt root seeded with the repo's own valid prompt files."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(reset_prompt_library)
        self.root = Path(self._tmp.name)
        shutil.copytree(REPO_PROMPTS, self.root, dirs_exist_ok=True)

    def write_file(self, name: str, content: str) -> Path:
        """Overwrite one prompt file inside the fixture root."""
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def load(self, root: Path | None = None) -> object:
        """Load the fixture root (or a specific root) and return the library."""
        return load_prompt_library(str(root or self.root))
