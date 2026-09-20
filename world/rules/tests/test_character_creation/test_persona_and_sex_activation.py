"""Slice of ``test_character_creation``: PersonaActivationTests, SexCreationTests."""
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
    PERSONA_BLOCK,
    _live_presets,
    _race_key,
    balanced_allocations,
)


class PersonaActivationTests(EvenniaTest):
    """Activation-time persona persistence (creation-persona-persistence D3)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
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

    def _prose_card(self, key):
        """A kit card with a fully authored persona (the shipped cards do)."""
        from world.lore.player_presets import PresetPersona

        return replace(
            SYNTH_PRESETS[key],
            key=key,
            persona=PresetPersona(
                personality="端莊內斂",
                background="在王都公會登_record 記的冒險者",
            ),
        )

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_concept_persona_persists_in_the_six_key_import_card_shape(self):
        result = activate_player_character(
            self.account, self.character, self.request(),
            persona=PERSONA_BLOCK,
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(
            self.character.db.persona,
            {
                "identity": {},
                "personality": "沉穩",
                "life_story": "來自邊境的小村，靠磨劍維生",
                "habit": "清晨練劍",
                "appearance": {},
                "social_connection": {},
            },
        )
        self.assertFalse(self.character.creation_pending)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_persona_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key

        def fail(stage):
            if stage == "persona":
                raise RuntimeError("injected persona failure")

        with self.assertRaisesRegex(RuntimeError, "injected persona failure"):
            activate_player_character(
                self.account, self.character, self.request(),
                persona=PERSONA_BLOCK,
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertIsNone(self.character.db.persona)
        self.assertEqual(self.character.traits.all(), [])
        self.assertIsNone(self.character.age)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_draft_without_persona_writes_nothing(self):
        activate_player_character(
            self.account, self.character, self.request()
        )
        self.assertFalse(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_custom_background_is_persisted_inside_the_persona_record(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="在公會登記的新人冒險者"),
        )
        self.assertFalse(self.character.creation_pending)
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "在公會登記的新人冒險者")
        for key in ("identity", "personality", "life_story", "habit",
                    "appearance", "social_connection"):
            self.assertIn(key, stored)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_background_merges_with_a_concept_persona_block(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="背景文字"),
            persona=PERSONA_BLOCK,
        )
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "背景文字")
        self.assertEqual(stored["personality"], "沉穩")
        self.assertEqual(stored["life_story"], "來自邊境的小村，靠磨劍維生")

    def test_blank_or_over_bound_background_is_rejected_or_omitted(self):
        for background in ("  ", "", None):
            with self.subTest(background=background):
                activate_player_character(
                    self.account, self.character,
                    self.request(background=background),
                )
                self.assertFalse(self.character.creation_pending)
                if background in ("  ", "", None):
                    self.assertFalse(self.character.attributes.has("persona"))
                self.character.creation_pending = True
                self.character.attributes.reset_cache()
        with self.assertRaises(CharacterCreationError):
            activate_player_character(
                self.account, self.character,
                self.request(background="x" * (MAX_PERSONA_FIELD_LENGTH + 1)),
            )
        self.assertTrue(self.character.creation_pending)

    def test_malformed_persona_is_rejected_without_mutation(self):
        cases = (
            {"personality": "沉穩", "life_story": "故事"},
            {"personality": "沉穩", "life_story": "故事", "habit": "習慣", "extra": "x"},
            {"personality": "", "life_story": "故事", "habit": "習慣"},
            {
                "personality": "長" * 601,
                "life_story": "故事",
                "habit": "習慣",
            },
            {"personality": 5, "life_story": "故事", "habit": "習慣"},
        )
        for persona in cases:
            with self.subTest(persona=persona), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character, self.request(),
                    persona=persona,
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])
            self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_activation_persists_the_registry_persona_record(self):
        # preset-persona-activation: the registry persona finally reaches
        # entity.db.persona inside the same activation transaction.
        card = self._prose_card("t_pale_wren")
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            self.character.location = self.room1
            activate_player_character(
                self.account, self.character,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(dict(self.character.db.persona), card.persona.to_record())
        self.assertTrue(self.character.db.persona["background"])

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_and_custom_records_carry_the_import_card_key_set_plus_optional_background(self):
        card = self._prose_card("t_ash_finch")
        custom = create_object(PlayerCharacter, key="creator-shell-custom-keys")
        self.account.at_post_create_character(custom)
        activate_player_character(
            self.account, custom, self.request(), persona=PERSONA_BLOCK
        )
        preset_shell = create_object(PlayerCharacter, key="creator-shell-preset-keys")
        self.account.at_post_create_character(preset_shell)
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            activate_player_character(
                self.account, preset_shell,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )
        # The six import-card keys are identical in both modes; ``background``
        # is present in each record only when that source supplied one.
        self.assertEqual(
            set(custom.db.persona), set(PERSONA_IMPORT_CARD_KEYS)
        )
        self.assertEqual(
            set(preset_shell.db.persona),
            set(PERSONA_IMPORT_CARD_KEYS) | {"background"},
        )

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_persona_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key
        card = self._prose_card("t_pale_wren")

        def fail(stage):
            if stage == "persona":
                raise RuntimeError("injected preset persona failure")

        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            with self.assertRaisesRegex(RuntimeError, "injected preset persona failure"):
                activate_player_character(
                    self.account, self.character,
                    CharacterCreationRequest(mode="preset", preset_key=card.key),
                    write_observer=fail,
                )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertIsNone(self.character.db.persona)
        self.assertEqual(self.character.traits.all(), [])
        self.assertIsNone(self.character.db.age)
        self.assertIsNone(self.character.db.skills)
        self.assertIsNone(self.character.db.inventory)

    def test_preset_mode_takes_precedence_over_a_custom_persona_argument(self):
        # ``persona`` is custom-mode only: the shared builder's preset branch
        # wins even if a mixed call hypothetically supplied one, so the
        # registry record can never be silently replaced by draft prose.
        from world.rules.character_creation import _ValidatedCreation, _persona_record_for

        card = self._prose_card("t_ash_finch")
        validated = _ValidatedCreation(
            "暮歌者", 24, 24, card.race, card.subrace, {}
        )
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            record = _persona_record_for(
                validated,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
                PERSONA_BLOCK,
            )
        self.assertEqual(record, card.persona.to_record())
        # The persona argument lost: the prose is the registry card's, not
        # the draft block's.
        self.assertEqual(record["personality"], card.persona.personality)
        self.assertNotEqual(record["personality"], PERSONA_BLOCK["personality"])


class SexCreationTests(EvenniaTest):
    """Optional sex channel: normalize, persist, reject, roll back
    (namegen-creation-ui D1)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "starting_kits",
            "presets",
            "skills",
            "items",
            "prices",
            "elements",
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
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

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_custom_sex_persists_on_the_activated_entity(self):
        activate_player_character(
            self.account, self.character, self.request(sex="female")
        )
        self.assertEqual(self.character.sex, "female")
        self.assertEqual(self.character.attributes.get("sex"), "female")

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    def test_omitted_or_null_sex_normalizes_to_the_default(self):
        for value in ({"sex": None}, {}):
            with self.subTest(value=value):
                character = create_object(PlayerCharacter, key="shell-default")
                self.account.at_post_create_character(character)
                checked = preflight_character_creation(
                    self.account, character, self.request(**value)
                )
                self.assertEqual(checked.sex, DEFAULT_SEX)
                activate_player_character(
                    self.account, character, self.request(**value)
                )
                self.assertEqual(character.sex, DEFAULT_SEX)
                self.assertEqual(character.attributes.get("sex"), DEFAULT_SEX)

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_sex_outside_the_vocabulary_is_rejected_without_mutation(self):
        for value in ("x", "Female", "horse", 5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    CharacterCreationError, "sex must be one of"
                ):
                    activate_player_character(
                        self.account, self.character, self.request(sex=value)
                    )
        self.assertTrue(self.character.creation_pending)
        # The shell's AttributeProperty default persists at object creation;
        # the rejection must leave that prior value untouched.
        self.assertEqual(self.character.attributes.get("sex"), DEFAULT_SEX)
        self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")
    def test_preset_activation_persists_the_declared_sex(self):
        # The preset registry is the source of truth for the sex channel: a
        # preset-mode request (which never carries a sex) must not fall back
        # to DEFAULT_SEX. The every-shipped-card sex fact lives in the
        # registered lore contract; here both kit values (female, male) are
        # exercised against their in-scope cards.
        for preset_key, preset in _live_presets().items():
            with self.subTest(preset=preset_key):
                character = create_object(PlayerCharacter, key=f"shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                self.assertEqual(character.sex, preset.sex)
                self.assertEqual(character.attributes.get("sex"), preset.sex)
                self.assertNotEqual(character.sex, DEFAULT_SEX)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_sex_write_failure_rolls_back_the_whole_activation(self):
        def fail(stage):
            if stage == "sex":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(sex="male"),
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        # Rollback restores the pre-activation snapshot: the creation-time
        # AttributeProperty default, not the rejected write's "male".
        self.assertEqual(self.character.attributes.get("sex"), DEFAULT_SEX)
        self.assertEqual(self.character.traits.all(), [])
