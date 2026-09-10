"""Tests for stable creation-rejection codes and Traditional Chinese messages."""

from unittest.mock import patch
import unittest

from world.rules.character_creation import (
    CharacterCreationError,
    CharacterCreationRequest,
    preflight_character_creation,
    resolve_starting_profile,
)
from world.rules.creation_messages import (
    CREATION_REASON_MESSAGES,
    FALLBACK_CODE,
    FALLBACK_MESSAGE,
    creation_reason,
    rejection_code,
    rejection_message,
)
from world.tests.synthetic_data import make_subrace, synthetic_registries

# Kit race/subrace rows: profile resolution (budget, bounds) reads whatever
# the scoped registries hold; the rejection mapping under test is race-agnostic.
_FOREIGN_BLOOD = make_subrace("t_hollowborn_blooded", race_key="t_hollowborn")


def balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result: dict[str, int] = {}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    if remaining:
        raise AssertionError("profile budget exceeds allocatable spans")
    return result


def request(**overrides):
    values = {
        "mode": "custom",
        "display_name": "測試角色",
        "age": 20,
        "apparent_age": 20,
        "race": "t_duskmari",
        "subrace": "t_duskmari_evensong",
        "allocations": balanced_allocations("t_duskmari", "t_duskmari_evensong"),
    }
    values.update(overrides)
    return CharacterCreationRequest(**values)


class FakeCharacter:
    """Minimal character surface sufficient for preflight validation."""
    creation_pending = True
    key = "pending-shell"


@synthetic_registries(
    "races", "subraces", extra={"subraces": {_FOREIGN_BLOOD.key: _FOREIGN_BLOOD}}
)
class CreationRejectionMappingTests(unittest.TestCase):
    """Every deterministic reason maps to a stable code and safe message."""

    def _code(self, error_message: str) -> str:
        return rejection_code(CharacterCreationError(error_message))

    def test_every_mapped_message_fragment_yields_a_stable_code(self):
        cases = {
            "unknown player preset": "unknown_preset",
            "display name must be text": "invalid_name",
            "display name must contain 1 to 64 characters": "invalid_name",
            "display name contains a control character": "invalid_name",
            "display name contains an Evennia markup delimiter": "markup_delimiter",
            "display name contains a reserved separator": "reserved_separator",
            "age must be an integer from 0 to 10000": "age_out_of_range",
            "apparent_age must be an integer from 0 to 10000": "apparent_age_out_of_range",
            "unknown race 'x'": "unknown_race",
            "race must be a registry key": "unknown_race",
            "unknown subrace 'x'": "unknown_subrace",
            "subrace must be a registry key or omitted": "unknown_subrace",
            "subrace 'foxkin' does not belong to race 'human'": "incompatible_subrace",
            "allocations must contain exactly the seven starting axes": "malformed_allocations",
            "allocation for hp must be an integer from 0 to 100": "out_of_span_allocation",
            "allocations must sum exactly to 224": "off_budget_allocations",
            "character creation is already complete": "already_complete",
            "character is not owned by this account": "ownership_rejected",
            "no creation draft saved": "no_draft",
            "creation mode must be 'preset' or 'custom'": "malformed_request",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(rejection_code(CharacterCreationError(message)), expected)
                self.assertIn(expected, CREATION_REASON_MESSAGES)

    def test_every_mapped_code_has_a_nonempty_zh_message(self):
        for code, message in CREATION_REASON_MESSAGES.items():
            with self.subTest(code=code):
                self.assertTrue(message.strip())

    def test_unknown_or_raw_reason_degrades_to_the_generic_fallback(self):
        self.assertEqual(rejection_code(RuntimeError("boom")), FALLBACK_CODE)
        self.assertEqual(rejection_code("no such stable code"), FALLBACK_CODE)
        self.assertEqual(rejection_message(RuntimeError("boom")), FALLBACK_MESSAGE)
        code, message = creation_reason(RuntimeError("boom"))
        self.assertEqual((code, message), (FALLBACK_CODE, FALLBACK_MESSAGE))

    def test_deterministic_rejections_round_trip_through_preflight(self):
        cases = [
            ("unknown preset", CharacterCreationRequest(mode="preset", preset_key="nope"), "unknown_preset"),
            ("negative age", request(age=-1), "age_out_of_range"),
            ("negative apparent age", request(apparent_age=-1), "apparent_age_out_of_range"),
            ("over-bound age", request(age=10001), "age_out_of_range"),
            ("over-bound apparent age", request(apparent_age=10001), "apparent_age_out_of_range"),
            ("markup name", request(display_name="|rbad|n"), "markup_delimiter"),
            ("separator name", request(display_name="角色/名"), "reserved_separator"),
            (
                "incompatible subrace",
                request(race="t_duskmari", subrace=_FOREIGN_BLOOD.key),
                "incompatible_subrace",
            ),
        ]
        for label, req, expected in cases:
            with self.subTest(label=label):
                with patch(
                    "world.rules.character_creation._owned_character", return_value=True
                ):
                    with self.assertRaises(CharacterCreationError) as ctx:
                        preflight_character_creation(object(), FakeCharacter(), req)
                self.assertEqual(rejection_code(ctx.exception), expected)

    def test_valid_request_passes_and_age_fields_reject_independently(self):
        with patch(
            "world.rules.character_creation._owned_character", return_value=True
        ):
            validated = preflight_character_creation(
                object(), FakeCharacter(), request(age=0, apparent_age=10000)
            )
            self.assertEqual((validated.age, validated.apparent_age), (0, 10000))
            for overrides, expected in (
                ({"age": -1}, "age_out_of_range"),
                ({"apparent_age": -1}, "apparent_age_out_of_range"),
            ):
                with self.subTest(overrides=overrides):
                    with self.assertRaises(CharacterCreationError) as ctx:
                        preflight_character_creation(
                            object(), FakeCharacter(), request(**overrides)
                        )
                    self.assertEqual(rejection_code(ctx.exception), expected)


if __name__ == "__main__":
    unittest.main()
