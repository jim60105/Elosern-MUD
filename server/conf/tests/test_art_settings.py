"""Tests for the deterministic art-assets settings contract.

CI/test invocations must not export ``ART_SD_*`` environment overrides;
``server/conf/test_settings.py`` sanitizes them regardless, so the effective
values pinned here are always the documented code defaults.
"""

import unittest

from django.conf import settings

from tools.spec_traceability import covers_requirement


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

    def test_output_format_pipeline_defaults(self):
        self.assertEqual(settings.ART_SD_OUTPUT_FORMAT, "png")
        self.assertEqual(settings.ART_SD_OUTPUT_QUALITY, 80)
        self.assertIs(settings.ART_SD_PRESERVE_GENERATION_METADATA, True)
        # Derived, never configured: the default format yields .png.
        self.assertEqual(settings.ART_SD_OUTPUT_EXTENSION, ".png")

    def test_background_removal_defaults(self):
        # The stage ships fully implemented and OFF (art-portrait-cutout D2):
        # the test defaults are exactly the documented code defaults, so no
        # test ever loads the optional rembg stack by accident.
        self.assertIs(settings.ART_REMBG_ENABLED, False)
        self.assertEqual(settings.ART_REMBG_MODEL, "bria-rmbg")
        self.assertIs(settings.ART_REMBG_DOWNLOAD_ENABLED, True)
        self.assertEqual(settings.ART_REMBG_ALLOWANCE_SECONDS, 120)
        self.assertEqual(settings.ART_REMBG_THREADS, 0)

    def test_background_removal_seam_and_model_dir_are_code_only(self):
        self.assertEqual(
            settings.ART_REMBG_BACKEND, "world.art.cutout.RembgCutoutBackend"
        )
        self.assertEqual(
            settings.ART_REMBG_MODEL_DIR,
            __import__("os").path.join(settings.GAME_DIR, "server", ".rembg"),
        )

    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_prompt_translation_defaults_to_off(self):
        self.assertIs(settings.ART_TRANSLATE_ENABLED, False)

    @covers_requirement(
        "settings-environment-overrides::the-client-seam-and-art-store-root-are-never-environment-configurable"
    )
    def test_prompt_translation_seam_is_code_only(self):
        self.assertEqual(
            settings.ART_TRANSLATE_BACKEND,
            "world.art.translate_ct2.CTranslate2Backend",
        )

    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_prompt_translation_download_is_air_gapped_under_test_settings(self):
        # The documented code default is True, but server/conf/test_settings.py
        # pins the knob False after the star import: every test run — even one
        # resolving the shipped backend against an unseeded directory — sits on
        # the air-gapped track and can never trigger a model download.
        self.assertIs(settings.ART_TRANSLATE_DOWNLOAD_ENABLED, False)

    def test_external_worker_settings_are_removed(self):
        self.assertFalse(hasattr(settings, "ART_WORKER_CMD"))
        self.assertFalse(hasattr(settings, "ART_WORKER_TIMEOUT_SECONDS"))
