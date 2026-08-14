"""Pure unit tests for the shared blueprint-characterization bound helper.

Covers the per-entry validation rules (``display_name`` bounds, paired
``age``/``apparent_age`` integer/floor/lifespan-band rules, the exactly-one-
``stable_key`` portrait rule, missing-key-vs-``None`` distinction) and the
cross-entry duplicate-``stable_key`` agreement rule, plus the registry-driven
race-lifespan bound resolution.
"""

from dataclasses import FrozenInstanceError
import unittest

from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.quests.characterization import (
    ADULT_MINIMUM,
    MAX_DISPLAY_NAME_LENGTH,
    MAX_STABLE_KEY_LENGTH,
    characterize_errors,
    duplicate_stable_key_errors,
    race_lifespan_upper_bound,
)

from tools.spec_traceability import covers_requirement


def _entry(**overrides):
    entry = {}
    entry.update(overrides)
    return entry


class CharacterizationRaceBoundTests(unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_human_race_bound_resolves_from_the_registry(self):
        bound = race_lifespan_upper_bound("civilian")
        self.assertEqual(bound, RACE_REGISTRY["human"].lifespan[1])
        self.assertEqual(bound, 80)

    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_elven_tier_bound_resolves_to_the_elf_lifespan_band(self):
        bound = race_lifespan_upper_bound("elven_civilian")
        self.assertEqual(bound, RACE_REGISTRY["elf"].lifespan[1])
        self.assertEqual(bound, 1200)

    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_unknown_tier_raises(self):
        with self.assertRaises(KeyError):
            race_lifespan_upper_bound("not_a_tier")


class CharacterizationEntryValidationTests(unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_valid_adult_values_pass(self):
        entry = _entry(
            display_name="莉絲·晨星",
            age=68,
            apparent_age=68,
            portrait={"stable_key": "library_keeper"},
        )
        self.assertEqual(characterize_errors(entry, lifespan_upper_bound=80), [])

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_valid_persona_and_background_pass(self):
        entry = _entry(
            display_name="莉絲·晨星",
            persona={
                "personality": "沉穩",
                "life_story": "守護圖書館多年",
                "habit": "黃昏時整理書架",
            },
            background="來自邊境的旅人",
        )
        self.assertEqual(characterize_errors(entry, lifespan_upper_bound=80), [])

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_over_bound_or_non_text_persona_fields_reject(self):
        cases = (
            {"persona": {"personality": "x" * 601}},
            {"persona": {"personality": ""}},
            {"persona": {"personality": 42}},
            {"persona": "not-an-object"},
            {"background": "x" * 601},
            {"background": 42},
        )
        for entry in cases:
            with self.subTest(entry=entry):
                self.assertTrue(
                    characterize_errors(entry, lifespan_upper_bound=80),
                    entry,
                )

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_duplicate_stable_key_agreement_includes_persona_identity(self):
        base = {
            "display_name": "莉絲·晨星",
            "age": 68,
            "apparent_age": 68,
            "portrait": {"stable_key": "library_keeper"},
            "persona": {"personality": "沉穩"},
        }
        twin = dict(base)
        twin["persona"] = {"personality": "開朗"}
        self.assertEqual(
            duplicate_stable_key_errors([base, base]),
            [],
        )
        errors = duplicate_stable_key_errors([base, twin])
        self.assertEqual(len(errors), 1)
        self.assertIn("conflicting characterization", errors[0])

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_elf_of_several_centuries_passes_within_the_elf_band(self):
        entry = _entry(age=300, apparent_age=300)
        self.assertEqual(characterize_errors(entry, lifespan_upper_bound=1200), [])

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_unpaired_ages_reject(self):
        self.assertTrue(characterize_errors(_entry(age=25), lifespan_upper_bound=80))
        self.assertTrue(
            characterize_errors(_entry(apparent_age=25), lifespan_upper_bound=80)
        )

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_none_valued_key_is_not_an_absence_and_rejects(self):
        self.assertTrue(
            characterize_errors(_entry(age=None, apparent_age=None), lifespan_upper_bound=80)
        )
        self.assertTrue(characterize_errors(_entry(age=25, apparent_age=None), lifespan_upper_bound=80))

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_boolean_and_fractional_ages_reject(self):
        self.assertTrue(characterize_errors(_entry(age=True, apparent_age=25), lifespan_upper_bound=80))
        self.assertTrue(characterize_errors(_entry(age=25, apparent_age=30.5), lifespan_upper_bound=80))

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_underage_value_rejects(self):
        self.assertTrue(characterize_errors(_entry(age=17, apparent_age=17), lifespan_upper_bound=80))

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_race_band_overflow_rejects(self):
        self.assertTrue(characterize_errors(_entry(age=120, apparent_age=120), lifespan_upper_bound=80))
        self.assertTrue(characterize_errors(_entry(age=1300, apparent_age=1300), lifespan_upper_bound=1200))

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_malformed_stable_key_rejects(self):
        for portrait in (
            {"stable_key": ""},
            {"stable_key": "a:b"},
            {"stable_key": "a\x00b"},
            {"stable_key": "a" * (MAX_STABLE_KEY_LENGTH + 1)},
        ):
            with self.subTest(portrait=portrait):
                self.assertTrue(
                    characterize_errors(_entry(portrait=portrait), lifespan_upper_bound=80)
                )

    @covers_requirement("art-stable-key-contract::stable-keys-share-one-producer-contract")
    def test_reserved_separator_stable_keys_reject_like_the_shared_contract(self):
        from world.art.subjects import (
            FORBIDDEN_SUBJECT_KEY_CHARACTERS,
            MAX_SUBJECT_KEY_BYTES,
        )

        for char in sorted(FORBIDDEN_SUBJECT_KEY_CHARACTERS):
            with self.subTest(char=char):
                self.assertTrue(
                    characterize_errors(
                        _entry(portrait={"stable_key": f"a{char}b"}),
                        lifespan_upper_bound=80,
                    )
                )
        with self.subTest(key="over-byte-bound"):
            self.assertTrue(
                characterize_errors(
                    _entry(
                        portrait={
                            "stable_key": "😀" * (MAX_SUBJECT_KEY_BYTES // 4 + 1)
                        }
                    ),
                    lifespan_upper_bound=80,
                )
            )

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_portrait_with_extra_keys_rejects(self):
        self.assertTrue(
            characterize_errors(
                _entry(portrait={"stable_key": "ok", "mode": "named"}),
                lifespan_upper_bound=80,
            )
        )

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_portrait_not_a_mapping_rejects(self):
        for portrait in (None, "library_keeper", ["library_keeper"]):
            with self.subTest(portrait=portrait):
                self.assertTrue(
                    characterize_errors(_entry(portrait=portrait), lifespan_upper_bound=80)
                )

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_display_name_bounds_reject(self):
        self.assertTrue(characterize_errors(_entry(display_name=""), lifespan_upper_bound=80))
        self.assertTrue(characterize_errors(_entry(display_name=42), lifespan_upper_bound=80))
        self.assertTrue(
            characterize_errors(
                _entry(display_name="字" * (MAX_DISPLAY_NAME_LENGTH + 1)),
                lifespan_upper_bound=80,
            )
        )

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_absent_fields_are_a_noop(self):
        self.assertEqual(characterize_errors(_entry(), lifespan_upper_bound=80), [])
        self.assertEqual(
            characterize_errors(_entry(disposition="frightened"), lifespan_upper_bound=80),
            [],
        )


class CharacterizationDuplicateKeyTests(unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_identical_characterization_under_a_shared_key_validates(self):
        entries = [
            _entry(display_name="莉絲·晨星", age=68, apparent_age=68, portrait={"stable_key": "library_keeper"}),
            _entry(display_name="莉絲·晨星", age=68, apparent_age=68, portrait={"stable_key": "library_keeper"}),
        ]
        self.assertEqual(duplicate_stable_key_errors(entries), [])

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_conflicting_characterization_under_a_shared_key_rejects(self):
        entries = [
            _entry(display_name="莉絲·晨星", age=68, apparent_age=68, portrait={"stable_key": "library_keeper"}),
            _entry(display_name="另一個人", age=69, apparent_age=69, portrait={"stable_key": "library_keeper"}),
        ]
        self.assertTrue(duplicate_stable_key_errors(entries))

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_entries_without_a_well_formed_key_are_ignored(self):
        entries = [
            _entry(portrait="malformed"),
            _entry(),
            _entry(portrait={"stable_key": "only_one"}),
        ]
        self.assertEqual(duplicate_stable_key_errors(entries), [])


class CharacterizationAdultFloorConstantTests(unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_adult_floor_is_the_named_constant(self):
        self.assertEqual(ADULT_MINIMUM, 18)


if __name__ == "__main__":
    unittest.main()
