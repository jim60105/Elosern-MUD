"""Slice of ``test_character_creation``: CharacterActivationTests."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
import inspect
from inspect import signature
from dataclasses import replace
from unittest.mock import patch
import unittest
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import StatModifiers
from world.lore.starting_kits import SubraceStartingKit
from world.lore.sex import DEFAULT_SEX
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_IMPORT_CARD_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_preset_values,
    resolve_starting_profile,
)
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_SUBRACES,
    StaticBand,
    Vitals,
    _SYNTH_ELEMENT,
    make_element,
    make_item,
    make_race,
    make_preset,
    make_subrace,
    make_skill,
    synthetic_registries,
)
from world.skills.registry import SkillPrerequisite
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
)

from ._support import (
    _BEADS_ROW,
    _DEEP_PRESET,
    _LINEAGE_SKILLS,
    _NEUTRAL_WEAPON,
    _PACK_TRINKET,
    _PLATEMAIL_ROW,
    _STRONG_BORN,
    _STRONG_FOLK,
    _kit_inventory,
    _race_key,
    balanced_allocations,
)


@synthetic_registries(
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "presets",
    "skills",
    "items",
    "prices",
    "elements",
    extra={
        "races": {_STRONG_FOLK.key: _STRONG_FOLK},
        "subraces": {_STRONG_BORN.key: _STRONG_BORN},
        "starting_kits": {
            _STRONG_BORN.key: SubraceStartingKit(
                _STRONG_BORN.key, (("t_thorn_knife", 1),)
            )
        },
        "skills": _LINEAGE_SKILLS,
        "presets": {_DEEP_PRESET.key: _DEEP_PRESET},
        "items": {
            _PLATEMAIL_ROW.key: _PLATEMAIL_ROW,
            _BEADS_ROW.key: _BEADS_ROW,
            _NEUTRAL_WEAPON.key: _NEUTRAL_WEAPON,
            _PACK_TRINKET.key: _PACK_TRINKET,
        },
    },
)
@patch.dict(
    "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
    {"t_duskmari": 2, "t_strong_folk": 1},
    clear=True,
)
class CharacterActivationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account("creator", "creator@example.test", "testpassword", typeclass=Account)
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_activation_persists_identity_traits_and_empty_mechanical_state(self):
        race_key = _race_key()
        old_id, old_location = self.character.id, self.character.location
        result = activate_player_character(
            self.account, self.character, self.request()
        )
        # magic_power is static-band-floor + allocation: derived from the
        # scoped race row, never a pinned shipped number.
        profile = resolve_starting_profile(race_key)
        self.assertEqual(
            result.magic_power,
            profile.bounds_dict()["magic_power"][0]
            + self.request().allocations["magic_power"],
        )
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual((self.character.age, self.character.apparent_age), (20, 20))
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.traits.magic_power.value, result.magic_power)
        self.assertEqual(self.character.traits.guild_merit.value, 0)
        self.assertEqual(self.character.db.skills, {"active": [], "passive": []})
        self.assertEqual(
            self.character.db.inventory,
            _kit_inventory(next(iter(SYNTH_SUBRACES))),
        )
        self.assertEqual(self.character.wallet, 0)
        self.assertEqual(self.character.id, old_id)
        self.assertEqual(self.character.location, old_location)
        self.assertIn(self.character, self.account.characters)

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_static_modifiers_apply_once_after_allocation(self):
        # A subrace with deliberately non-zero modifiers: each counter axis
        # reads floor + allocation, then the modifier applies once through
        # the round rule (never a second copy of the base).
        modified = make_subrace("t_clever_folk_kin", static_modifiers=StatModifiers(atk_phys=-0.10, agility=0.40, defense=-0.30))
        with synthetic_registries("races", "subraces", extra={"subraces": {modified.key: modified}}):
            allocations = balanced_allocations(_race_key(), modified.key)
            request = self.request(
                race=_race_key(), subrace=modified.key, allocations=allocations
            )
            checked = preflight_character_creation(self.account, self.character, request)
            profile = resolve_starting_profile(_race_key(), modified.key)
            bounds = profile.bounds_dict()
            for key in ("atk_phys", "agility", "defense"):
                raw = bounds[key][0] + allocations[key]
                expected = round(raw * (1 + getattr(profile.static_modifiers, key)))
                self.assertEqual(checked.values[key], expected)

    def test_under_and_over_budget_rejections_are_non_mutating(self):
        valid = balanced_allocations(_race_key())
        bounds = resolve_starting_profile(_race_key()).bounds_dict()
        for delta in (-1, 1):
            allocations = dict(valid)
            key = next(key for key in ALLOCATABLE_AXES if 0 <= allocations[key] + delta <= bounds[key][1] - bounds[key][0])
            allocations[key] += delta
            with self.subTest(delta=delta), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(allocations=allocations),
                )
            self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_age_name_and_subrace_rejections_are_non_mutating(self):
        foreign = make_subrace("t_outside_blood", race_key="t_not_in_scope")
        requests = (
            self.request(age=-1),
            self.request(apparent_age=10001),
            self.request(display_name="|rbad|n"),
            self.request(subrace=foreign.key),
        )
        with synthetic_registries("subraces", extra={"subraces": {foreign.key: foreign}}):
            for request in requests:
                with self.subTest(request=request), self.assertRaises(CharacterCreationError):
                    activate_player_character(self.account, self.character, request)
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    def test_custom_creation_without_a_subrace_is_rejected(self):
        for missing in (None, "", "  ", "none"):
            with self.subTest(missing=missing):
                request = self.request(subrace=missing)
                with self.assertRaisesRegex(
                    CharacterCreationError, "requires a registered subrace"
                ):
                    activate_player_character(self.account, self.character, request)
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])
                self.assertIsNone(self.character.age)

    def test_display_name_rejects_separators_and_the_shared_length_bound(self):
        for name in ("角色/名", "角色:名", "角色}名", "x" * 65):
            with self.subTest(name=name[:6]), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(display_name=name),
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])

    def test_64_character_display_name_is_accepted(self):
        name = "新" * 64
        result = activate_player_character(
            self.account, self.character,
            self.request(display_name=name),
        )
        self.assertEqual(result.display_name, name)
        self.assertEqual(self.character.key, name)

    def _synthetic_preset(self, key, **overrides):
        from world.lore.player_presets import PlayerPreset

        race_key = _race_key()
        subrace_key = next(iter(SYNTH_SUBRACES))
        values = dict(
            key=key, display_name=f"合成{key}", age=20, apparent_age=20,
            race=race_key, subrace=subrace_key,
            allocations=tuple(balanced_allocations(race_key, subrace_key).items()),
            emphasis="測試", sex="female",
        )
        values.update(overrides)
        return PlayerPreset(**values)

    def _activate_synthetic_preset(self, preset, shell_key):
        """Activate a registry-patched synthetic preset on a fresh shell."""
        character = create_object(PlayerCharacter, key=shell_key)
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
            )
        return character
