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

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    @covers_requirement("disguised-stats-boundary::disguised-stats-keys-are-readable-by-exactly-three-consumers-including-implemented-guild-registration")
    def test_preset_activation_persists_declared_disguise_without_touching_true_traits(self):
        # Scenario "A declared disguise layer is persisted": the mapping is
        # written inside the activation transaction, and the boundary holds
        # -- true traits are unchanged while the sanctioned accessor shows
        # the disguise.
        from world.rules.traits import get_display_value

        preset = self._synthetic_preset(
            "t_disguised_scout", disguised_stats=(("atk_phys", 99999), ("agility", 99998))
        )
        observed = []
        character = create_object(PlayerCharacter, key="creator-shell-disguise")
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
                write_observer=observed.append,
            )
        self.assertIn("disguised_stats", observed)
        self.assertEqual(
            character.db.disguised_stats, {"atk_phys": 99999, "agility": 99998}
        )
        self.assertEqual(get_display_value(character, "atk_phys"), 99999)
        self.assertEqual(get_display_value(character, "agility"), 99998)
        self.assertNotEqual(
            character.traits.atk_phys.value, character.db.disguised_stats["atk_phys"]
        )
        self.assertNotEqual(
            character.traits.agility.value, character.db.disguised_stats["agility"]
        )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_preset_activation_writes_none_for_an_empty_disguise_declaration(self):
        # Scenario "An empty disguise declaration writes None": the fresh
        # shell already reads None, so the write itself is evidenced through
        # the activation observer; the value stays the absent-reading None.
        preset = self._synthetic_preset("t_plain_scout")
        observed = []
        character = create_object(PlayerCharacter, key="creator-shell-plain")
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
                write_observer=observed.append,
            )
        self.assertIn("disguised_stats", observed)
        self.assertIsNone(character.db.disguised_stats)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    @covers_requirement("sexual-state-handler::sexualstate-is-constructed-from-entity-db-sexual-when-a-raw-baseline-is-present")
    def test_preset_activation_seeds_the_handler_from_a_declared_baseline(self):
        # Scenario "A declared sexual baseline seeds the handler": db.sexual
        # equals to_record(), the lazily constructed entity.sexual derives
        # from it, and each omitted optional field floors through the
        # existing construction rule.
        from world.lore.player_presets import PresetSexualBaseline

        baseline = PresetSexualBaseline(
            arousal="微興奮", virgin=False, sensitivity=(("私處", "極高"),)
        )
        preset = self._synthetic_preset("t_hedonist_scout", sexual_baseline=baseline)
        character = self._activate_synthetic_preset(preset, "creator-shell-baseline")
        self.assertEqual(
            character.db.sexual,
            {"arousal": "微興奮", "virgin": False, "sensitivity": {"私處": "極高"}},
        )
        state = character.sexual
        self.assertFalse(state.virgin)
        self.assertEqual(state.sensitivity["私處"].level, "極高")
        self.assertEqual(state.wetness.level, "乾燥")
        self.assertEqual(state.shame.level, "無")
        self.assertEqual(state.exposure.level, "極低")
        self.assertEqual(state.climax_phase.level, "未達")
        self.assertEqual(state.arousal.level, "微興奮")

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_preset_without_a_baseline_keeps_the_lazy_generic_default(self):
        # Scenario "An undeclared sexual baseline preserves the lazy
        # default": the key stays absent and the generic floor state builds.
        preset = self._synthetic_preset("t_default_scout")
        character = self._activate_synthetic_preset(preset, "creator-shell-default")
        self.assertFalse(character.attributes.has("sexual"))
        state = character.sexual
        self.assertEqual(state.arousal.level, "平靜")
        self.assertTrue(state.virgin)
        self.assertEqual(state.wetness.level, "乾燥")

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_custom_activation_writes_neither_disguise_nor_baseline(self):
        # Task 3.4: custom mode preserves today's behavior exactly -- the
        # disguise layer stays at its shell-initialized None and the sexual
        # attribute is never written.
        observed = []
        activate_player_character(
            self.account, self.character, self.request(),
            write_observer=observed.append,
        )
        self.assertNotIn("disguised_stats", observed)
        self.assertNotIn("sexual", observed)
        self.assertFalse(self.character.attributes.has("sexual"))
        self.assertIsNone(self.character.db.disguised_stats)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_failure_after_both_writes_restores_disguise_and_baseline(self):
        # Scenario "A failed activation leaves no disguise or baseline
        # residue": the observer fails at the ``sexual`` stage, which fires
        # only after both writes landed in the idmapper cache. Restore
        # returns each surface to its PRE-ACTIVATION state: the shell
        # pre-initializes disguised_stats to None (so it reads back None,
        # not absent) and never had a sexual key (so it is removed again);
        # the handler's derived sexual_traits must never have been built.
        from world.lore.player_presets import PresetSexualBaseline

        preset = self._synthetic_preset(
            "t_rolledback_scout",
            disguised_stats=(("atk_phys", 5),),
            sexual_baseline=PresetSexualBaseline(
                arousal="中等", virgin=False, sensitivity=(("耳朵", "高"),)
            ),
        )
        character = create_object(PlayerCharacter, key="creator-shell-rollback")
        self.account.at_post_create_character(character)
        old_key = character.key

        def fail(stage):
            if stage == "sexual":
                raise RuntimeError(stage)

        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            with self.assertRaisesRegex(RuntimeError, "sexual"):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset.key),
                    write_observer=fail,
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        self.assertIsNone(character.attributes.get("disguised_stats"))
        self.assertFalse(character.attributes.has("sexual"))
        self.assertFalse(character.attributes.has("sexual_traits"))
        # The preset provenance attribute is part of the covered snapshot: a
        # rolled-back preset activation leaves no fallback-declaration hint.
        self.assertFalse(character.attributes.has("creation_preset_key"))
