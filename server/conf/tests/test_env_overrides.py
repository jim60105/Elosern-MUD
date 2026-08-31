"""Subprocess black-box tests for the environment-variable settings overrides.

Effective values and fail-closed behavior exist only at settings-import time,
so every behavioral case runs ``sys.executable -c "import server.conf.settings"``
with a curated environment (inherited ``DJANGO_SETTINGS_MODULE`` and any
deployment override names stripped), mirroring the import-time subprocess
pattern in ``world/ai/tests/test_profiles.py``.

CI/test invocations must not export ``ART_SD_*`` / ``ART_SCHEDULER_*`` /
``ELOSERN_VUE_CLIENT`` / ``SD_WEBUI_BASE_URL`` overrides; the test-settings
sanitize step keeps a star-imported run at the code defaults regardless.
"""

import ast
import os
import re
import subprocess
import sys
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
SETTINGS_PATH = os.path.join(REPO_ROOT, "server", "conf", "settings.py")
TEST_SETTINGS_PATH = os.path.join(REPO_ROOT, "server", "conf", "test_settings.py")
ENV_EXAMPLE_PATH = os.path.join(REPO_ROOT, ".env.example")
GUIDE_PATH = os.path.join(REPO_ROOT, "docs", "development", "settings-and-environment.md")
SIDEBAR_PATH = os.path.join(REPO_ROOT, "docs", "_sidebar.md")
PROMPTS_DOC_PATH = os.path.join(REPO_ROOT, "docs", "gm", "prompts.md")

# The env-backed inventory: 23 same-named variables plus the URL knob whose
# variable name is fixed by the internal-art-worker spec.
ENV_BACKED: dict[str, str] = {
    "ART_SD_BASE_URL": "SD_WEBUI_BASE_URL",
    "ART_SD_TIMEOUT_SECONDS": "ART_SD_TIMEOUT_SECONDS",
    "ART_SD_STEPS": "ART_SD_STEPS",
    "ART_SD_CFG_SCALE": "ART_SD_CFG_SCALE",
    "ART_SD_SAMPLER": "ART_SD_SAMPLER",
    "ART_SD_SCHEDULER": "ART_SD_SCHEDULER",
    "ART_SD_CHECKPOINT": "ART_SD_CHECKPOINT",
    "ART_SD_STYLES": "ART_SD_STYLES",
    "ART_SD_MODULES": "ART_SD_MODULES",
    "ART_SD_SCENE_WIDTH": "ART_SD_SCENE_WIDTH",
    "ART_SD_SCENE_HEIGHT": "ART_SD_SCENE_HEIGHT",
    "ART_SD_PORTRAIT_WIDTH": "ART_SD_PORTRAIT_WIDTH",
    "ART_SD_PORTRAIT_HEIGHT": "ART_SD_PORTRAIT_HEIGHT",
    "ART_SD_MAX_RESPONSE_BYTES": "ART_SD_MAX_RESPONSE_BYTES",
    "ART_SD_MAX_IMAGE_DIMENSIONS": "ART_SD_MAX_IMAGE_DIMENSIONS",
    "ART_SD_MAX_IMAGE_PIXELS": "ART_SD_MAX_IMAGE_PIXELS",
    "ART_SD_PREPIN_SAMPLES_FORMAT": "ART_SD_PREPIN_SAMPLES_FORMAT",
    "ART_SD_OUTPUT_FORMAT": "ART_SD_OUTPUT_FORMAT",
    "ART_SD_OUTPUT_QUALITY": "ART_SD_OUTPUT_QUALITY",
    "ART_SD_PRESERVE_GENERATION_METADATA": "ART_SD_PRESERVE_GENERATION_METADATA",
    "ART_SD_PROBE_TIMEOUT_MS": "ART_SD_PROBE_TIMEOUT_MS",
    "ART_SD_PROBE_CACHE_SECONDS": "ART_SD_PROBE_CACHE_SECONDS",
    "ART_SCHEDULER_ENABLED": "ART_SCHEDULER_ENABLED",
    "ART_SCHEDULER_INTERVAL_SECONDS": "ART_SCHEDULER_INTERVAL_SECONDS",
    "ART_SCHEDULER_LIMIT": "ART_SCHEDULER_LIMIT",
    "ELOSERN_VUE_CLIENT": "ELOSERN_VUE_CLIENT",
}

# repr() of each effective default, exactly as test_art_settings.py pins them.
DEFAULT_REPR: dict[str, str] = {
    "ART_SD_BASE_URL": "'http://127.0.0.1:7860'",
    "ART_SD_TIMEOUT_SECONDS": "600",
    "ART_SD_STEPS": "30",
    "ART_SD_CFG_SCALE": "7.0",
    "ART_SD_SAMPLER": "''",
    "ART_SD_SCHEDULER": "''",
    "ART_SD_CHECKPOINT": "''",
    "ART_SD_STYLES": "''",
    "ART_SD_MODULES": "''",
    "ART_SD_SCENE_WIDTH": "1344",
    "ART_SD_SCENE_HEIGHT": "768",
    "ART_SD_PORTRAIT_WIDTH": "768",
    "ART_SD_PORTRAIT_HEIGHT": "1024",
    "ART_SD_MAX_RESPONSE_BYTES": "52428800",
    "ART_SD_MAX_IMAGE_DIMENSIONS": "4096",
    "ART_SD_MAX_IMAGE_PIXELS": "16777216",
    "ART_SD_PREPIN_SAMPLES_FORMAT": "False",
    "ART_SD_OUTPUT_FORMAT": "'png'",
    "ART_SD_OUTPUT_QUALITY": "80",
    "ART_SD_PRESERVE_GENERATION_METADATA": "True",
    "ART_SD_PROBE_TIMEOUT_MS": "5000",
    "ART_SD_PROBE_CACHE_SECONDS": "300",
    "ART_SCHEDULER_ENABLED": "True",
    "ART_SCHEDULER_INTERVAL_SECONDS": "30",
    "ART_SCHEDULER_LIMIT": "4",
    "ELOSERN_VUE_CLIENT": "True",
}

# One valid override per env-backed setting: (setting, variable, raw,
# expected repr). The repr comparison pins the Python type as well as the
# value, so a hard-coded literal, a missing int()/float() coercion, or a
# stringified bool fails the assertion.
VALID_OVERRIDES: list[tuple[str, str, str, str]] = [
    ("ART_SD_BASE_URL", "SD_WEBUI_BASE_URL", "http://sd.internal:7861", "'http://sd.internal:7861'"),
    ("ART_SD_TIMEOUT_SECONDS", "ART_SD_TIMEOUT_SECONDS", " 120 ", "120"),
    ("ART_SD_STEPS", "ART_SD_STEPS", "12", "12"),
    ("ART_SD_CFG_SCALE", "ART_SD_CFG_SCALE", "1.5", "1.5"),
    ("ART_SD_SAMPLER", "ART_SD_SAMPLER", "Euler a", "'Euler a'"),
    ("ART_SD_SCHEDULER", "ART_SD_SCHEDULER", "karras", "'karras'"),
    (
        "ART_SD_CHECKPOINT",
        "ART_SD_CHECKPOINT",
        "anima/animaika_v43.safetensors",
        "'anima/animaika_v43.safetensors'",
    ),
    ("ART_SD_STYLES", "ART_SD_STYLES", "cinematic, portrait", "'cinematic, portrait'"),
    (
        "ART_SD_MODULES",
        "ART_SD_MODULES",
        "te.safetensors,vae.safetensors",
        "'te.safetensors,vae.safetensors'",
    ),
    ("ART_SD_SCENE_WIDTH", "ART_SD_SCENE_WIDTH", "1024", "1024"),
    ("ART_SD_SCENE_HEIGHT", "ART_SD_SCENE_HEIGHT", "576", "576"),
    ("ART_SD_PORTRAIT_WIDTH", "ART_SD_PORTRAIT_WIDTH", "896", "896"),
    ("ART_SD_PORTRAIT_HEIGHT", "ART_SD_PORTRAIT_HEIGHT", "1152", "1152"),
    ("ART_SD_MAX_RESPONSE_BYTES", "ART_SD_MAX_RESPONSE_BYTES", "1048576", "1048576"),
    ("ART_SD_MAX_IMAGE_DIMENSIONS", "ART_SD_MAX_IMAGE_DIMENSIONS", "2048", "2048"),
    ("ART_SD_MAX_IMAGE_PIXELS", "ART_SD_MAX_IMAGE_PIXELS", "4194304", "4194304"),
    ("ART_SD_PREPIN_SAMPLES_FORMAT", "ART_SD_PREPIN_SAMPLES_FORMAT", "true", "True"),
    ("ART_SD_OUTPUT_FORMAT", "ART_SD_OUTPUT_FORMAT", "WEBP", "'webp'"),
    ("ART_SD_OUTPUT_FORMAT", "ART_SD_OUTPUT_FORMAT", " jpeg ", "'jpeg'"),
    ("ART_SD_OUTPUT_QUALITY", "ART_SD_OUTPUT_QUALITY", "60", "60"),
    ("ART_SD_OUTPUT_QUALITY", "ART_SD_OUTPUT_QUALITY", "1", "1"),
    ("ART_SD_OUTPUT_QUALITY", "ART_SD_OUTPUT_QUALITY", "100", "100"),
    (
        "ART_SD_PRESERVE_GENERATION_METADATA",
        "ART_SD_PRESERVE_GENERATION_METADATA",
        "off",
        "False",
    ),
    ("ART_SD_PROBE_TIMEOUT_MS", "ART_SD_PROBE_TIMEOUT_MS", "2000", "2000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "ART_SD_PROBE_TIMEOUT_MS", "1000", "1000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "ART_SD_PROBE_TIMEOUT_MS", "60000", "60000"),
    ("ART_SD_PROBE_CACHE_SECONDS", "ART_SD_PROBE_CACHE_SECONDS", "60", "60"),
    ("ART_SD_PROBE_CACHE_SECONDS", "ART_SD_PROBE_CACHE_SECONDS", "5", "5"),
    ("ART_SD_PROBE_CACHE_SECONDS", "ART_SD_PROBE_CACHE_SECONDS", "3600", "3600"),
    ("ART_SCHEDULER_ENABLED", "ART_SCHEDULER_ENABLED", "0", "False"),
    ("ART_SCHEDULER_INTERVAL_SECONDS", "ART_SCHEDULER_INTERVAL_SECONDS", "15", "15"),
    ("ART_SCHEDULER_LIMIT", "ART_SCHEDULER_LIMIT", "8", "8"),
    ("ELOSERN_VUE_CLIENT", "ELOSERN_VUE_CLIENT", "off", "False"),
]

# (env var, raw value, extra expected stderr substring) per fail-closed family.
INVALID_VALUES: list[tuple[str, str, str]] = [
    ("ART_SD_STEPS", " twelve ", "expected a positive integer"),
    ("ART_SD_STEPS", "twelve", "expected a positive integer"),
    ("ART_SD_STEPS", "0", "expected a positive integer"),
    ("ART_SD_STEPS", "-3", "expected a positive integer"),
    ("ART_SD_MAX_IMAGE_PIXELS", "0", "expected a positive integer"),
    ("ART_SCHEDULER_INTERVAL_SECONDS", "-1", "expected a positive integer"),
    ("ART_SCHEDULER_LIMIT", "0", "expected a positive integer"),
    ("ART_SD_CFG_SCALE", "fast", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "0", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "-1.5", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "nan", "expected a positive float"),
    ("ART_SD_CFG_SCALE", "inf", "expected a positive float"),
    ("ART_SCHEDULER_ENABLED", "maybe", "1/true/yes/on/0/false/no/off"),
    ("ART_SD_PREPIN_SAMPLES_FORMAT", "2", "1/true/yes/on/0/false/no/off"),
    ("ELOSERN_VUE_CLIENT", "TRUE!", "1/true/yes/on/0/false/no/off"),
    ("ART_SD_PORTRAIT_WIDTH", "777", "expected a positive multiple of 8"),
    ("ART_SD_SCENE_WIDTH", "1001", "expected a positive multiple of 8"),
    ("ART_SD_SCENE_HEIGHT", "0", "expected a positive multiple of 8"),
    ("ART_SD_PORTRAIT_HEIGHT", "-16", "expected a positive multiple of 8"),
    ("ART_SD_OUTPUT_FORMAT", "heic", "expected one of png/webp/jpeg/avif (case-insensitive)"),
    ("ART_SD_OUTPUT_FORMAT", "pngs", "expected one of png/webp/jpeg/avif (case-insensitive)"),
    ("ART_SD_OUTPUT_QUALITY", "0", "expected an integer between 1 and 100"),
    ("ART_SD_OUTPUT_QUALITY", "101", "expected an integer between 1 and 100"),
    ("ART_SD_OUTPUT_QUALITY", "twelve", "expected an integer between 1 and 100"),
    ("ART_SD_PRESERVE_GENERATION_METADATA", "maybe", "1/true/yes/on/0/false/no/off"),
    ("ART_SD_PROBE_TIMEOUT_MS", "999", "expected an integer between 1000 and 60000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "60001", "expected an integer between 1000 and 60000"),
    ("ART_SD_PROBE_TIMEOUT_MS", "twelve", "expected an integer between 1000 and 60000"),
    ("ART_SD_PROBE_CACHE_SECONDS", "4", "expected an integer between 5 and 3600"),
    ("ART_SD_PROBE_CACHE_SECONDS", "3601", "expected an integer between 5 and 3600"),
    ("ART_SD_PROBE_CACHE_SECONDS", "0", "expected an integer between 5 and 3600"),
]

_IMPORT = "import server.conf.settings as s"

BOOL_SETTINGS = [
    "ART_SD_PREPIN_SAMPLES_FORMAT",
    "ART_SD_PRESERVE_GENERATION_METADATA",
    "ART_SCHEDULER_ENABLED",
    "ELOSERN_VUE_CLIENT",
]


def _settings_repr(names: list[str]) -> str:
    """Subprocess snippet printing `NAME <repr(value)>` for each setting."""
    lines = [_IMPORT]
    for name in names:
        lines.append(f"print({name!r}, repr(s.{name}))")
    return "\n".join(lines)


def _printed_map(stdout: str, expected: set[str]) -> dict[str, str]:
    """Parse `NAME <repr>` lines, ignoring the benign `secret_settings.py
    file not found` line that the settings import prints to stdout."""
    printed = {}
    for line in stdout.splitlines():
        name, _, value = line.partition(" ")
        if name in expected:
            printed[name] = value
    return printed


# Every case pre-seeds an EMPTY synthetic secret_settings module so a
# developer's gitignored server/conf/secret_settings.py can never shift the
# effective values under test (the precedence test overwrites this entry with
# a populated module via plain assignment). The production import structure
# is unchanged: settings.py still executes `from server.conf.secret_settings
# import *` at the bottom; the synthetic module simply defines nothing.
_SECRET_ISOLATION_PRELUDE = (
    "import sys\n"
    "import types\n"
    "sys.modules.setdefault(\n"
    "    'server.conf.secret_settings',\n"
    "    types.ModuleType('server.conf.secret_settings'),\n"
    ")\n"
)


class _SubprocessSettingsTests(unittest.TestCase):
    """Shared harness: bare interpreter, curated environment, repo cwd."""

    def _base_env(self) -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key != "DJANGO_SETTINGS_MODULE"
            and not key.startswith("ART_")
            and key not in ("SD_WEBUI_BASE_URL", "ELOSERN_VUE_CLIENT")
        }

    def _run(self, code: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        env = self._base_env()
        env.update(overrides)
        code = _SECRET_ISOLATION_PRELUDE + code
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
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
            "ART_SCHEDULER_ENABLED": "OFF",
            "ELOSERN_VUE_CLIENT": "Yes",
        }
        result = self._run(_settings_repr(BOOL_SETTINGS), **env)
        self.assertEqual(
            _printed_map(result.stdout, set(BOOL_SETTINGS)),
            {
                "ART_SD_PREPIN_SAMPLES_FORMAT": "True",
                "ART_SD_PRESERVE_GENERATION_METADATA": "True",
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


class CodeOnlySeamTests(_SubprocessSettingsTests):
    @covers_requirement(
        "settings-environment-overrides::the-client-seam-and-art-store-root-are-never-environment-configurable"
    )
    def test_hostile_client_seam_and_store_root_variables_are_ignored(self):
        names = ["ART_SD_CLIENT", "ART_STORE_ROOT"]
        env = {
            "ART_SD_CLIENT": "os.system",
            "ART_STORE_ROOT": "/tmp/env-override-art-root",
        }
        result = self._run(_settings_repr(names), **env)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = _printed_map(
            result.stdout, {"ART_SD_CLIENT", "ART_STORE_ROOT"}
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


def _env_read_names(path: str) -> set[str]:
    """Every environment-variable name literal read in a settings module."""
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    names: set[str] = set()
    helper_calls = {
        "_env_str",
        "_env_typed",
        "_env_int",
        "_env_int_bounded",
        "_env_dimension",
        "_env_float",
        "_env_choice",
        "_env_bool",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        fname = (
            func.id
            if isinstance(func, ast.Name)
            else (func.attr if isinstance(func, ast.Attribute) else None)
        )
        if fname in helper_calls and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
        # os.environ.get("NAME", ...) and os.environ.pop("NAME", None)
        if fname in ("get", "pop") and isinstance(func, ast.Attribute):
            base = func.value
            if (
                isinstance(base, ast.Attribute)
                and base.attr == "environ"
                and isinstance(base.value, ast.Name)
                and base.value.id == "os"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                names.add(node.args[0].value)
        # os.environ["NAME"]
        if isinstance(func, ast.Subscript) and isinstance(func.value, ast.Attribute):
            base = func.value
            if (
                base.attr == "environ"
                and isinstance(base.value, ast.Name)
                and base.value.id == "os"
            ):
                index = func.slice
                if isinstance(index, ast.Constant) and isinstance(index.value, str):
                    names.add(index.value)
    return names


def _test_settings_popped_names() -> set[str]:
    tree = ast.parse(open(TEST_SETTINGS_PATH, encoding="utf-8").read())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "_ENV_OVERRIDES"
                for target in node.targets
            )
            and isinstance(node.value, (ast.Tuple, ast.List))
        ):
            return {
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant)
                and isinstance(element.value, str)
            }
    raise AssertionError("_ENV_OVERRIDES tuple not found in test_settings.py")


def _active_env_example_keys() -> set[str]:
    keys = set()
    with open(ENV_EXAMPLE_PATH, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
            if match:
                keys.add(match.group(1))
    return keys


# Reviewed key-to-reader allow-list for keys .env.example may advertise that
# are read OUTSIDE server/conf/settings.py (launcher, compose, harness, CI).
EXTERNAL_READERS: dict[str, str] = {
    "OLLAMA_BASE_URL": "world/ai/profiles.py default_profiles()",
    "PROMPTS_DIR": "compose.yaml bind mount interpolation",
    "CONTAINER_UID": "Containerfile build ARG",
    "IMAGE_TAG": "compose.yaml image tag interpolation",
    "VERSION": "Containerfile/OCI label build ARG",
    "RELEASE": "Containerfile/OCI label build ARG",
    "WEBSOCKET_CLIENT_PROXY_PORT": "evennia.web.utils.general_context",
    "MUD_TEST_SETTINGS": "server/conf/test_settings.py import guard",
    "DJANGO_SETTINGS_MODULE": "evennia launcher / Django bootstrap",
    "TEST_DB_PATH": "evennia.settings_default test database name",
    "OPENSPEC_TEST_EVIDENCE": "tools/spec_traceability evidence records",
    "COVERAGE_FILE": ".github/workflows/quality-gate.yml coverage data file",
}
EXTERNAL_READERS_PREFIXES: dict[str, str] = {
    "EVENNIA_SUPERUSER_": "evennia launcher non-interactive superuser bootstrap",
    "ELOSERN_BROWSER_": "web/tests/browser/ managed browser-test harness",
}


def _env_example_lines() -> list[str]:
    with open(ENV_EXAMPLE_PATH, encoding="utf-8") as handle:
        return handle.read().splitlines()


def _guide_rows() -> list[str]:
    with open(GUIDE_PATH, encoding="utf-8") as handle:
        return [line for line in handle if line.lstrip().startswith("|")]


class InventoryTests(unittest.TestCase):
    """Pure filesystem + AST checks; no subprocess."""

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_settings_ast_reads_exactly_the_env_backed_inventory(self):
        read = _env_read_names(SETTINGS_PATH)
        self.assertEqual(read, set(ENV_BACKED.values()) | {"PROMPT_ROOT"})
        # Belt-and-braces for the security seam: the forbidden names never
        # appear as an argument to ANY call in settings.py, so an aliased or
        # dynamic environment read (env = os.environ; env.get(...)) cannot
        # reintroduce an env path for them outside the shapes above.
        tree = ast.parse(open(SETTINGS_PATH, encoding="utf-8").read())
        call_string_args = {
            node.value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            for arg in [*call.args, *(kw.value for kw in call.keywords)]
            for node in ast.walk(arg)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn("ART_SD_CLIENT", call_string_args)
        self.assertNotIn("ART_STORE_ROOT", call_string_args)
        self.assertNotIn("ART_SD_USERNAME", call_string_args)
        self.assertNotIn("ART_SD_PASSWORD", call_string_args)

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_env_example_advertises_no_dead_variables(self):
        live = set(ENV_BACKED.values()) | {"PROMPT_ROOT"}
        for key in _active_env_example_keys():
            with self.subTest(key=key):
                self.assertTrue(
                    key in live
                    or key in EXTERNAL_READERS
                    or any(
                        key.startswith(prefix)
                        for prefix in EXTERNAL_READERS_PREFIXES
                    ),
                    msg=f"{key} has no reader (settings AST or allow-list)",
                )

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_env_example_documents_every_env_backed_override(self):
        # The typed override examples ship commented (never an uncommented
        # empty typed entry), so completeness must be checked against the
        # COMMENTED assignments too — deleting or renaming one example entry
        # would otherwise silently desync the template from the live AST.
        commented = {
            match.group(1)
            for line in _env_example_lines()
            if (match := re.match(r"^#([A-Za-z_][A-Za-z0-9_]*)=", line))
        }
        missing = set(ENV_BACKED.values()) - commented
        self.assertFalse(missing, msg=f"missing .env.example entries: {missing}")

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_test_settings_override_names_match_the_settings_ast(self):
        self.assertEqual(_test_settings_popped_names(), set(ENV_BACKED.values()))

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_guide_documents_every_env_backed_setting_and_is_linked(self):
        self.assertTrue(os.path.isfile(GUIDE_PATH))
        with open(SIDEBAR_PATH, encoding="utf-8") as handle:
            self.assertIn("/development/settings-and-environment", handle.read())
        rows = _guide_rows()
        for setting, variable in ENV_BACKED.items():
            matching = [
                row
                for row in rows
                if f"`{setting}`" in row and f"`{variable}`" in row
            ]
            self.assertTrue(
                matching,
                msg=f"guide has no table row naming {setting} and {variable}",
            )
            cells = [
                cell.strip()
                for cell in matching[0].strip().strip("|").split("|")
            ]
            self.assertGreaterEqual(
                len(cells),
                5,
                msg=f"guide row for {setting} lacks type/default/rule cells",
            )
            self.assertTrue(
                all(cells), msg=f"guide row for {setting} has an empty cell"
            )
        timeout_rows = [row for row in rows if "`ART_SD_TIMEOUT_SECONDS`" in row]
        self.assertTrue(
            any("600" in row for row in timeout_rows),
            msg="timeout guide row omits its default",
        )
        prepin_rows = [row for row in rows if "`ART_SD_PREPIN_SAMPLES_FORMAT`" in row]
        self.assertTrue(
            any("1/true/yes/on" in row for row in prepin_rows),
            msg="boolean guide row omits the accepted word list",
        )
        for dimension in (
            "ART_SD_SCENE_WIDTH",
            "ART_SD_SCENE_HEIGHT",
            "ART_SD_PORTRAIT_WIDTH",
            "ART_SD_PORTRAIT_HEIGHT",
        ):
            dimension_rows = [row for row in rows if f"`{dimension}`" in row]
            self.assertTrue(
                any("8 倍數" in row or "multiple of 8" in row for row in dimension_rows),
                msg=f"dimension guide row for {dimension} omits the multiple-of-8 rule",
            )
        with open(PROMPTS_DOC_PATH, encoding="utf-8") as handle:
            self.assertIn("settings-and-environment", handle.read())


class ShardOwnershipGuardTests(unittest.TestCase):
    """server/conf/tests/ is owned by the manifest's package-level `server`
    label, which resolves by walking test*.py under the directory; adding an
    entry for this module to .github/evennia-shards.json would BREAK the
    ownership contract (tests.test_evennia_test_optimization_contract)."""

    def test_new_module_path_is_not_listed_in_the_shard_manifest(self):
        manifest_path = os.path.join(REPO_ROOT, ".github", "evennia-shards.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest_text = handle.read()
        self.assertNotIn("test_env_overrides", manifest_text)
