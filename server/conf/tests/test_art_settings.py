"""Tests for the deterministic art-assets settings contract."""

from pathlib import Path
import unittest

from django.conf import settings


class ArtSettingsTests(unittest.TestCase):
    def test_store_root_lives_under_game_dir_and_defaults_are_sane(self):
        self.assertTrue(settings.ART_STORE_ROOT.startswith(settings.GAME_DIR))
        self.assertIn(".art", settings.ART_STORE_ROOT)
        self.assertIsInstance(settings.ART_WORKER_CMD, list)
        self.assertIn("-m", settings.ART_WORKER_CMD)
        self.assertGreater(settings.ART_WORKER_TIMEOUT_SECONDS, 0)
        self.assertGreater(settings.ART_SCHEDULER_INTERVAL_SECONDS, 0)
        self.assertGreater(settings.ART_SCHEDULER_LIMIT, 0)
        self.assertIsInstance(settings.ART_SCHEDULER_ENABLED, bool)

    def test_default_worker_module_exists_in_the_repository(self):
        game_dir = Path(settings.GAME_DIR)
        self.assertTrue((game_dir / "tools" / "art_worker.py").is_file())
