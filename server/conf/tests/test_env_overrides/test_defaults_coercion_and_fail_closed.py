"""Slice of ``test_env_overrides``: DefaultsTests, ValidCoercionTests, FailClosedTests.
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
    BOOL_SETTINGS,
    DEFAULT_REPR,
    ENV_BACKED,
    INVALID_VALUES,
    VALID_OVERRIDES,
    _IMPORT,
    _SubprocessSettingsTests,
    _printed_map,
    _settings_repr,
)


class DefaultsTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_unset_environment_yields_the_documented_defaults(self):
        result = self._run(_settings_repr(list(DEFAULT_REPR)))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, set(DEFAULT_REPR)), DEFAULT_REPR
        )


class ValidCoercionTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_every_env_backed_setting_coerces_its_valid_override(self):
        for setting, variable, raw, expected in VALID_OVERRIDES:
            with self.subTest(setting=setting, raw=raw):
                result = self._run(_settings_repr([setting]), **{variable: raw})
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertEqual(
                    _printed_map(result.stdout, {setting}),
                    {setting: expected},
                )

    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_boolean_word_families_convert_every_boolean_knob(self):
        words = {
            "1": "True",
            "true": "True",
            "yes": "True",
            "on": "True",
            "0": "False",
            "false": "False",
            "no": "False",
            "off": "False",
        }
        for word, expected in words.items():
            with self.subTest(word=word):
                env = {name: word for name in BOOL_SETTINGS}
                result = self._run(_settings_repr(BOOL_SETTINGS), **env)
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                printed = _printed_map(result.stdout, set(BOOL_SETTINGS))
                for name in BOOL_SETTINGS:
                    self.assertEqual(printed[name], expected, msg=f"{name}={word}")

    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_boolean_words_are_case_insensitive(self):
        env = {
            "ART_SD_PREPIN_SAMPLES_FORMAT": "True",
            "ART_SD_PRESERVE_GENERATION_METADATA": "TRUE",
            "ART_REMBG_ENABLED": "TRUE",
            "ART_REMBG_DOWNLOAD_ENABLED": "Yes",
            "ART_SCHEDULER_ENABLED": "OFF",
            "ELOSERN_VUE_CLIENT": "Yes",
        }
        result = self._run(_settings_repr(BOOL_SETTINGS), **env)
        self.assertEqual(
            _printed_map(result.stdout, set(BOOL_SETTINGS)),
            {
                "ART_SD_PREPIN_SAMPLES_FORMAT": "True",
                "ART_SD_PRESERVE_GENERATION_METADATA": "True",
                "ART_REMBG_ENABLED": "True",
                "ART_REMBG_DOWNLOAD_ENABLED": "True",
                "ART_SCHEDULER_ENABLED": "False",
                "ELOSERN_VUE_CLIENT": "True",
            },
        )

    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_present_but_empty_falls_back_to_defaults_and_empty_free_text(self):
        names = [
            "ART_SD_SCENE_WIDTH",
            "ART_SD_BASE_URL",
            "ART_SD_SAMPLER",
            "ART_SD_SCHEDULER",
            "ART_SD_CHECKPOINT",
            "ART_SCHEDULER_INTERVAL_SECONDS",
            "ELOSERN_VUE_CLIENT",
        ]
        env = {ENV_BACKED[name]: "" for name in names}
        result = self._run(_settings_repr(names), **env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            _printed_map(result.stdout, set(names)),
            {name: DEFAULT_REPR[name] for name in names},
        )

    @covers_requirement(
        "settings-environment-overrides::deployment-settings-accept-typed-environment-overrides"
    )
    def test_free_text_knobs_keep_content_verbatim(self):
        env = {
            "ART_SD_SAMPLER": "DPM++ 2M Karras",
            "ART_SD_SCHEDULER": "normal",
            "ART_SD_CHECKPOINT": "mix/Taipei_style_v2.safetensors [3f5c2a1b]",
        }
        result = self._run(
            _settings_repr(
                ["ART_SD_SAMPLER", "ART_SD_SCHEDULER", "ART_SD_CHECKPOINT"]
            ),
            **env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = _printed_map(
            result.stdout,
            {"ART_SD_SAMPLER", "ART_SD_SCHEDULER", "ART_SD_CHECKPOINT"},
        )
        self.assertEqual(printed["ART_SD_SAMPLER"], repr("DPM++ 2M Karras"))
        self.assertEqual(printed["ART_SD_SCHEDULER"], repr("normal"))
        self.assertEqual(
            printed["ART_SD_CHECKPOINT"],
            repr("mix/Taipei_style_v2.safetensors [3f5c2a1b]"),
        )


class FailClosedTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::invalid-environment-values-fail-settings-load-with-a-named-error"
    )
    def test_invalid_values_abort_the_settings_import_naming_variable_and_rule(self):
        for variable, raw, rule in INVALID_VALUES:
            with self.subTest(variable=variable, raw=raw):
                result = self._run(_IMPORT, **{variable: raw})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ImproperlyConfigured", result.stderr)
                self.assertIn(variable, result.stderr)
                # The contract quotes the raw value: 'twelve', not twelve.
                self.assertIn(f"'{raw}'", result.stderr)
                self.assertIn(rule, result.stderr)
