"""Slice of ``test_character_creation``: PresetPersonaLengthSweepTests, PresetValueResolverParityTests, PresetValueResolverPurityTests."""
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
    _live_presets,
)


class PresetPersonaLengthSweepTests(unittest.TestCase):
    """The rules-side sweep enforces the persona prose cap at module import.

    ``world/lore/`` may not import ``world/rules/``, so
    ``MAX_PERSONA_FIELD_LENGTH`` is checked over the registry HERE
    (field-parity design 3.1): every string the persona record can carry —
    top-level prose, identity layers, appearance sub-keys, and both sides of a
    social-connection pair — must fit the cap. The sweep runs on synthetic
    cards; the shipped registry's own conformance is a lore-contract claim in
    ``world/lore/tests/test_player_presets.py``.
    """

    @covers_requirement("player-character-creation::the-preset-registry-declares-a-full-persona-in-import-card-shape")
    def test_registry_sweep_raises_for_over_long_persona_prose(self):
        from world.lore.player_presets import (
            PresetAppearance,
            PresetIdentity,
            PresetPersona,
            PlayerPreset,
        )
        from world.rules.character_creation import (
            _validate_preset_persona_lengths,
        )

        card = make_preset("t_sweep_card")

        def make(persona):
            return {"x": replace(card, persona=persona)}

        over = "長" * (MAX_PERSONA_FIELD_LENGTH + 1)
        ok = "長" * MAX_PERSONA_FIELD_LENGTH
        long_name = "名" * (MAX_PERSONA_FIELD_LENGTH + 1)
        for persona, message in (
            (PresetPersona(personality=over), r"persona\.personality"),
            (PresetPersona(background=over), r"persona\.background"),
            (PresetPersona(identity=PresetIdentity(hidden=over)), r"persona\.identity\.hidden"),
            (PresetPersona(appearance=PresetAppearance(feature=over)), r"persona\.appearance\.feature"),
            (PresetPersona(social_connection=(("甲", over),)), r"persona\.social_connection\.甲"),
            (PresetPersona(social_connection=((long_name, "舊識"),)), r"persona\.social_connection key"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                CharacterCreationError, message
            ):
                _validate_preset_persona_lengths(make(persona))
        # At-bound values pass.
        _validate_preset_persona_lengths(make(
            PresetPersona(personality=ok, background=ok)
        ))


class PresetValueResolverPurityTests(EvenniaTestCase):
    """``resolve_preset_values`` is callable with only a preset and writes nothing.

    Covers the delta scenario "The resolver is pure": one preset argument, no
    account, no character, no database, no world clock.
    """

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_resolver_reads_nothing_but_the_registry_and_writes_nothing(self):
        # Signature: exactly one positional parameter — no account, no character.
        params = list(signature(resolve_preset_values).parameters.values())
        self.assertEqual(
            [(p.name, p.kind) for p in params],
            [("preset", inspect.Parameter.POSITIONAL_OR_KEYWORD)],
        )
        with synthetic_registries(
            "races", "static_tiers", "subraces", "presets", "skills", "items",
            "prices", "elements", "starting_kits",
        ):
            preset = _live_presets()["t_pale_wren"]
            # Zero queries proves no database read and no write; the world-clock
            # accessor always issues a search_script query, so a clock read fails
            # here too. Registries are plain in-memory dicts, so the resolver's
            # only legal inputs cost no queries.
            with self.assertNumQueries(0):
                first = resolve_preset_values(preset)
                second = resolve_preset_values(preset)
        self.assertEqual(first, second)
        # Each call hands back a fresh caller-owned mapping.
        self.assertIsNot(first, second)


class PresetValueResolverParityTests(EvenniaTest):
    """One resolver owns the computation for every in-scope preset."""

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
            "resolver", "resolver@example.test", "testpassword", typeclass=Account
        )

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_resolver_matches_activated_traits_axis_for_axis(self):
        axes = ALLOCATABLE_AXES + ("guild_merit",)
        for preset_key, preset in _live_presets().items():
            with self.subTest(preset=preset_key):
                expected = resolve_preset_values(preset)
                character = create_object(PlayerCharacter, key=f"value-shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                for axis in axes:
                    self.assertEqual(
                        character.traits[axis].value, expected[axis],
                        msg=f"{preset_key}/{axis}",
                    )
                self.assertFalse(character.creation_pending)
