"""Subprocess black-box tests for the LLM knob environment overrides.

Every case imports ``server.conf.settings`` in a bare interpreter with a
curated environment (no ``DJANGO_SETTINGS_MODULE``, no ``LLM_*``/
``OLLAMA_BASE_URL`` leakage from the developer shell, an empty synthetic
``secret_settings`` module unless the case populates one), mirroring the
pattern in ``test_env_overrides.py``. Ownership note: ``server/conf/tests/``
is owned by the shard manifest's package-level ``server`` label, which
resolves by walking ``test*.py`` under the directory — adding this module to
the manifest by name would BREAK the ownership contract.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from server.conf.llm_knobs import (
    LAYER_NAMES,
    LLM_KNOBS,
    llm_env_names,
    llm_global_env_names,
    llm_layer_env_names,
)

from tools.spec_traceability import covers_requirement

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# The 23 documented global names (endpoint design §3.1), written literally so
# a rename in the knob table without a docs/spec update fails here.
DOCUMENTED_GLOBAL_NAMES = frozenset(
    {
        "LLM_BASE_URL",
        "LLM_PATH",
        "LLM_API_KEY",
        "LLM_APP_TITLE",
        "LLM_APP_URL",
        "LLM_MODEL",
        "LLM_TEMPERATURE",
        "LLM_FREQUENCY_PENALTY",
        "LLM_PRESENCE_PENALTY",
        "LLM_TOP_K",
        "LLM_TOP_P",
        "LLM_REPETITION_PENALTY",
        "LLM_MIN_P",
        "LLM_TOP_A",
        "LLM_REASONING_ENABLED",
        "LLM_REASONING_EFFORT",
        "LLM_REASONING_STYLE",
        "LLM_MAX_COMPLETION_TOKENS",
        "LLM_MAX_TOKENS",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
        "LLM_SUPPORTS_RESPONSE_FORMAT",
        "LLM_ENABLED",
    }
)

_SECRET_PRELUDE = (
    "import sys\n"
    "import types\n"
    "sys.modules.setdefault(\n"
    "    'server.conf.secret_settings',\n"
    "    types.ModuleType('server.conf.secret_settings'),\n"
    ")\n"
)

_IMPORT = (
    _SECRET_PRELUDE
    + "import server.conf.settings as s\n"
)


def _raw_field(layer: str, field: str) -> str:
    """Print line + expression fetching the RAW map value with a sentinel."""
    return (
        f"print({layer!r}, {field!r},"
        f" repr(s.LLM_PROFILES[{layer!r}].get({field!r}, '<ABSENT>')))"
    )


def _parse_fields(stdout: str, wanted: set[tuple[str, str]]) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for line in stdout.splitlines():
        parts = line.split(" ")
        if len(parts) == 3 and (parts[0], parts[1]) in wanted:
            found[(parts[0], parts[1])] = parts[2]
    return found


class _LlmSubprocessTests(unittest.TestCase):
    """Shared harness: bare interpreter, LLM-clean environment, repo cwd."""

    def _base_env(self) -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key != "DJANGO_SETTINGS_MODULE"
            and not key.startswith("LLM_")
            and key != "OLLAMA_BASE_URL"
        }

    def _run(self, code: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        env = self._base_env()
        env.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def _fields(
        self, wanted: list[tuple[str, str]], **overrides: str
    ) -> dict[tuple[str, str], str]:
        code = _IMPORT + "\n".join(_raw_field(layer, field) for layer, field in wanted)
        result = self._run(code, **overrides)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return _parse_fields(result.stdout, set(wanted))

    def _assert_fails(self, variable: str, raw: str, *fragments: str) -> None:
        result = self._run(_IMPORT, **{variable: raw})
        self.assertNotEqual(result.returncode, 0, msg=result.stdout)
        self.assertIn("ImproperlyConfigured", result.stderr)
        for fragment in (variable, raw, *fragments):
            self.assertIn(fragment, result.stderr)


class KnobTableTests(unittest.TestCase):
    """Pure in-process checks of the inert generated-name definition."""

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_global_names_equal_the_documented_knob_list_exactly(self):
        self.assertEqual(llm_global_env_names(), DOCUMENTED_GLOBAL_NAMES)
        self.assertEqual(len(llm_global_env_names()), 23)

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_total_name_set_is_globals_plus_per_layer_for_seven_layers(self):
        names = llm_env_names()
        # Exact set equality, never a cardinality count.
        expected = set(DOCUMENTED_GLOBAL_NAMES)
        for layer in LAYER_NAMES:
            expected |= {
                f"LLM_{layer.upper()}_{name.removeprefix('LLM_')}"
                for name in DOCUMENTED_GLOBAL_NAMES
            }
        self.assertEqual(names, frozenset(expected))
        self.assertEqual(len(names), 23 + 23 * 7)
        self.assertEqual(
            llm_layer_env_names("title_nomination"),
            {n for n in names if n.startswith("LLM_TITLE_NOMINATION_")},
        )

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_knob_table_rows_are_unique_and_complete(self):
        suffixes = [knob.suffix for knob in LLM_KNOBS]
        fields = [knob.field for knob in LLM_KNOBS]
        self.assertEqual(len(set(suffixes)), 23)
        self.assertEqual(len(set(fields)), 23)
        self.assertEqual(frozenset(f"LLM_{s}" for s in suffixes), DOCUMENTED_GLOBAL_NAMES)


class DefaultBootTests(_LlmSubprocessTests):
    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_unset_environment_yields_the_documented_profile_defaults(self):
        wanted = [
            ("narrator", "base_url"),
            ("narrator", "path"),
            ("narrator", "model"),
            ("narrator", "temperature"),
            ("narrator", "max_tokens"),
            ("narrator", "timeout_seconds"),
            ("narrator", "max_retries"),
            ("narrator", "enabled"),
            ("narrator", "frequency_penalty"),
            ("narrator", "reasoning_enabled"),
            ("narrator", "api_key"),
            ("action_options", "max_tokens"),
            ("action_options", "supports_response_format"),
            ("title_nomination", "max_tokens"),
        ]
        printed = self._fields(wanted)
        self.assertEqual(printed[("narrator", "base_url")], repr("http://127.0.0.1:11434"))
        self.assertEqual(printed[("narrator", "path")], repr("/v1/chat/completions"))
        self.assertEqual(printed[("narrator", "model")], repr("llama3.2"))
        self.assertEqual(printed[("narrator", "temperature")], repr(0.7))
        self.assertEqual(printed[("narrator", "max_tokens")], "250")
        self.assertEqual(printed[("narrator", "timeout_seconds")], "60")
        self.assertEqual(printed[("narrator", "max_retries")], "2")
        self.assertEqual(printed[("narrator", "enabled")], "True")
        # Presence-driven resolution: unset optionals never enter the raw map.
        self.assertEqual(printed[("narrator", "frequency_penalty")], "'<ABSENT>'")
        self.assertEqual(printed[("narrator", "reasoning_enabled")], "'<ABSENT>'")
        self.assertEqual(printed[("narrator", "api_key")], "'<ABSENT>'")
        self.assertEqual(printed[("action_options", "max_tokens")], "320")
        self.assertEqual(printed[("action_options", "supports_response_format")], "True")
        self.assertEqual(printed[("title_nomination", "max_tokens")], "640")

    @covers_requirement(
        "settings-environment-overrides::environment-inventory-and-configuration-guide-are-version-controlled-and-exact"
    )
    def test_published_name_set_equals_the_inert_definition(self):
        code = (
            _IMPORT
            + "from server.conf.llm_knobs import llm_env_names\n"
            + "print('MATCH', s.LLM_ENV_NAMES == frozenset(llm_env_names()))\n"
            + "print('COUNT', len(s.LLM_ENV_NAMES))\n"
        )
        result = self._run(code)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MATCH True", result.stdout)
        self.assertIn("COUNT 184", result.stdout)


class ValidCoercionTests(_LlmSubprocessTests):
    KNOBS: list[tuple[str, str, str, str]] = [
        # (variable, field, raw, expected repr)
        ("LLM_BASE_URL", "base_url", "http://llm:8000", repr("http://llm:8000")),
        ("LLM_PATH", "path", "/v9/chat", repr("/v9/chat")),
        ("LLM_API_KEY", "api_key", "sk-or-test", repr("sk-or-test")),
        ("LLM_APP_TITLE", "app_title", "Elosern", repr("Elosern")),
        ("LLM_APP_URL", "app_url", "https://example.test", repr("https://example.test")),
        ("LLM_MODEL", "model", "gpt-4o-mini", repr("gpt-4o-mini")),
        ("LLM_TEMPERATURE", "temperature", "1.25", repr(1.25)),
        ("LLM_FREQUENCY_PENALTY", "frequency_penalty", "-1.5", repr(-1.5)),
        ("LLM_PRESENCE_PENALTY", "presence_penalty", "2", repr(2.0)),
        ("LLM_TOP_K", "top_k", "40", "40"),
        ("LLM_TOP_P", "top_p", "0.9", repr(0.9)),
        ("LLM_REPETITION_PENALTY", "repetition_penalty", "1.1", repr(1.1)),
        ("LLM_MIN_P", "min_p", "0.05", repr(0.05)),
        ("LLM_TOP_A", "top_a", "0", repr(0.0)),
        ("LLM_REASONING_EFFORT", "reasoning_effort", "HIGH", repr("high")),
        ("LLM_REASONING_STYLE", "reasoning_style", "Vllm", repr("vllm")),
        ("LLM_MAX_COMPLETION_TOKENS", "max_completion_tokens", "512", "512"),
        ("LLM_MAX_TOKENS", "max_tokens", "300", "300"),
        ("LLM_TIMEOUT_SECONDS", "timeout_seconds", "120", "120"),
        ("LLM_MAX_RETRIES", "max_retries", "0", "0"),
        ("LLM_SUPPORTS_RESPONSE_FORMAT", "supports_response_format", "yes", "True"),
        ("LLM_ENABLED", "enabled", "off", "False"),
    ]

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_every_knob_coerces_its_valid_global_value_into_every_layer(self):
        for variable, field, raw, expected in self.KNOBS:
            with self.subTest(variable=variable, raw=raw):
                printed = self._fields(
                    [("narrator", field), ("title_nomination", field)],
                    **{variable: raw},
                )
                self.assertEqual(printed[("narrator", field)], expected)
                self.assertEqual(printed[("title_nomination", field)], expected)

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_boundary_values_convert(self):
        for variable, raw in (
            ("LLM_TEMPERATURE", "0"),
            ("LLM_TEMPERATURE", "2"),
            ("LLM_FREQUENCY_PENALTY", "-2"),
            ("LLM_FREQUENCY_PENALTY", "2"),
            ("LLM_TOP_P", "1"),
            ("LLM_REPETITION_PENALTY", "0.001"),
            ("LLM_MIN_P", "0"),
            ("LLM_MIN_P", "1"),
            ("LLM_TOP_A", "0"),
            ("LLM_TOP_K", "1"),
            ("LLM_MAX_TOKENS", "1"),
            ("LLM_MAX_RETRIES", "0"),
            ("LLM_MAX_COMPLETION_TOKENS", "1"),
        ):
            with self.subTest(variable=variable, raw=raw):
                result = self._run(_IMPORT, **{variable: raw})
                self.assertEqual(result.returncode, 0, msg=result.stderr)

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_blank_optional_knobs_omit_rather_than_zero(self):
        printed = self._fields(
            [("narrator", "frequency_penalty"), ("narrator", "reasoning_enabled")],
            LLM_FREQUENCY_PENALTY=" ",
            LLM_REASONING_ENABLED="",
        )
        self.assertEqual(printed[("narrator", "frequency_penalty")], "'<ABSENT>'")
        self.assertEqual(printed[("narrator", "reasoning_enabled")], "'<ABSENT>'")

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_blank_required_knobs_fall_through_to_the_code_default(self):
        printed = self._fields(
            [("narrator", "model"), ("narrator", "base_url")],
            LLM_MODEL="",
            LLM_BASE_URL="  ",
        )
        self.assertEqual(printed[("narrator", "model")], repr("llama3.2"))
        self.assertEqual(printed[("narrator", "base_url")], repr("http://127.0.0.1:11434"))

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_reasoning_enabled_is_tri_state(self):
        absent = self._fields([("narrator", "reasoning_enabled")])
        self.assertEqual(absent[("narrator", "reasoning_enabled")], "'<ABSENT>'")
        off = self._fields(
            [("narrator", "reasoning_enabled")], LLM_REASONING_ENABLED="off"
        )
        self.assertEqual(off[("narrator", "reasoning_enabled")], "False")
        on = self._fields(
            [("narrator", "reasoning_enabled")], LLM_REASONING_ENABLED="On"
        )
        self.assertEqual(on[("narrator", "reasoning_enabled")], "True")


class InvalidValueTests(_LlmSubprocessTests):
    CASES: list[tuple[str, str, str]] = [
        # (variable, raw, rule fragment)
        ("LLM_TEMPERATURE", "2.1", "float in 0..2"),
        ("LLM_TEMPERATURE", "twelve", "float in 0..2"),
        ("LLM_TEMPERATURE", "nan", "float in 0..2"),
        ("LLM_FREQUENCY_PENALTY", "-2.5", "float in -2..2"),
        ("LLM_PRESENCE_PENALTY", "3", "float in -2..2"),
        ("LLM_TOP_K", "0", "positive integer"),
        ("LLM_TOP_K", "abc", "positive integer"),
        ("LLM_TOP_P", "1.5", "0 < x <= 1"),
        ("LLM_TOP_P", "0", "0 < x <= 1"),
        ("LLM_REPETITION_PENALTY", "0", "greater than 0"),
        ("LLM_MIN_P", "1.5", "float in 0..1"),
        ("LLM_TOP_A", "-0.1", "non-negative float"),
        ("LLM_REASONING_ENABLED", "maybe", "1/true/yes/on/0/false/no/off"),
        ("LLM_REASONING_EFFORT", "extreme", "minimal/low/medium/high"),
        ("LLM_REASONING_STYLE", "ollama", "openrouter/vllm/off"),
        ("LLM_MAX_COMPLETION_TOKENS", "0", "positive integer"),
        ("LLM_MAX_TOKENS", "0", "positive integer"),
        ("LLM_TIMEOUT_SECONDS", "-5", "positive integer"),
        ("LLM_MAX_RETRIES", "-1", "non-negative integer"),
        ("LLM_SUPPORTS_RESPONSE_FORMAT", "2", "1/true/yes/on/0/false/no/off"),
        ("LLM_ENABLED", "yes please", "1/true/yes/on/0/false/no/off"),
    ]

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_invalid_values_fail_the_boot_naming_variable_raw_and_rule(self):
        for variable, raw, rule in self.CASES:
            with self.subTest(variable=variable, raw=raw):
                self._assert_fails(variable, raw, rule)

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_an_invalid_per_layer_value_fails_even_with_a_valid_global(self):
        result = self._run(
            _IMPORT, LLM_TOP_P="0.9", LLM_NARRATOR_TOP_P="1.5"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LLM_NARRATOR_TOP_P", result.stderr)
        self.assertIn("1.5", result.stderr)


class PrecedenceTests(_LlmSubprocessTests):
    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_a_per_layer_override_wins_over_the_global_value(self):
        printed = self._fields(
            [
                ("character_creation", "model"),
                ("narrator", "model"),
                ("narrator", "temperature"),
            ],
            LLM_MODEL="llama3.2",
            LLM_CHARACTER_CREATION_MODEL="qwen2.5-32b-instruct",
        )
        self.assertEqual(
            printed[("character_creation", "model")], repr("qwen2.5-32b-instruct")
        )
        self.assertEqual(printed[("narrator", "model")], repr("llama3.2"))
        self.assertEqual(printed[("narrator", "temperature")], repr(0.7))

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_a_blank_per_layer_value_falls_through_to_the_global(self):
        printed = self._fields(
            [("narrator", "model")],
            LLM_MODEL="gpt-4o-mini",
            LLM_NARRATOR_MODEL=" ",
        )
        self.assertEqual(printed[("narrator", "model")], repr("gpt-4o-mini"))

    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_per_layer_max_tokens_override_preserves_other_layers(self):
        printed = self._fields(
            [
                ("action_options", "max_tokens"),
                ("title_nomination", "max_tokens"),
                ("narrator", "max_tokens"),
            ],
            LLM_ACTION_OPTIONS_MAX_TOKENS="400",
        )
        self.assertEqual(printed[("action_options", "max_tokens")], "400")
        self.assertEqual(printed[("title_nomination", "max_tokens")], "640")
        self.assertEqual(printed[("narrator", "max_tokens")], "250")


class TestSettingsSanitizationTests(_LlmSubprocessTests):
    @covers_requirement(
        "settings-environment-overrides::llm-profile-knobs-accept-global-and-per-layer-environment-overrides"
    )
    def test_test_settings_pops_every_generated_llm_name(self):
        code = "\n".join(
            [
                "import sys",
                "sys.argv = ['evennia', 'test']",
                "import server.conf.test_settings as t",
                "print('MODEL', repr(t.LLM_PROFILES['narrator']['model']))",
                "print('AOTOK', repr(t.LLM_PROFILES['action_options']['max_tokens']))",
                "print('HOST', repr(t.LLM_PROFILES['narrator']['base_url']))",
            ]
        )
        result = self._run(
            code,
            MUD_TEST_SETTINGS="1",
            LLM_MODEL="poisoned",
            LLM_ACTION_OPTIONS_MAX_TOKENS="999",
            LLM_BASE_URL="http://poisoned:1",
            OLLAMA_BASE_URL="http://old-poison:1",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("MODEL 'llama3.2'", result.stdout)
        self.assertIn("AOTOK 320", result.stdout)
        self.assertIn("HOST 'http://127.0.0.1:11434'", result.stdout)


_SECRET_CHARACTER_CREATION = {
    "base_url": "http://secret:1/v1",
    "path": "/v1/chat/completions",
    "headers": {},
    "model": "secret-model",
    "temperature": 0.5,
    "max_tokens": 111,
    "timeout_seconds": 30,
    "max_retries": 0,
    "supports_response_format": False,
    "enabled": True,
}


class SecretMergeTests(_LlmSubprocessTests):
    """Design D-A7: a secret LLM_PROFILES replaces named layers wholesale and
    leaves every other layer at its environment-resolved entry."""

    def _secret_run(
        self, secret_map: object, **env: str
    ) -> subprocess.CompletedProcess[str]:
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            f"secret.LLM_PROFILES = {secret_map!r}\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            "import server.conf.settings as s\n"
        )
        return self._run(code, **env)

    @covers_requirement(
        "settings-environment-overrides::configuration-layers-follow-default-environment-secret-precedence",
        "llm-profiles::secret-settings-profile-entries-merge-per-layer-over-environment-resolved-defaults",
    )
    def test_a_one_layer_secret_entry_preserves_other_layers_env_values(self):
        secret_map = {"character_creation": dict(_SECRET_CHARACTER_CREATION)}
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            f"secret.LLM_PROFILES = {secret_map!r}\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            "import server.conf.settings as s\n"
            + _raw_field("character_creation", "model")
            + "\n"
            + _raw_field("action_options", "max_tokens")
            + "\n"
            + _raw_field("narrator", "model")
            + "\n"
            + _raw_field("narrator", "base_url")
            + "\n"
        )
        result = self._run(
            code,
            LLM_MODEL="llama3.2",
            LLM_ACTION_OPTIONS_MAX_TOKENS="400",
            LLM_BASE_URL="http://env-host:8000",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = _parse_fields(
            result.stdout,
            {
                ("character_creation", "model"),
                ("action_options", "max_tokens"),
                ("narrator", "model"),
                ("narrator", "base_url"),
            },
        )
        # Secret layer: wholesale from the secret entry.
        self.assertEqual(printed[("character_creation", "model")], repr("secret-model"))
        # Environment layers survive.
        self.assertEqual(printed[("action_options", "max_tokens")], "400")
        self.assertEqual(printed[("narrator", "model")], repr("llama3.2"))
        self.assertEqual(printed[("narrator", "base_url")], repr("http://env-host:8000"))

    @covers_requirement(
        "llm-profiles::secret-settings-profile-entries-merge-per-layer-over-environment-resolved-defaults",
    )
    def test_a_secret_layer_entry_replaces_its_layer_wholesale(self):
        # No field-level merge exists: the environment model reached neither
        # the secret entry nor a partial merge. A secret entry that omits a
        # required field fails the strict construction-time validation naming
        # the layer and field — exactly as a hand-written LLM_PROFILES entry
        # missing the field would (the raw map may not carry None defaults).
        entry = dict(_SECRET_CHARACTER_CREATION)
        del entry["model"]
        result = self._secret_run(
            {"character_creation": entry},
            LLM_CHARACTER_CREATION_MODEL="qwen2.5-32b-instruct",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ProfileValidationError", result.stderr)
        self.assertIn("character_creation", result.stderr)
        self.assertIn("model", result.stderr)
        self.assertNotIn("qwen2.5-32b-instruct", result.stderr)

    @covers_requirement(
        "llm-profiles::secret-settings-profile-entries-merge-per-layer-over-environment-resolved-defaults",
    )
    def test_an_empty_secret_map_is_a_legal_no_op(self):
        printed_lines = self._secret_run({}, LLM_MODEL="gpt-4o-mini")
        self.assertEqual(printed_lines.returncode, 0, msg=printed_lines.stderr)
        code = (
            "import sys\n"
            "import types\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            "secret.LLM_PROFILES = {}\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            "import server.conf.settings as s\n"
            + _raw_field("narrator", "model")
            + "\n"
        )
        result = self._run(code, LLM_MODEL="gpt-4o-mini")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = _parse_fields(result.stdout, {("narrator", "model")})
        self.assertEqual(printed[("narrator", "model")], repr("gpt-4o-mini"))

    @covers_requirement(
        "llm-profiles::secret-settings-profile-entries-merge-per-layer-over-environment-resolved-defaults",
    )
    def test_an_unknown_secret_layer_fails_the_boot(self):
        result = self._secret_run({"not_a_layer": {}})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UnknownLayerError", result.stderr)
        self.assertIn("not_a_layer", result.stderr)


class ShardOwnershipGuardTests(unittest.TestCase):
    """server/conf/tests/ is owned by the manifest's package-level `server`
    label (directory walk); a by-name entry would break the ownership
    contract, mirroring test_env_overrides.ShardOwnershipGuardTests."""

    def test_new_module_path_is_not_listed_in_the_shard_manifest(self):
        manifest_path = os.path.join(REPO_ROOT, ".github", "evennia-shards.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest_text = handle.read()
        self.assertNotIn("test_llm_env_overrides", manifest_text)
