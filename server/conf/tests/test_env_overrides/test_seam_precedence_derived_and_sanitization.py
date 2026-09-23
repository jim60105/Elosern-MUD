"""Slice of ``test_env_overrides``: CodeOnlySeamTests, CutoutBootGuardTests, PrecedenceTests, DerivedExtensionTests, TestSettingsSanitizationTests.
"""
import ast
import os
import re
import subprocess
import sys
import unittest
from server.conf.llm_knobs import llm_env_names, llm_global_env_names
from tools.spec_traceability import covers_requirement

from ._support import (
    DEFAULT_REPR,
    REPO_ROOT,
    VALID_OVERRIDES,
    _IMPORT,
    _SubprocessSettingsTests,
    _printed_map,
    _settings_repr,
)


class CodeOnlySeamTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::the-client-seam-and-art-store-root-are-never-environment-configurable"
    )
    def test_hostile_client_seam_and_store_root_variables_are_ignored(self):
        names = [
            "ART_SD_CLIENT",
            "ART_STORE_ROOT",
            "ART_REMBG_BACKEND",
            "ART_REMBG_MODEL_DIR",
            "ART_TRANSLATE_BACKEND",
            "ART_TRANSLATE_MODEL_DIR",
        ]
        env = {
            "ART_SD_CLIENT": "os.system",
            "ART_STORE_ROOT": "/tmp/env-override-art-root",
            "ART_REMBG_BACKEND": "os.system",
            "ART_REMBG_MODEL_DIR": "/tmp/env-override-rembg",
            "ART_TRANSLATE_BACKEND": "os.system",
            "ART_TRANSLATE_MODEL_DIR": "/tmp/env-override-translate",
        }
        result = self._run(_settings_repr(names), **env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = _printed_map(
            result.stdout,
            {
                "ART_SD_CLIENT",
                "ART_STORE_ROOT",
                "ART_REMBG_BACKEND",
                "ART_REMBG_MODEL_DIR",
                "ART_TRANSLATE_BACKEND",
                "ART_TRANSLATE_MODEL_DIR",
            },
        )
        self.assertEqual(
            printed["ART_SD_CLIENT"], repr("world.art.sd_worker.SDWebUIClient")
        )
        self.assertEqual(
            printed["ART_STORE_ROOT"],
            repr(os.path.join(REPO_ROOT, "server", ".art")),
            msg=printed["ART_STORE_ROOT"],
        )
        self.assertNotIn("env-override-art-root", printed["ART_STORE_ROOT"])
        self.assertEqual(
            printed["ART_REMBG_BACKEND"],
            repr("world.art.cutout.RembgCutoutBackend"),
        )
        self.assertEqual(
            printed["ART_REMBG_MODEL_DIR"],
            repr(os.path.join(REPO_ROOT, "server", ".rembg")),
            msg=printed["ART_REMBG_MODEL_DIR"],
        )
        self.assertNotIn("env-override-rembg", printed["ART_REMBG_MODEL_DIR"])
        self.assertEqual(
            printed["ART_TRANSLATE_BACKEND"],
            repr("world.art.translate_ct2.CTranslate2Backend"),
        )
        self.assertEqual(
            printed["ART_TRANSLATE_MODEL_DIR"],
            repr(os.path.join(REPO_ROOT, "server", ".translate")),
            msg=printed["ART_TRANSLATE_MODEL_DIR"],
        )
        self.assertNotIn("env-override-translate", printed["ART_TRANSLATE_MODEL_DIR"])

    @covers_requirement(
        "settings-environment-overrides::the-client-seam-and-art-store-root-are-never-environment-configurable"
    )
    def test_hostile_credential_variables_are_ignored(self):
        names = ["ART_SD_USERNAME", "ART_SD_PASSWORD"]
        result = self._run(_settings_repr(names), ART_SD_USERNAME="x", ART_SD_PASSWORD="y")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = _printed_map(result.stdout, set(names))
        self.assertEqual(printed["ART_SD_USERNAME"], "''")
        self.assertEqual(printed["ART_SD_PASSWORD"], "''")


class CutoutBootGuardTests(_SubprocessSettingsTests):  # archive-sync annotations

    """The alpha-hostile combination is refused at boot, never silently
    degraded: an enabled background-removal stage with an effective
    ART_SD_OUTPUT_FORMAT of jpeg would store the original background-ful
    portrait while the record claimed to be a cutout. The check runs AFTER the
    secret_settings import, so every override path is covered by the one
    guard (art-portrait-cutout D4; annotations follow the archive sync, task
    6.11)."""

    @covers_requirement("art-portrait-cutout::an-output-format-that-cannot-carry-alpha-is-refused-at-boot")
    def test_enabled_with_jpeg_fails_settings_import(self):
        result = self._run(
            _IMPORT, ART_REMBG_ENABLED="true", ART_SD_OUTPUT_FORMAT="jpeg"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertIn("ART_REMBG_ENABLED", result.stderr)
        self.assertIn("ART_SD_OUTPUT_FORMAT", result.stderr)

    @covers_requirement("art-portrait-cutout::an-output-format-that-cannot-carry-alpha-is-refused-at-boot")
    def test_a_secret_format_override_is_caught_by_the_same_guard(self):
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            "secret.ART_SD_OUTPUT_FORMAT = 'jpeg'\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            + _IMPORT
        )
        result = self._run(code, ART_REMBG_ENABLED="true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertIn("ART_REMBG_ENABLED", result.stderr)
        self.assertIn("ART_SD_OUTPUT_FORMAT", result.stderr)

    @covers_requirement("art-portrait-cutout::an-output-format-that-cannot-carry-alpha-is-refused-at-boot")
    def test_alpha_capable_formats_boot_normally_when_enabled(self):
        for raw in ("png", "webp", "avif"):
            with self.subTest(format=raw):
                result = self._run(
                    _settings_repr(["ART_REMBG_ENABLED", "ART_SD_OUTPUT_FORMAT"]),
                    ART_REMBG_ENABLED="true",
                    ART_SD_OUTPUT_FORMAT=raw,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertEqual(
                    _printed_map(result.stdout, {"ART_REMBG_ENABLED", "ART_SD_OUTPUT_FORMAT"}),
                    {"ART_REMBG_ENABLED": "True", "ART_SD_OUTPUT_FORMAT": repr(raw)},
                )

    @covers_requirement("art-portrait-cutout::an-output-format-that-cannot-carry-alpha-is-refused-at-boot")
    def test_jpeg_alone_is_still_a_supported_configuration(self):
        result = self._run(
            _settings_repr(["ART_REMBG_ENABLED", "ART_SD_OUTPUT_FORMAT"]),
            ART_SD_OUTPUT_FORMAT="jpeg",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, {"ART_REMBG_ENABLED", "ART_SD_OUTPUT_FORMAT"}),
            {"ART_REMBG_ENABLED": "False", "ART_SD_OUTPUT_FORMAT": "'jpeg'"},
        )


class PrecedenceTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::configuration-layers-follow-default-environment-secret-precedence"
    )
    def test_environment_wins_over_the_code_default(self):
        result = self._run(
            _settings_repr(["ART_SD_TIMEOUT_SECONDS"]), ART_SD_TIMEOUT_SECONDS="120"
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, {"ART_SD_TIMEOUT_SECONDS"}),
            {"ART_SD_TIMEOUT_SECONDS": "120"},
        )

    @covers_requirement(
        "settings-environment-overrides::configuration-layers-follow-default-environment-secret-precedence"
    )
    def test_secret_settings_wins_over_the_environment(self):
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            "secret.ART_SD_TIMEOUT_SECONDS = 90\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            + _settings_repr(["ART_SD_TIMEOUT_SECONDS"])
        )
        result = self._run(code, ART_SD_TIMEOUT_SECONDS="120")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, {"ART_SD_TIMEOUT_SECONDS"}),
            {"ART_SD_TIMEOUT_SECONDS": "90"},
        )


class DerivedExtensionTests(_SubprocessSettingsTests):
    """ART_SD_OUTPUT_EXTENSION is derived, never configured: it follows the
    EFFECTIVE format (default, environment, or secret_settings) and any
    directly assigned value is unconditionally discarded."""

    NAMES = ["ART_SD_OUTPUT_FORMAT", "ART_SD_OUTPUT_EXTENSION"]

    @covers_requirement(
        "settings-environment-overrides::the-output-extension-is-derived-never-configured"
    )
    def test_the_environment_format_flows_into_the_extension(self):
        for raw, fmt, extension in (
            ("AVIF", "avif", ".avif"),
            ("jpeg", "jpeg", ".jpg"),
            ("webp", "webp", ".webp"),
            ("png", "png", ".png"),
        ):
            with self.subTest(raw=raw):
                result = self._run(
                    _settings_repr(self.NAMES), ART_SD_OUTPUT_FORMAT=raw
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertEqual(
                    _printed_map(result.stdout, set(self.NAMES)),
                    {
                        "ART_SD_OUTPUT_FORMAT": repr(fmt),
                        "ART_SD_OUTPUT_EXTENSION": repr(extension),
                    },
                )

    @covers_requirement(
        "settings-environment-overrides::the-output-extension-is-derived-never-configured"
    )
    def test_a_secret_format_override_flows_into_the_extension(self):
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            "secret.ART_SD_OUTPUT_FORMAT = 'webp'\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            + _settings_repr(self.NAMES)
        )
        result = self._run(code)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, set(self.NAMES)),
            {
                "ART_SD_OUTPUT_FORMAT": "'webp'",
                "ART_SD_OUTPUT_EXTENSION": "'.webp'",
            },
        )

    @covers_requirement(
        "settings-environment-overrides::the-output-extension-is-derived-never-configured"
    )
    def test_a_direct_environment_extension_assignment_is_discarded(self):
        result = self._run(
            _settings_repr(self.NAMES), ART_SD_OUTPUT_EXTENSION=".heic"
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, set(self.NAMES)),
            {
                "ART_SD_OUTPUT_FORMAT": "'png'",
                "ART_SD_OUTPUT_EXTENSION": "'.png'",
            },
        )

    @covers_requirement(
        "settings-environment-overrides::the-output-extension-is-derived-never-configured"
    )
    def test_a_secret_extension_assignment_is_discarded(self):
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            "secret.ART_SD_OUTPUT_FORMAT = 'avif'\n"
            "secret.ART_SD_OUTPUT_EXTENSION = '.heic'\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            + _settings_repr(self.NAMES)
        )
        result = self._run(code)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, set(self.NAMES)),
            {
                "ART_SD_OUTPUT_FORMAT": "'avif'",
                "ART_SD_OUTPUT_EXTENSION": "'.avif'",
            },
        )


class TestSettingsSanitizationTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_test_settings_pop_inherited_override_names_before_star_import(self):
        # Full sweep, not a sample: every env-backed variable gets a valid,
        # deliberately non-default value (VALID_OVERRIDES raws), and every
        # setting must still come out at its code default. A partial pop
        # list fails for at least the omitted knob.
        code = "\n".join(
            [
                "import sys",
                "sys.argv = ['evennia', 'test']",
                "import server.conf.test_settings as t",
            ]
            + [f"print({name!r}, repr(t.{name}))" for name in DEFAULT_REPR]
        )
        env = {
            "MUD_TEST_SETTINGS": "1",
            **{variable: raw for _, variable, raw, _ in VALID_OVERRIDES},
        }
        result = self._run(code, **env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, set(DEFAULT_REPR)), DEFAULT_REPR
        )
