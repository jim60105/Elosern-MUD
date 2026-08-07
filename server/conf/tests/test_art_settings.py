"""Tests for the deterministic art-assets settings contract."""

import unittest

from django.conf import settings


class ArtSettingsTests(unittest.TestCase):
    def test_store_root_lives_under_game_dir_and_defaults_are_sane(self):
        self.assertTrue(settings.ART_STORE_ROOT.startswith(settings.GAME_DIR))
        self.assertIn(".art", settings.ART_STORE_ROOT)
        self.assertGreater(settings.ART_SCHEDULER_INTERVAL_SECONDS, 0)
        self.assertGreater(settings.ART_SCHEDULER_LIMIT, 0)
        self.assertIsInstance(settings.ART_SCHEDULER_ENABLED, bool)

    def test_sd_client_defaults_to_the_internal_client(self):
        self.assertEqual(
            settings.ART_SD_CLIENT, "world.art.sd_worker.SDWebUIClient"
        )

    def test_sd_endpoint_and_timeout_defaults(self):
        self.assertTrue(settings.ART_SD_BASE_URL.startswith("http"))
        self.assertEqual(settings.ART_SD_TIMEOUT_SECONDS, 600)
        self.assertIsInstance(settings.ART_SD_TIMEOUT_SECONDS, int)
        self.assertGreater(settings.ART_SD_TIMEOUT_SECONDS, 0)

    def test_generation_parameter_defaults(self):
        self.assertGreater(settings.ART_SD_STEPS, 0)
        self.assertGreater(settings.ART_SD_CFG_SCALE, 0)
        self.assertEqual(settings.ART_SD_SAMPLER, "")
        self.assertEqual(settings.ART_SD_SCHEDULER, "")
        self.assertEqual(settings.ART_SD_CHECKPOINT, "")

    def test_per_aspect_ratio_sizes_are_sd_compatible(self):
        self.assertEqual(settings.ART_SD_SCENE_WIDTH, 1344)
        self.assertEqual(settings.ART_SD_SCENE_HEIGHT, 768)
        self.assertEqual(settings.ART_SD_PORTRAIT_WIDTH, 768)
        self.assertEqual(settings.ART_SD_PORTRAIT_HEIGHT, 1024)
        for dimension in (
            settings.ART_SD_SCENE_WIDTH,
            settings.ART_SD_SCENE_HEIGHT,
            settings.ART_SD_PORTRAIT_WIDTH,
            settings.ART_SD_PORTRAIT_HEIGHT,
        ):
            self.assertEqual(dimension % 8, 0)

    def test_resource_caps_and_prepin_defaults(self):
        self.assertEqual(settings.ART_SD_MAX_RESPONSE_BYTES, 52428800)
        self.assertEqual(settings.ART_SD_MAX_IMAGE_DIMENSIONS, 4096)
        self.assertEqual(settings.ART_SD_MAX_IMAGE_PIXELS, 16777216)
        self.assertIs(settings.ART_SD_PREPIN_SAMPLES_FORMAT, False)

    def test_external_worker_settings_are_removed(self):
        self.assertFalse(hasattr(settings, "ART_WORKER_CMD"))
        self.assertFalse(hasattr(settings, "ART_WORKER_TIMEOUT_SECONDS"))
