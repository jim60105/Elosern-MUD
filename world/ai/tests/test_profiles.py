"""Tests for the per-layer LLM profile registry (llm-profiles)."""

from dataclasses import fields
import importlib
import os
import subprocess
import sys
from types import MappingProxyType
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai.profiles import (
    LAYER_NAMES,
    LLMProfile,
    ProfileValidationError,
    UnknownLayerError,
    build_profiles,
    default_profiles,
    get_profile,
)

from tools.spec_traceability import covers_requirement

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class ProfileDataclassTests(unittest.TestCase):
    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_frozen_dataclass_carries_the_declared_fields(self):
        self.assertEqual(
            [field.name for field in fields(LLMProfile)],
            [
                "base_url",
                "path",
                "headers",
                "model",
                "temperature",
                "max_tokens",
                "timeout_seconds",
                "max_retries",
                "supports_response_format",
                "enabled",
                "api_key",
                "app_title",
                "app_url",
                "frequency_penalty",
                "presence_penalty",
                "top_k",
                "top_p",
                "repetition_penalty",
                "min_p",
                "top_a",
                "reasoning_enabled",
                "reasoning_effort",
                "reasoning_style",
                "max_completion_tokens",
            ],
        )
        profile = LLMProfile(
            base_url="http://127.0.0.1:11434",
            path="/v1/chat/completions",
            headers={"Content-Type": ("application/json",)},
            model="llama3.2",
            temperature=0.7,
            max_tokens=250,
            timeout_seconds=60,
            max_retries=2,
            supports_response_format=False,
            enabled=True,
        )
        with self.assertRaises(Exception):
            profile.base_url = "http://other"
        with self.assertRaises(Exception):
            profile.headers["Content-Type"] = ("text/plain",)

    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_headers_are_frozen_and_detached_from_the_source_dict(self):
        source = {"Content-Type": ["application/json"]}
        profile = LLMProfile(
            base_url="http://127.0.0.1:11434",
            path="/v1/chat/completions",
            headers=source,
            model="m",
            temperature=0.7,
            max_tokens=100,
            timeout_seconds=60,
            max_retries=1,
            supports_response_format=False,
            enabled=True,
        )
        source["Content-Type"].append("text/plain")
        self.assertEqual(profile.headers, {"Content-Type": ("application/json",)})
        with self.assertRaises(TypeError):
            profile.headers["X-New"] = ("x",)

    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_api_key_never_reaches_repr_or_str(self):
        profile = LLMProfile(
            **valid_profile_values(api_key="super-secret-token")
        )
        self.assertNotIn("super-secret-token", repr(profile))
        self.assertNotIn("super-secret-token", str(profile))
        self.assertEqual(profile.api_key, "super-secret-token")

    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_omitted_optional_fields_construct_at_their_omit_defaults(self):
        profile = LLMProfile(**valid_profile_values())
        self.assertEqual(profile.api_key, "")
        self.assertEqual(profile.app_title, "")
        self.assertEqual(profile.app_url, "")
        for name in (
            "frequency_penalty",
            "presence_penalty",
            "top_k",
            "top_p",
            "repetition_penalty",
            "min_p",
            "top_a",
            "reasoning_enabled",
            "reasoning_effort",
            "max_completion_tokens",
        ):
            self.assertIsNone(getattr(profile, name))
        self.assertEqual(profile.reasoning_style, "openrouter")


def valid_profile_values(**overrides):
    values = {
        "base_url": "http://127.0.0.1:11434",
        "path": "/v1/chat/completions",
        "headers": {"Content-Type": ("application/json",)},
        "model": "llama3.2",
        "temperature": 0.7,
        "max_tokens": 250,
        "timeout_seconds": 60,
        "max_retries": 2,
        "supports_response_format": False,
        "enabled": True,
    }
    values.update(overrides)
    return values


def _clean_subprocess_env() -> dict[str, str]:
    """Environment without DJANGO_SETTINGS_MODULE and any LLM knob, so a
    developer shell can never shift settings-import subprocess results."""
    return {
        key: value
        for key, value in os.environ.items()
        if key != "DJANGO_SETTINGS_MODULE"
        and not key.startswith("LLM_")
        and key != "OLLAMA_BASE_URL"
    }


class ProfileValidationTests(unittest.TestCase):
    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_valid_profile_builds(self):
        profile = build_profiles({"narrator": valid_profile_values()})["narrator"]
        self.assertEqual(profile.model, "llama3.2")

    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_direct_construction_fails_closed_on_every_bound(self):
        bad_values = [
            {"base_url": ""},
            {"temperature": float("nan")},
            {"max_tokens": True},
            {"timeout_seconds": 0},
            {"max_retries": -1},
            {"enabled": 1},
            {"headers": {"X": 123}},
            {"frequency_penalty": 2.5},
            {"presence_penalty": -2.5},
            {"top_p": 1.5},
            {"top_p": 0.0},
            {"repetition_penalty": 0.0},
            {"min_p": 1.5},
            {"top_a": -0.1},
            {"top_k": 0},
            {"max_completion_tokens": "10"},
            {"reasoning_enabled": 1},
            {"reasoning_effort": "extreme"},
            {"reasoning_style": "ollama"},
            {"reasoning_style": None},
            {"api_key": None},
            {"app_title": 5},
        ]
        for overrides in bad_values:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ProfileValidationError):
                    LLMProfile(**valid_profile_values(**overrides))

    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_every_failing_bound_raises_a_named_layer_field_error(self):
        cases = {
            "base_url": (None, ""),
            "path": ("", "  "),
            "model": ("", None),
            "temperature": (-0.1, 2.1, float("nan"), float("inf"), True),
            "max_tokens": (0, -1, True, "10"),
            "timeout_seconds": (0, -1, True),
            "max_retries": (-1, True, 1.5),
            "supports_response_format": (0, "yes", None),
            "enabled": (1, "no", None),
            "frequency_penalty": (-2.1, 2.1, float("nan"), True),
            "presence_penalty": (-2.1, 2.1, float("inf")),
            "top_p": (0, -0.1, 1.1, float("nan")),
            "repetition_penalty": (0, -1.0),
            "min_p": (-0.1, 1.1, float("nan")),
            "top_a": (-0.1, float("nan")),
            "top_k": (0, -3, True, "5"),
            "max_completion_tokens": (0, -3, True, "5"),
            "reasoning_enabled": (1, "yes"),
            "reasoning_effort": ("extreme", 3),
            "reasoning_style": ("ollama", "OFF"),
            "api_key": (None, 7),
            "app_title": (None,),
            "app_url": (None,),
        }
        for field, bad_values in cases.items():
            for bad in bad_values:
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(ProfileValidationError) as ctx:
                        build_profiles({"narrator": valid_profile_values(**{field: bad})})
                    self.assertEqual(ctx.exception.layer, "narrator")
                    self.assertEqual(ctx.exception.field, field)

    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_boundary_optional_values_construct(self):
        for field, ok in (
            ("frequency_penalty", -2.0),
            ("frequency_penalty", 2.0),
            ("presence_penalty", 0.0),
            ("top_p", 1.0),
            ("repetition_penalty", 0.001),
            ("min_p", 0.0),
            ("min_p", 1.0),
            ("top_a", 0.0),
            ("top_k", 1),
            ("max_completion_tokens", 1),
            ("reasoning_enabled", False),
            ("reasoning_effort", "minimal"),
            ("reasoning_style", "vllm"),
            ("reasoning_style", "off"),
        ):
            with self.subTest(field=field, ok=ok):
                profile = build_profiles(
                    {"narrator": valid_profile_values(**{field: ok})}
                )["narrator"]
                self.assertEqual(getattr(profile, field), ok)

    @covers_requirement("llm-profiles::credential-bearing-standard-headers-are-rejected-in-profile-headers")
    def test_credential_bearing_header_names_fail_construction(self):
        for name in (
            "Authorization",
            "authorization",
            "AUTHORIZATION",
            "Proxy-Authorization",
            "X-Api-Key",
            "api-key",
        ):
            with self.subTest(name=name):
                with self.assertRaises(ProfileValidationError) as ctx:
                    build_profiles(
                        {
                            "narrator": valid_profile_values(
                                headers={name: ("Bearer super-secret",)}
                            )
                        }
                    )
                self.assertEqual(ctx.exception.layer, "narrator")
                self.assertEqual(ctx.exception.field, "headers")
                self.assertIn("api_key", str(ctx.exception))

    @covers_requirement("llm-profiles::credential-bearing-standard-headers-are-rejected-in-profile-headers")
    def test_non_credential_headers_still_pass(self):
        profile = build_profiles(
            {
                "narrator": valid_profile_values(
                    headers={
                        "X-Title": ("Elosern",),
                        "X-Request-Tag": ("abc",),
                        "HTTP-Referer": ("https://example.test",),
                    }
                )
            }
        )["narrator"]
        self.assertEqual(profile.headers["X-Title"], ("Elosern",))
        self.assertEqual(profile.headers["X-Request-Tag"], ("abc",))
        self.assertEqual(profile.headers["HTTP-Referer"], ("https://example.test",))

    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_headers_key_or_value_not_a_string_fails_construction(self):
        for bad_headers in (
            {123: ("application/json",)},
            {"Content-Type": ("",)},
            {"Content-Type": ()},
            {"Content-Type": (123,)},
            {"Content-Type": None},
            "not-a-mapping",
        ):
            with self.subTest(headers=bad_headers):
                with self.assertRaises(ProfileValidationError):
                    build_profiles({"narrator": valid_profile_values(headers=bad_headers)})

    @covers_requirement("llm-profiles::startup-profile-validation-is-strict")
    def test_headers_string_value_is_normalized_to_a_tuple(self):
        profile = build_profiles(
            {"narrator": valid_profile_values(headers={"Content-Type": "application/json"})}
        )["narrator"]
        self.assertEqual(profile.headers, {"Content-Type": ("application/json",)})


class RegistryTests(unittest.TestCase):
    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_every_layer_resolves_to_a_complete_profile(self):
        profiles = build_profiles({})
        self.assertEqual(set(profiles), set(LAYER_NAMES))
        for layer in LAYER_NAMES:
            profile = profiles[layer]
            self.assertIsInstance(profile, LLMProfile)
            self.assertTrue(profile.base_url)
            self.assertTrue(profile.path)
            self.assertTrue(profile.model)

    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_unknown_layer_key_is_rejected(self):
        with self.assertRaises(UnknownLayerError):
            build_profiles({"bogus": valid_profile_values()})

    def test_duplicate_layer_key_is_rejected(self):
        with self.assertRaises(ProfileValidationError) as ctx:
            build_profiles(
                [("narrator", valid_profile_values()), ("narrator", valid_profile_values())]
            )
        self.assertEqual(ctx.exception.layer, "narrator")

    def test_module_import_is_side_effect_free(self):
        before = os.environ.copy()
        importlib.import_module("world.ai.profiles")
        self.assertEqual(os.environ, before)

    @covers_requirement("llm-client::local-first-default-endpoint-from-the-environment", "ai-action-options-prompts::layer-names-gains-the-action-options-slot-with-structured-output-defaults")
    def test_default_profiles_target_local_ollama_by_default(self):
        profiles = build_profiles(default_profiles())
        for layer in LAYER_NAMES:
            self.assertEqual(profiles[layer].base_url, "http://127.0.0.1:11434")
            self.assertEqual(profiles[layer].path, "/v1/chat/completions")
            self.assertTrue(profiles[layer].enabled)
            # Optional endpoint fields sit at their omit defaults.
            self.assertIsNone(profiles[layer].frequency_penalty)
            self.assertIsNone(profiles[layer].reasoning_enabled)
            self.assertEqual(profiles[layer].reasoning_style, "openrouter")
            self.assertEqual(profiles[layer].api_key, "")
            if layer == "action_options":
                self.assertTrue(profiles[layer].supports_response_format)
                self.assertEqual(profiles[layer].max_tokens, 320)
            elif layer == "title_nomination":
                self.assertEqual(profiles[layer].max_tokens, 640)
            else:
                self.assertFalse(profiles[layer].supports_response_format)
                self.assertEqual(profiles[layer].max_tokens, 250)

    @covers_requirement("llm-profiles::default-profiles-are-injected-not-environment-read")
    def test_injected_defaults_merge_over_code_defaults(self):
        with patch.dict(
            os.environ,
            {"LLM_MODEL": "poisoned-from-environment"},
        ):
            profiles = build_profiles(
                default_profiles(
                    defaults={"character_creation": {"model": "qwen2.5-32b-instruct"}}
                )
            )
        self.assertEqual(
            profiles["character_creation"].model, "qwen2.5-32b-instruct"
        )
        for layer in LAYER_NAMES:
            if layer != "character_creation":
                self.assertEqual(profiles[layer].model, "llama3.2")

    @covers_requirement("llm-profiles::default-profiles-are-injected-not-environment-read")
    def test_invalid_injected_values_still_fail_closed(self):
        with self.assertRaises(ProfileValidationError) as ctx:
            default_profiles(defaults={"narrator": {"top_p": 1.5}})
        self.assertEqual(ctx.exception.layer, "narrator")
        self.assertEqual(ctx.exception.field, "top_p")

    @covers_requirement("llm-profiles::default-profiles-are-injected-not-environment-read")
    def test_unknown_injected_layer_is_rejected(self):
        with self.assertRaises(UnknownLayerError):
            default_profiles(defaults={"bogus": {"model": "m"}})

    @covers_requirement("llm-profiles::default-profiles-are-injected-not-environment-read")
    def test_profiles_module_source_performs_no_environment_reads(self):
        source = open(
            os.path.join(REPO_ROOT, "world", "ai", "profiles.py"), encoding="utf-8"
        ).read()
        self.assertNotIn("os.environ", source)
        self.assertNotIn("import os", source)
        self.assertNotIn("OLLAMA", source)

    @covers_requirement("llm-client::local-first-default-endpoint-from-the-environment", "settings-environment-overrides::the-base-url-environment-reader-is-the-settings-module")
    def test_llm_base_url_selects_the_compose_host_via_settings(self):
        code = (
            "import sys, types\n"
            "sys.modules.setdefault('server.conf.secret_settings',"
            " types.ModuleType('server.conf.secret_settings'))\n"
            "import server.conf.settings as s\n"
            "print(s.LLM_PROFILES['narrator']['base_url'])\n"
        )
        env = _clean_subprocess_env()
        env["LLM_BASE_URL"] = "http://host.containers.internal:11434"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("http://host.containers.internal:11434", result.stdout)

    @covers_requirement("settings-environment-overrides::the-base-url-environment-reader-is-the-settings-module")
    def test_the_old_variable_name_is_inert(self):
        code = (
            "import sys, types\n"
            "sys.modules.setdefault('server.conf.secret_settings',"
            " types.ModuleType('server.conf.secret_settings'))\n"
            "import server.conf.settings as s\n"
            "print(s.LLM_PROFILES['narrator']['base_url'])\n"
        )
        env = _clean_subprocess_env()
        env["OLLAMA_BASE_URL"] = "http://old-host:11434"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("http://127.0.0.1:11434", result.stdout)
        self.assertNotIn("old-host", result.stdout)


class GetProfileTests(unittest.TestCase):
    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_get_profile_reads_settings_and_resolves_every_layer(self):
        with override_settings(LLM_PROFILES=default_profiles()):
            for layer in LAYER_NAMES:
                profile = get_profile(layer)
                self.assertIsInstance(profile, LLMProfile)

    @covers_requirement("llm-profiles::per-layer-profile-registry")
    def test_get_profile_rejects_unknown_layer(self):
        with override_settings(LLM_PROFILES=default_profiles()):
            with self.assertRaises(UnknownLayerError):
                get_profile("bogus")

    def test_get_profile_merges_missing_layers_from_defaults(self):
        partial = {"narrator": dict(default_profiles()["narrator"], model="override")}
        with override_settings(LLM_PROFILES=partial):
            self.assertEqual(get_profile("narrator").model, "override")
            self.assertEqual(get_profile("scene_builder").model, "llama3.2")

    @covers_requirement("llm-profiles::profiles-are-locally-disableable")
    def test_disabled_profile_is_preserved_not_clamped(self):
        raw = default_profiles()
        raw["narrator"]["enabled"] = False
        with override_settings(LLM_PROFILES=raw):
            self.assertFalse(get_profile("narrator").enabled)
            self.assertTrue(get_profile("scene_builder").enabled)


class ActionOptionsProfileTests(unittest.TestCase):
    """The action_options slot and its structured-output requirement."""

    @covers_requirement("ai-action-options-prompts::layer-names-gains-the-action-options-slot-with-structured-output-defaults")
    def test_action_options_is_a_registered_layer(self):
        self.assertIn("action_options", LAYER_NAMES)
        profiles = build_profiles(default_profiles())
        self.assertIsInstance(profiles["action_options"], LLMProfile)

    @covers_requirement("ai-action-options-prompts::layer-names-gains-the-action-options-slot-with-structured-output-defaults")
    def test_action_options_defaults_support_structured_output(self):
        profile = build_profiles(default_profiles())["action_options"]
        self.assertTrue(profile.supports_response_format)
        self.assertEqual(profile.max_tokens, 320)
        self.assertEqual(profile.temperature, 0.7)

    @covers_requirement("ai-action-options-prompts::construction-time-validation-rejects-a-structured-output-disabled-action-options-profile-at-settings-load")
    def test_action_options_disabled_structured_output_is_rejected(self):
        raw = default_profiles()
        raw["action_options"]["supports_response_format"] = False
        with self.assertRaises(ProfileValidationError) as ctx:
            build_profiles(raw)
        self.assertEqual(ctx.exception.layer, "action_options")
        self.assertEqual(ctx.exception.field, "supports_response_format")

    @covers_requirement("ai-action-options-prompts::construction-time-validation-rejects-a-structured-output-disabled-action-options-profile-at-settings-load")
    def test_other_layers_may_disable_structured_output(self):
        raw = default_profiles()
        raw["narrator"]["supports_response_format"] = False
        profiles = build_profiles(raw)
        self.assertFalse(profiles["narrator"].supports_response_format)
        self.assertTrue(profiles["action_options"].supports_response_format)

    @covers_requirement("ai-action-options-prompts::construction-time-validation-rejects-a-structured-output-disabled-action-options-profile-at-settings-load")
    def test_settings_import_validation_fails_at_startup(self):
        code = (
            "import world.ai.profiles as profiles\n"
            "raw = profiles.default_profiles()\n"
            "raw['action_options']['supports_response_format'] = False\n"
            "profiles.default_profiles = lambda **kw: raw\n"
            "import server.conf.settings\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            env=_clean_subprocess_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ProfileValidationError", result.stderr)
        self.assertIn("action_options", result.stderr)
        self.assertIn("supports_response_format", result.stderr)

    @covers_requirement("ai-action-options-prompts::construction-time-validation-rejects-a-structured-output-disabled-action-options-profile-at-settings-load")
    def test_settings_import_validates_the_effective_map_after_secret_overrides(self):
        code = (
            "import sys\n"
            "import types\n"
            "import world.ai.profiles as profiles\n"
            "raw = profiles.default_profiles()\n"
            "raw['action_options']['supports_response_format'] = False\n"
            "secret = types.ModuleType('server.conf.secret_settings')\n"
            "secret.LLM_PROFILES = raw\n"
            "sys.modules['server.conf.secret_settings'] = secret\n"
            "import server.conf.settings\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            env=_clean_subprocess_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ProfileValidationError", result.stderr)
        self.assertIn("action_options", result.stderr)
        self.assertIn("supports_response_format", result.stderr)

    @covers_requirement("ai-action-options-prompts::layer-names-gains-the-action-options-slot-with-structured-output-defaults")
    def test_effective_settings_expose_the_action_options_slot(self):
        from django.conf import settings as django_settings

        raw = getattr(django_settings, "LLM_PROFILES", None)
        self.assertIsNotNone(raw)
        self.assertIn("action_options", raw)
        self.assertTrue(raw["action_options"]["supports_response_format"])
        self.assertEqual(raw["action_options"]["max_tokens"], 320)
