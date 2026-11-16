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
from world.tests.geography_fixture import (
    publish_shipped_map_world,
    sync_test_settlements,
)
from world.tests.start_room_fixture import stub_start_room
from world.tests.synthetic_data import (
    SYNTH_ANCHOR_PLACEMENTS,
    SYNTH_ITEMS,
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_START_LOCATIONS,
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


# Placement runs against the synthetic start row, whose anchor placement
# borrows a materialized node of the published map world.
_START_SUBRACE = next(iter(SYNTH_SUBRACES))
_START_MAP_ID = SYNTH_ANCHOR_PLACEMENTS[
    SYNTH_START_LOCATIONS[_START_SUBRACE].anchor_key
].zcoord


def setUpModule():
    publish_shipped_map_world()


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
    "start_locations",
    "anchor_placements",
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
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Runs outside the synthetic scope: the shipped registries are live
        # while the borrowed settlement is materialized.
        sync_test_settlements((_START_MAP_ID,))

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

    def test_fault_after_trait_write_restores_all_state_and_handler_cache(self):
        self.character.db.guild_rank = "preserve-me"
        before_traits = deepcopy(dict(self.character.traits.trait_data))
        old_key = self.character.key

        def fail(stage):
            if stage == "traits":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.db.guild_rank, "preserve-me")
        self.assertEqual(dict(self.character.traits.trait_data), before_traits)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_every_observable_write_failure_restores_the_complete_shell(self):
        stages = (
            "identity", "traits", "age", "apparent_age", "race", "subrace",
            "skill_proficiency", "skills", "skill_grants",
            "equipment", "inventory", "wallet", "quest_log", "guild_rank",
            "creation_pending", "start_location", "portrait_policy",
        )
        for stage in stages:
            with self.subTest(stage=stage):
                character = create_object(PlayerCharacter, key=f"shell-{stage}")
                self.account.at_post_create_character(character)
                character.db.guild_rank = 9
                before = {
                    key: (
                        character.attributes.has(key),
                        deepcopy(character.attributes.get(key)),
                    )
                    for key in (
                        "age", "apparent_age", "race", "subrace",
                        "creation_pending", "skill_proficiency",
                        "skills", "skill_grants", "equipment", "inventory",
                        "wallet", "quest_log", "guild_rank",
                        "portrait_policy", "map_knowledge",
                    )
                }
                before_traits = deepcopy(dict(character.traits.trait_data))
                old_key, old_location = character.key, character.location
                old_home = character.home

                def fail(current, target=stage):
                    if current == target:
                        raise RuntimeError(target)

                with self.assertRaisesRegex(RuntimeError, stage):
                    activate_player_character(
                        self.account, character, self.request(),
                        write_observer=fail,
                    )
                self.assertEqual(character.key, old_key)
                self.assertIs(character.location, old_location)
                self.assertEqual(character.home, old_home)
                self.assertIn(character, self.account.characters)
                self.assertEqual(dict(character.traits.trait_data), before_traits)
                for key, (existed, value) in before.items():
                    self.assertEqual(character.attributes.has(key), existed, key)
                    self.assertEqual(character.attributes.get(key), value, key)

    # -- start-room placement (subrace-start-settlements) --------------------

    def _assert_unplaced(self, character, location, home):
        """The failed activation left the shell exactly where it stood."""
        from evennia.objects.models import ObjectDB

        self.assertTrue(character.creation_pending)
        self.assertIs(character.location, location)
        self.assertEqual(character.home, home)
        self.assertFalse(character.attributes.has("map_knowledge"))
        if location is not None:
            self.assertIn(character, location.contents)
        # Fresh row read: the durable location and home are the originals.
        row = ObjectDB.objects.filter(id=character.id).values(
            "db_location_id", "db_home_id"
        ).get()
        self.assertEqual(row["db_location_id"], getattr(location, "id", None))
        self.assertEqual(row["db_home_id"], getattr(home, "id", None))

    @covers_requirement(
        "player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation",
        "map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams",
    )
    def test_successful_activation_places_the_character_in_its_start_room(self):
        from world.rules.clock import get_world_clock
        from world.rules.map_knowledge import encode_grid
        from world.rules.start_location import resolve_start_room

        room = resolve_start_room(_START_SUBRACE)
        dbref = self.character.dbref
        clock = get_world_clock()
        tick_before = clock.tick
        activate_player_character(self.account, self.character, self.request())
        self.assertFalse(self.character.creation_pending)
        self.assertIsNotNone(self.character.traits.magic_power)
        self.assertEqual(self.character.location, room)
        self.assertEqual(self.character.home, room)
        self.assertIn(self.character, room.contents)
        visited = self.character.attributes.get("map_knowledge")["visited"]
        node = encode_grid(room.xyz[2], int(room.xyz[0]), int(room.xyz[1]))
        self.assertEqual(list(visited), [node])
        self.assertEqual(visited[node]["last_seen_tick"], tick_before)
        self.assertEqual(self.character.dbref, dbref)
        self.assertIn(self.character, self.account.characters)
        self.assertEqual(clock.tick, tick_before)

    def test_preset_activation_lands_in_the_preset_subrace_start_room(self):
        from world.rules.start_location import resolve_start_room

        preset = self._synthetic_preset("t_start_scout")
        self.assertEqual(preset.subrace, _START_SUBRACE)
        character = self._activate_synthetic_preset(preset, "shell-start-preset")
        room = resolve_start_room(_START_SUBRACE)
        self.assertFalse(character.creation_pending)
        self.assertEqual(character.location, room)
        self.assertEqual(character.home, room)

    def test_an_unresolvable_start_room_fails_before_any_write(self):
        from world.rules.scene_visits import ENTERED_ARCHETYPES_ATTRIBUTE
        from world.rules.start_location import StartLocationError

        old_location, old_home = self.character.location, self.character.home
        archetypes = deepcopy(
            self.character.attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE)
        )
        with patch(
            "world.rules.character_creation._run_start_arrival_effects"
        ) as effects, patch(
            "world.rules.start_location.resolve_start_room",
            side_effect=StartLocationError("t_unbuilt"),
        ), self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesRegex(CharacterCreationError, "t_unbuilt"):
                activate_player_character(
                    self.account, self.character, self.request()
                )
        effects.assert_not_called()
        self._assert_unplaced(self.character, old_location, old_home)
        self.assertEqual(self.character.key, "creator-shell")
        self.assertEqual(self.character.traits.all(), [])
        self.assertEqual(
            self.character.attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE), archetypes
        )

    def test_a_failure_after_the_move_returns_the_character_without_hooks(self):
        from typeclasses.characters import Character
        from typeclasses.rooms import LimboRoom
        from world.rules.scene_visits import ENTERED_ARCHETYPES_ATTRIBUTE

        birth = create_object(LimboRoom, key="t_birth")
        for stage in ("start_location", "portrait_policy"):
            with self.subTest(stage=stage):
                # The account hook's default shell typeclass, which the birth
                # room refuses on an ordinary arrival.
                character = create_object(
                    Character, key=f"shell-birth-{stage}", location=birth
                )
                self.account.at_post_create_character(character)
                self.assertIs(character.location, birth)
                # The birth room refuses an ordinary arrival of this shell.
                self.assertTrue(birth.refuses_arrival(character))
                old_home = character.home
                archetypes = deepcopy(
                    character.attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE)
                )

                def fail(current, target=stage):
                    if current == target:
                        raise RuntimeError(target)

                with stub_start_room(), patch(
                    "world.rules.character_creation._run_start_arrival_effects"
                ) as effects, self.captureOnCommitCallbacks(execute=True):
                    with self.assertRaisesRegex(RuntimeError, stage):
                        activate_player_character(
                            self.account, character, self.request(),
                            write_observer=fail,
                        )
                effects.assert_not_called()
                self._assert_unplaced(character, birth, old_home)
                self.assertEqual(
                    character.attributes.get(ENTERED_ARCHETYPES_ATTRIBUTE),
                    archetypes,
                )

    def test_a_failed_placement_of_a_location_less_shell_restores_no_location(self):
        character = create_object(PlayerCharacter, key="shell-nowhere")
        self.account.at_post_create_character(character)
        character.location = None
        old_home = character.home

        def fail(current):
            if current == "start_location":
                raise RuntimeError("start_location")

        with stub_start_room():
            from world.rules import start_location

            stub_room = start_location.resolve_start_room(None)
            with self.assertRaisesRegex(RuntimeError, "start_location"):
                activate_player_character(
                    self.account, character, self.request(), write_observer=fail
                )
        self._assert_unplaced(character, None, old_home)
        self.assertNotIn(character, stub_room.contents)

    def test_arrival_effects_are_isolated_best_effort_steps(self):
        from typeclasses.rooms import Room
        from world.rules.character_creation import _run_start_arrival_effects

        room = create_object(Room, key="t_arrival_room")
        origin = create_object(Room, key="t_arrival_origin")
        self.character.location = room
        with patch.object(
            room, "at_object_receive", side_effect=RuntimeError("receive")
        ) as receive, patch(
            "world.quests.room_observation.observe_arrival_lore"
        ) as lore, patch(
            "world.quests.encounter_dispatch.activate_for_move"
        ) as encounters, patch.object(
            self.character, "msg"
        ) as msg, patch(
            "world.rules.character_creation.log_warn"
        ) as warn:
            _run_start_arrival_effects(self.character, room, origin)
        receive.assert_called_once_with(self.character, origin, move_type="teleport")
        # The failed first step neither raises nor stops the later steps.
        lore.assert_called_once_with(self.character, room)
        encounters.assert_called_once_with(self.character)
        msg.assert_called_once()
        self.assertEqual(msg.call_args.kwargs["text"][1], {"type": "look"})
        warn.assert_called_once()
        self.assertEqual(warn.call_args.args[0], "character_start_arrival_effect_failed")
        self.assertEqual(warn.call_args.kwargs["context"]["step"], "receive")

    def test_a_refused_restore_move_is_logged_and_never_raised(self):
        from typeclasses.rooms import Room
        from world.rules.character_creation import restore_activation_placement

        origin = create_object(Room, key="t_restore_origin")
        elsewhere = create_object(Room, key="t_restore_elsewhere")
        self.character.location = elsewhere
        with patch.object(self.character, "move_to", return_value=False), patch(
            "world.rules.character_creation.log_warn"
        ) as warn:
            restore_activation_placement(self.character, origin)
        warn.assert_called_once()
        self.assertEqual(warn.call_args.args[0], "rollback_restore_failed")
        self.assertEqual(warn.call_args.kwargs["context"]["key"], "location")

    def test_arrival_effects_run_once_after_a_committed_activation(self):
        from world.rules.start_location import resolve_start_room

        origin = self.character.location
        room = resolve_start_room(_START_SUBRACE)
        with patch(
            "world.rules.character_creation._run_start_arrival_effects"
        ) as effects:
            with self.captureOnCommitCallbacks(execute=True):
                activate_player_character(
                    self.account, self.character, self.request()
                )
                effects.assert_not_called()
        effects.assert_called_once_with(self.character, room, origin)

    @covers_requirement("art-gallery-fallback::a-fallback-key-resolves-by-declaration-then-band-then-deterministic-hash")
    def test_preset_activation_persists_the_registry_provenance_attribute(self):
        # The built-in fallback resolver's declaration rung keys off this
        # write: an activated player must carry its preset key so a preset
        # declaration resolves even though the portrait subject is pk-keyed.
        preset = self._synthetic_preset("t_provenance_scout")
        character = self._activate_synthetic_preset(preset, "shell-provenance")
        self.assertEqual(character.attributes.get("creation_preset_key"), preset.key)
        # Custom-mode activation carries nothing.
        self.assertFalse(self.character.attributes.has("creation_preset_key"))
