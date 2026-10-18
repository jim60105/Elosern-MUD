"""Party-wide SKIP, movement, field-cast and item-use settlement.

Pins the widened settlement scopes: a commander-initiated rest, sleep, wait,
or movement advance settles the present party / travelling party, a member in
another room is never settled, and a failed advance restores every settled
member's gauges, buffs, and practice booking together with the tick. An
out-of-combat field cast or item use likewise settles the present party and
rolls every member back on failure. Church, GM-console, defeat-aftermath, and
combat settlements keep their existing entity tuples.

``party-time-settlement`` requirement IDs pinned by the decorators below:

- ``party-time-settlement::skip-advances-settle-the-present-party``
- ``party-time-settlement::movement-advances-settle-the-travelling-party``
- ``party-time-settlement::other-advances-keep-their-scope``
- ``party-time-settlement::a-failed-party-advance-restores-every-settled-member``
- ``party-time-settlement::field-cast-and-item-use-advances-settle-the-present-party``
"""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools.spec_traceability import covers_requirement

from evennia.contrib.grid.wilderness.wilderness import WildernessScript
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.skip import CmdRest, CmdSleep
from typeclasses.entities import LivingEntity
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.rules.action import ActionRequest
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules import church
from world.rules.buffs import BUFF_DEFINITIONS, apply_buff, entity_active_buffs
from world.rules.buffs.definitions import BuffDefinition
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.clock import (
    CLOCK_YAML,
    AdvanceSource,
    EventSourceRegistration,
    WorldClock,
    _EVENT_SOURCES,
    get_world_clock,
    settle_combat_result,
)
from world.rules.defeat_aftermath.aftermath import _recovery_scope
from world.rules.defeat_aftermath.violation import (
    _advance_attempt_clock,
    _violation_scope,
)
from world.rules.gm import advance_clock
from world.rules.items import ItemUseReason, use_item
from world.rules.movement import charge_movement
from world.rules.party import join_party
from world.rules.possession import enter_possession
from world.rules.targeting import RoomActionContext
from world.rules.time_skip import advance_skip
from world.skills.registry import TargetSpec
from world.tests.raw_attributes import raw_attribute_value
from world.tests.synthetic_data import (
    SYNTH_SKILLS,
    make_skill,
    synthetic_registries,
)

from .test_item_use import _support as item_support

MOVE = CLOCK_YAML["command_defaults"]["move"]
WILDERNESS_MOVE = CLOCK_YAML["command_defaults"]["wilderness_move"]

#: File-local synthetic timed buff: expires inside every advance under test
#: and carries no modifiers, so it never changes gauge arithmetic.
_PROBE_BUFF = "t_party_probe_buff"

#: File-local synthetic ACTIVE skill: a companion's own booking settles and
#: rolls back against this row, never a shipped content key.
_PROBE_SKILL = SYNTH_SKILLS["t_cinder_cleave"].key

#: File-local synthetic ACTIVE skill: a zero-cost, effect-free self cast whose
#: only settlement work is the command-time advance under test.
_FIELD_CAST_SKILL = make_skill(
    "t_party_field_probe",
    effects=[],
    target_spec=TargetSpec.SELF,
    cost={},
)


def _raising_stage():
    """A boundary-stage source that always fails after settlement starts."""
    return EventSourceRegistration(
        lambda start, end: (_ for _ in ()).throw(
            RuntimeError("simulated clock boundary failure")
        ),
        None,
    )


def _field_item_scope():
    """The synthetic healing potion and its effect profile for one test."""
    return synthetic_registries(
        "items",
        extra={
            "items": dict(item_support._SCOPE_ITEMS),
            "item_effect_profiles": dict(item_support._SCOPE_PROFILES),
        },
    )


def _gate_anchor_entry():
    """The entry row behind the production east gate, resolved by probe."""
    import importlib

    entries = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    ).values()
    return next(entry for entry in entries if entry.gate_for("w") is not None)


_CAPITAL = _gate_anchor_entry()
_EAST_GATE = _CAPITAL.gate_for("w")
EAST_GATE_XYZ = (*_EAST_GATE.grid_xy, _EAST_GATE.z_map_key)
ENTRY_XY = _CAPITAL.approach_cell(_EAST_GATE)


class _PartySettlementFixture:
    """Synthetic commander/companions, gauges, and a timed probe buff."""

    def _make_companion(self, key, location=None):
        npc = create_object(NPC, key=key, location=self.player.location)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        if location is not None:
            npc.location = location
        return npc

    def _register_probe_buff(self):
        BUFF_DEFINITIONS[_PROBE_BUFF] = BuffDefinition(
            key=_PROBE_BUFF,
            duration=20,
            tick_interval=None,
            stacking="refresh",
            modifiers={},
        )
        self.addCleanup(BUFF_DEFINITIONS.pop, _PROBE_BUFF, None)

    def _set_gauges(self, entity, rates, current=10):
        for key, rate in zip(("hp", "mp", "sp"), rates):
            gauge = getattr(entity.traits, key)
            gauge.current = current
            gauge.rate = rate

    def _fill_gauges(self, entity):
        for key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0

    def _gauges(self, entity):
        return tuple(getattr(entity.traits, key).current for key in ("hp", "mp", "sp"))


class SkipPartySettlementTests(_PartySettlementFixture, EvenniaTest):
    """``rest``/``sleep`` and the shared helper settle the present party."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.room1.key = "Room1"
        self.room1.save()
        self.room2.key = "Room2"
        self.room2.save()
        self.ella = self._make_companion("艾拉")
        self.kahn = self._make_companion("卡恩", location=self.room2)
        self._register_probe_buff()

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    @covers_requirement(
        "party-member-authority::the-present-party-scope-is-ordered-and-room-bound"
    )
    @covers_requirement(
        "party-time-settlement::skip-advances-settle-the-present-party"
    )
    def test_rest_settles_the_present_party_only(self):
        self._set_gauges(self.ella, (0.005, 0.01, 0.015))
        self._set_gauges(self.kahn, (0.005, 0.01, 0.015))
        apply_buff(self.ella, _PROBE_BUFF)
        apply_buff(self.kahn, _PROBE_BUFF)
        before = get_world_clock().tick

        command = CmdRest()
        command.caller = self.player
        command.args = "1h"
        command.func()

        self.assertEqual(get_world_clock().tick - before, 3600)
        # 艾拉 regenerates by her own per-gauge rates and her short buff
        # expires in the same advance.
        self.assertEqual(self._gauges(self.ella), (28, 46, 64))
        self.assertNotIn(_PROBE_BUFF, entity_active_buffs(self.ella))
        # 卡恩 waits in another room: neither gauges nor buff state change.
        self.assertEqual(self._gauges(self.kahn), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.kahn))

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum"
    )
    @covers_requirement(
        "party-time-settlement::skip-advances-settle-the-present-party"
    )
    def test_sleep_derives_its_duration_from_the_caller_only(self):
        self._fill_gauges(self.player)
        self.player.traits.mp.rate = 1.0
        self.player.traits.mp.current = self.player.traits.mp.max - 10
        self._fill_gauges(self.ella)
        self.ella.traits.mp.rate = 1.0
        self.ella.traits.mp.current = 0
        before = get_world_clock().tick

        command = CmdSleep()
        command.caller = self.player
        command.args = ""
        command.func()

        # The caller needs ten seconds; 艾拉 would need a hundred.
        self.assertEqual(get_world_clock().tick - before, 10)
        self.assertEqual(self.ella.traits.mp.current, 10)

    @synthetic_registries("skills")
    @covers_requirement(
        "world-clock::a-rolled-back-advance-restores-every-callback-owned-"
        "surface-not-just-caller-entities"
    )
    @covers_requirement(
        "party-time-settlement::a-failed-party-advance-restores-every-settled-member"
    )
    def test_failed_party_skip_restores_every_member(self):
        import world.rules.clock as clock_module

        self._set_gauges(self.player, (0.005, 0.01, 0.015))
        self._set_gauges(self.ella, (0.005, 0.01, 0.015))
        apply_buff(self.ella, _PROBE_BUFF)
        self.ella.db.practice_booking = _PROBE_SKILL
        before = get_world_clock().tick
        real_run_stages = clock_module._run_stages

        def run_then_raise(clock, seconds, source, entities):
            real_run_stages(clock, seconds, source, entities)
            raise RuntimeError("post-settlement failure")

        with patch("world.rules.clock._run_stages", side_effect=run_then_raise):
            with self.assertRaises(RuntimeError):
                advance_skip(self.player, 3600)

        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self._gauges(self.player), (10, 10, 10))
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.ella))
        self.assertEqual(self.ella.db.practice_booking, _PROBE_SKILL)

    @covers_requirement(
        "world-clock::clock-advance-and-restore-failures-emit-observability-events"
    )
    def test_clock_advance_reports_the_party_scope(self):
        with (
            patch("world.rules.clock.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            advance_skip(self.player, 60)

        info.assert_called_once()
        (event,), kwargs = info.call_args
        self.assertEqual(event, "clock_advance")
        self.assertEqual(kwargs["context"]["scope"], 2)

    @covers_requirement(
        "party-time-settlement::skip-advances-settle-the-present-party"
    )
    def test_possessed_rest_settles_the_whole_present_party_once(self):
        self.kahn.location = self.room1
        enter_possession(self.player, self.ella)
        self._set_gauges(self.player, (0.005, 0.01, 0.015))
        self._set_gauges(self.ella, (0.005, 0.01, 0.015))
        self._set_gauges(self.kahn, (0.005, 0.01, 0.015))
        before = get_world_clock().tick

        command = CmdRest()
        command.caller = self.ella
        command.args = "1h"
        command.func()

        self.assertEqual(get_world_clock().tick - before, 3600)
        # The commander's body, the puppet and the companion settle once each:
        # a duplicated puppet entry would double the regenerated gauges.
        for member in (self.player, self.ella, self.kahn):
            self.assertEqual(self._gauges(member), (28, 46, 64))


class MovementPartySettlementTests(_PartySettlementFixture, EvenniaTest):
    """A successful traversal settles the traverser's travelling party."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.room1.key = "Room1"
        self.room1.save()
        self.room2.key = "Room2"
        self.room2.save()
        self.ella = self._make_companion("艾拉")
        self.kahn = self._make_companion("卡恩", location=self.room2)
        self._register_probe_buff()
        self.door = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-"
        "cost-charging-function"
    )
    @covers_requirement(
        "party-time-settlement::movement-advances-settle-the-travelling-party"
    )
    def test_grid_traversal_settles_followers_not_a_companion_elsewhere(self):
        self._set_gauges(self.ella, (0.5, 1.0, 1.5))
        self._set_gauges(self.kahn, (0.5, 1.0, 1.5))
        apply_buff(self.ella, _PROBE_BUFF)
        apply_buff(self.kahn, _PROBE_BUFF)
        before = get_world_clock().tick

        self.door.at_traverse(self.player, self.room2)

        self.assertIs(self.ella.location, self.room2)
        self.assertEqual(get_world_clock().tick - before, MOVE)
        self.assertEqual(self._gauges(self.ella), (25, 40, 55))
        self.assertNotIn(_PROBE_BUFF, entity_active_buffs(self.ella))
        self.assertEqual(self._gauges(self.kahn), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.kahn))

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-"
        "cost-charging-function"
    )
    @covers_requirement(
        "party-time-settlement::movement-advances-settle-the-travelling-party"
    )
    def test_possessed_traversal_settles_the_whole_travelling_party(self):
        self.kahn.location = self.room1
        enter_possession(self.player, self.ella)
        self._set_gauges(self.player, (0.5, 1.0, 1.5))
        self._set_gauges(self.ella, (0.5, 1.0, 1.5))
        self._set_gauges(self.kahn, (0.5, 1.0, 1.5))
        before = get_world_clock().tick

        self.door.at_traverse(self.ella, self.room2)

        self.assertEqual(get_world_clock().tick - before, MOVE)
        for member in (self.ella, self.player, self.kahn):
            self.assertIs(member.location, self.room2)
            self.assertEqual(self._gauges(member), (25, 40, 55))

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-"
        "cost-charging-function"
    )
    def test_flight_waiver_skips_the_party_advance(self):
        self.player.db.skills = {"active": [], "passive": ["flight"]}
        self._set_gauges(self.ella, (0.5, 1.0, 1.5))
        before = get_world_clock().tick

        charge_movement(
            self.player, "wilderness_move", source_location=self.room1
        )

        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-"
        "persisted-relocation-and-reconciles-every-evennia-cache-surface"
    )
    @covers_requirement(
        "party-time-settlement::a-failed-party-advance-restores-every-settled-member"
    )
    def test_failed_party_movement_restores_every_member(self):
        self._set_gauges(self.player, (0.5, 1.0, 1.5))
        self._set_gauges(self.ella, (0.5, 1.0, 1.5))
        apply_buff(self.ella, _PROBE_BUFF)
        before = get_world_clock().tick
        real_advance = WorldClock.advance

        def advance_then_raise(clock, seconds, source, entities):
            real_advance(clock, seconds, source, entities)
            raise RuntimeError("post-advance failure")

        with patch.object(WorldClock, "advance", advance_then_raise):
            with self.assertRaises(RuntimeError):
                self.door.at_traverse(self.player, self.room2)

        self.assertIs(self.player.location, self.room1)
        self.assertIs(self.ella.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self._gauges(self.player), (10, 10, 10))
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.ella))


class WildernessPartySettlementTests(_PartySettlementFixture, EvenniaTest):
    """Gate entry and ordinary steps settle the whole travelling party."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.room1.key = "Room1"
        self.room1.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [
            exit_obj
            for exit_obj in self.east_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]
        self.player.location = self.east_gate
        self.ella = self._make_companion("艾拉")
        self.kahn = self._make_companion("卡恩")
        self._register_probe_buff()

    def _exit(self, direction):
        return [
            exit_obj
            for exit_obj in self.player.location.exits
            if exit_obj.key == direction
        ][0]

    def _script(self):
        return WildernessScript.objects.get(db_key=WILDERNESS_NAME)

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-"
        "cost-charging-function"
    )
    @covers_requirement(
        "party-time-settlement::movement-advances-settle-the-travelling-party"
    )
    def test_gate_entry_settles_followers(self):
        self._set_gauges(self.ella, (0.001, 0.002, 0.003))
        self._set_gauges(self.kahn, (0.001, 0.002, 0.003))
        apply_buff(self.ella, _PROBE_BUFF)
        before = get_world_clock().tick

        self.gate.at_traverse(self.player, self.east_gate)

        self.assertEqual(self.player.location.coordinates, ENTRY_XY)
        self.assertEqual(self.ella.location.coordinates, ENTRY_XY)
        self.assertEqual(self.kahn.location.coordinates, ENTRY_XY)
        self.assertEqual(get_world_clock().tick - before, WILDERNESS_MOVE)
        self.assertEqual(self._gauges(self.ella), (19, 28, 37))
        self.assertNotIn(_PROBE_BUFF, entity_active_buffs(self.ella))

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-"
        "cost-charging-function"
    )
    @covers_requirement(
        "party-time-settlement::movement-advances-settle-the-travelling-party"
    )
    def test_step_excludes_a_destination_only_companion(self):
        self.gate.at_traverse(self.player, self.east_gate)
        script = self._script()
        target = (ENTRY_XY[0] + 1, ENTRY_XY[1])
        # 卡恩's destination room was recycled: only its registration at the
        # destination cell remains. The step's pooled-room reuse then
        # materializes him into the same room object that represents the
        # source cell, so room identity alone would wrongly count him.
        self.kahn.location = None
        self.kahn.ndb.wilderness = script
        script.db.itemcoordinates[self.kahn] = target
        self._set_gauges(self.ella, (0.001, 0.002, 0.003))
        self._set_gauges(self.kahn, (0.001, 0.002, 0.003))
        apply_buff(self.kahn, _PROBE_BUFF)
        source_room = self.player.location
        calls = []
        real_advance = WorldClock.advance

        def spy(clock, seconds, source, entities):
            calls.append(list(entities))
            return real_advance(clock, seconds, source, entities)

        with patch.object(WorldClock, "advance", spy):
            self._exit("east").at_traverse(self.player, self.player.location)

        # The source room object was reused for the destination cell, yet the
        # charge settled only the source-registered travelling party.
        self.assertIs(self.player.location, source_room)
        self.assertEqual(self.player.location.coordinates, target)
        self.assertEqual(calls[0], [self.player, self.ella])
        self.assertEqual(self._gauges(self.kahn), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.kahn))

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-"
        "persisted-relocation-and-reconciles-every-evennia-cache-surface"
    )
    @covers_requirement(
        "party-time-settlement::a-failed-party-advance-restores-every-settled-member"
    )
    def test_failed_step_restores_every_member_and_excludes_the_destination(self):
        self.gate.at_traverse(self.player, self.east_gate)
        script = self._script()
        target = (ENTRY_XY[0] + 1, ENTRY_XY[1])
        self.kahn.location = None
        self.kahn.ndb.wilderness = script
        script.db.itemcoordinates[self.kahn] = target
        self._set_gauges(self.player, (0.001, 0.002, 0.003))
        self._set_gauges(self.ella, (0.001, 0.002, 0.003))
        self._set_gauges(self.kahn, (0.001, 0.002, 0.003))
        apply_buff(self.ella, _PROBE_BUFF)
        apply_buff(self.kahn, _PROBE_BUFF)
        before = get_world_clock().tick
        source_coordinates = self.player.location.coordinates
        real_advance = WorldClock.advance

        def advance_then_raise(clock, seconds, source, entities):
            real_advance(clock, seconds, source, entities)
            raise RuntimeError("post-advance failure")

        with patch.object(WorldClock, "advance", advance_then_raise):
            with self.assertRaises(RuntimeError):
                self._exit("east").at_traverse(self.player, self.player.location)

        self.assertEqual(self.player.location.coordinates, source_coordinates)
        self.assertEqual(self.ella.location.coordinates, source_coordinates)
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self._gauges(self.player), (10, 10, 10))
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.ella))
        # The destination-only companion was never settled nor moved.
        self.assertEqual(self._gauges(self.kahn), (10, 10, 10))
        self.assertIn(_PROBE_BUFF, entity_active_buffs(self.kahn))
        self.assertEqual(script.db.itemcoordinates.get(self.kahn), target)

    @covers_requirement(
        "party-time-settlement::movement-advances-settle-the-travelling-party"
    )
    def test_possessed_step_settles_the_registered_owner_body_and_companion(self):
        self.gate.at_traverse(self.player, self.east_gate)
        script = self._script()
        source_coordinates = self.player.location.coordinates
        enter_possession(self.player, self.ella)
        self._set_gauges(self.player, (0.001, 0.002, 0.003))
        self._set_gauges(self.ella, (0.001, 0.002, 0.003))
        self._set_gauges(self.kahn, (0.001, 0.002, 0.003))
        before = get_world_clock().tick
        calls = []
        real_advance = WorldClock.advance

        def spy(clock, seconds, source, entities):
            calls.append(list(entities))
            return real_advance(clock, seconds, source, entities)

        with patch.object(WorldClock, "advance", spy):
            self._exit("east").at_traverse(self.ella, self.ella.location)

        # The puppet, the owner's registered body and the companion travel
        # together, so the one advance settles all three in that order.
        self.assertEqual(calls[0], [self.ella, self.player, self.kahn])
        target = (source_coordinates[0] + 1, source_coordinates[1])
        for member in (self.ella, self.player, self.kahn):
            self.assertEqual(member.location.coordinates, target)
            self.assertEqual(self._gauges(member), (19, 28, 37))
            self.assertEqual(script.db.itemcoordinates.get(member), target)
        self.assertEqual(get_world_clock().tick - before, WILDERNESS_MOVE)


class FieldCastPartySettlementTests(_PartySettlementFixture, EvenniaTest):
    """An out-of-combat field cast settles the caster's present party."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.room1.key = "Room1"
        self.room1.save()
        self.room2.key = "Room2"
        self.room2.save()
        self.ella = self._make_companion("艾拉")
        self.kahn = self._make_companion("卡恩", location=self.room2)
        self._register_probe_buff()
        self.player.db.skills = {"active": [_FIELD_CAST_SKILL.key], "passive": []}

    def _request(self):
        return ActionRequest(
            actor=self.player,
            skill_key=_FIELD_CAST_SKILL.key,
            targets=[],
            context=RoomActionContext(self.player.location),
        )

    @synthetic_registries(
        "skills", extra={"skills": {_FIELD_CAST_SKILL.key: _FIELD_CAST_SKILL}}
    )
    @covers_requirement(
        "cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-"
        "world-time-cost-in-one-outer-transaction"
    )
    @covers_requirement(
        "party-time-settlement::field-cast-and-item-use-advances-settle-the-"
        "present-party"
    )
    def test_field_cast_settles_the_present_party_only(self):
        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        self._set_gauges(self.kahn, (1.0, 1.0, 1.0))
        apply_buff(self.ella, _PROBE_BUFF)
        apply_buff(self.kahn, _PROBE_BUFF)
        clock = WorldClock()

        settlement = settle_out_of_combat_cast(self._request(), clock=clock)

        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(clock.tick, 6)
        # The commander and 艾拉 regenerate once each; a duplicated scope
        # entry would double the regenerated gauges.
        self.assertEqual(self._gauges(self.player), (16, 16, 16))
        self.assertEqual(self._gauges(self.ella), (16, 16, 16))
        self.assertEqual(self.ella.buffs.all[_PROBE_BUFF].remaining_seconds, 14)
        # 卡恩 waits in another room: neither gauges nor buff state change.
        self.assertEqual(self._gauges(self.kahn), (10, 10, 10))
        self.assertEqual(self.kahn.buffs.all[_PROBE_BUFF].remaining_seconds, 20)

    @synthetic_registries(
        "skills", extra={"skills": {_FIELD_CAST_SKILL.key: _FIELD_CAST_SKILL}}
    )
    @covers_requirement(
        "cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-"
        "every-touched-evennia-cache-before-the-failure-surfaces"
    )
    def test_failed_field_cast_restores_every_settled_member(self):
        import world.rules.clock as clock_module

        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        apply_buff(self.player, _PROBE_BUFF)
        apply_buff(self.ella, _PROBE_BUFF)
        clock = WorldClock()
        real_run_stages = clock_module._run_stages

        def run_then_raise(clock_self, seconds, source, entities):
            real_run_stages(clock_self, seconds, source, entities)
            raise RuntimeError("post-settlement failure")

        with patch("world.rules.clock._run_stages", side_effect=run_then_raise):
            with self.assertRaises(RuntimeError):
                settle_out_of_combat_cast(self._request(), clock=clock)

        self.assertEqual(clock.tick, 0)
        self.assertEqual(self._gauges(self.player), (10, 10, 10))
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))
        self.assertEqual(self.player.buffs.all[_PROBE_BUFF].remaining_seconds, 20)
        self.assertEqual(self.ella.buffs.all[_PROBE_BUFF].remaining_seconds, 20)

    @synthetic_registries(
        "skills", extra={"skills": {_FIELD_CAST_SKILL.key: _FIELD_CAST_SKILL}}
    )
    @covers_requirement(
        "cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-"
        "every-touched-evennia-cache-before-the-failure-surfaces"
    )
    def test_outer_failure_after_the_advance_restores_every_settled_member(self):
        # The advance itself succeeds here; the failure lands after it returns,
        # so only the cast settlement's OUTER snapshot can restore the party.
        from world.rules.cast_settlement import _snapshot_settlement_state
        from world.rules.party_scope import present_party_scope

        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        apply_buff(self.player, _PROBE_BUFF)
        apply_buff(self.ella, _PROBE_BUFF)
        before_buffs = {
            member.key: deepcopy(member.db.buffs)
            for member in (self.player, self.ella)
        }
        clock = WorldClock()
        snapshot = _snapshot_settlement_state(
            self._request(), clock, present_party_scope(self.player)
        )
        # The widened merge marks every present member, not just the actor.
        self.assertTrue(snapshot.objects[id(self.ella)].refresh_caches)
        real_advance = WorldClock.advance

        def advance_then_raise(clock_self, seconds, source, entities):
            real_advance(clock_self, seconds, source, entities)
            raise RuntimeError("post-advance failure")

        with patch.object(WorldClock, "advance", advance_then_raise):
            with self.assertRaises(RuntimeError):
                settle_out_of_combat_cast(self._request(), clock=clock)

        self.assertEqual(clock.tick, 0)
        for member in (self.player, self.ella):
            self.assertEqual(self._gauges(member), (10, 10, 10))
            self.assertEqual(member.db.buffs, before_buffs[member.key])
            self.assertEqual(
                raw_attribute_value(member, "buffs"), before_buffs[member.key]
            )
            self.assertEqual(
                raw_attribute_value(member, "traits")["hp"]["current"], 10
            )

    @synthetic_registries(
        "skills", extra={"skills": {_FIELD_CAST_SKILL.key: _FIELD_CAST_SKILL}}
    )
    @covers_requirement(
        "world-clock::clock-advance-and-restore-failures-emit-observability-events"
    )
    def test_field_cast_reports_the_party_scope(self):
        with (
            patch("world.rules.clock.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settle_out_of_combat_cast(self._request(), clock=WorldClock())

        info.assert_called_once()
        (event,), kwargs = info.call_args
        self.assertEqual(event, "clock_advance")
        self.assertEqual(kwargs["context"]["scope"], 2)


class FieldItemUsePartySettlementTests(_PartySettlementFixture, EvenniaTest):
    """An out-of-combat item use settles the user's present party."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.room1.key = "Room1"
        self.room1.save()
        self.room2.key = "Room2"
        self.room2.save()
        self.ella = self._make_companion("艾拉")
        self.kahn = self._make_companion("卡恩", location=self.room2)
        self._sources = dict(_EVENT_SOURCES)

        def restore_sources():
            _EVENT_SOURCES.clear()
            _EVENT_SOURCES.update(self._sources)

        self.addCleanup(restore_sources)

    def _use(self, clock):
        self.player.db.inventory = [item_support._TONIC_KEY]
        return use_item(self.player, item_support._TONIC_KEY, clock=clock)

    @_field_item_scope()
    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-"
        "time-once"
    )
    @covers_requirement(
        "party-time-settlement::field-cast-and-item-use-advances-settle-the-"
        "present-party"
    )
    def test_potion_use_settles_the_present_party_once(self):
        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        self._set_gauges(self.kahn, (1.0, 1.0, 1.0))
        clock = WorldClock()

        settlement = self._use(clock)

        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(clock.tick, item_support.ITEM_USE_SECONDS)
        self.assertEqual(self.player.db.inventory, [])
        # The commander and 艾拉 regenerate once each; a duplicated scope
        # entry would double the regenerated gauges.
        self.assertEqual(self.player.traits.mp.current, 16)
        self.assertEqual(self.player.traits.sp.current, 16)
        self.assertEqual(self.ella.traits.mp.current, 16)
        self.assertEqual(self.ella.traits.sp.current, 16)
        # 卡恩 waits in another room: his gauges are untouched.
        self.assertEqual(self._gauges(self.kahn), (10, 10, 10))

    @_field_item_scope()
    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-"
        "time-once"
    )
    @covers_requirement(
        "party-time-settlement::field-cast-and-item-use-advances-settle-the-"
        "present-party"
    )
    def test_rejected_potion_use_settles_nobody(self):
        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        self.player.traits.hp.current = self.player.traits.hp.max
        clock = WorldClock()

        settlement = self._use(clock)

        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, ItemUseReason.HP_FULL)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.player.traits.hp.current, self.player.traits.hp.max)
        self.assertEqual(self.player.traits.mp.current, 10)
        self.assertEqual(self.player.traits.sp.current, 10)
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))
        self.assertEqual(self.player.db.inventory, [item_support._TONIC_KEY])

    @_field_item_scope()
    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-"
        "time-once"
    )
    def test_clock_callback_failure_restores_item_and_both_members(self):
        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        clock = WorldClock()

        with self.assertRaises(RuntimeError):
            self._use(clock)

        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.player.db.inventory, [item_support._TONIC_KEY])
        self.assertEqual(self._gauges(self.player), (10, 10, 10))
        self.assertEqual(self._gauges(self.ella), (10, 10, 10))

    @_field_item_scope()
    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-"
        "time-once"
    )
    def test_outer_failure_after_the_advance_restores_item_and_both_members(self):
        # The advance itself succeeds here; the failure lands after it returns,
        # so only the item-use outer rollback can restore the party and item.
        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        self._set_gauges(self.ella, (1.0, 1.0, 1.0))
        before_buffs = {
            member.key: deepcopy(member.db.buffs)
            for member in (self.player, self.ella)
        }
        clock = WorldClock()
        real_advance = WorldClock.advance

        def advance_then_raise(clock_self, seconds, source, entities):
            real_advance(clock_self, seconds, source, entities)
            raise RuntimeError("post-advance failure")

        with patch.object(WorldClock, "advance", advance_then_raise):
            with self.assertRaises(RuntimeError):
                self._use(clock)

        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.player.db.inventory, [item_support._TONIC_KEY])
        for member in (self.player, self.ella):
            self.assertEqual(self._gauges(member), (10, 10, 10))
            self.assertEqual(member.db.buffs, before_buffs[member.key])
            self.assertEqual(
                raw_attribute_value(member, "buffs"), before_buffs[member.key]
            )
            self.assertEqual(
                raw_attribute_value(member, "traits")["hp"]["current"], 10
            )

    @_field_item_scope()
    @covers_requirement(
        "world-clock::clock-advance-and-restore-failures-emit-observability-events"
    )
    def test_item_use_reports_the_party_scope(self):
        self._set_gauges(self.player, (1.0, 1.0, 1.0))
        with (
            patch("world.rules.clock.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self._use(WorldClock())

        info.assert_called_once()
        (event,), kwargs = info.call_args
        self.assertEqual(event, "clock_advance")
        self.assertEqual(kwargs["context"]["scope"], 2)


class UnchangedSettlementScopeTests(EvenniaTest):
    """Church, GM, defeat aftermath, and combat keep their entity tuples."""

    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="t_church_hall")
        from world.lore.church.places import resolve_church_place_keys

        self.hall.tags.add(next(iter(resolve_church_place_keys())))
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        church.add_merit(self.char1, 0)

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    @covers_requirement(
        "party-time-settlement::other-advances-keep-their-scope"
    )
    def test_church_pray_advance_keeps_its_single_entity_scope(self):
        clock = WorldClock(tick=0)
        calls = []
        real_advance = WorldClock.advance

        def spy(clock_self, seconds, source, entities):
            calls.append((seconds, source, entities))
            return real_advance(clock_self, seconds, source, entities)

        with (
            patch("world.rules.church.get_world_clock", return_value=clock),
            patch.object(WorldClock, "advance", spy),
        ):
            church.pray_step(self.char1)

        self.assertEqual(calls[0][1], AdvanceSource.COMMAND)
        self.assertEqual(calls[0][2], (self.char1,))

    @covers_requirement(
        "world-clock::advance-settles-exactly-the-entities-its-caller-supplies-"
        "never-a-global-registry"
    )
    @covers_requirement(
        "party-time-settlement::other-advances-keep-their-scope"
    )
    def test_gm_console_advance_keeps_the_living_entity_tuple(self):
        clock = Mock()
        with (
            patch("world.rules.gm.read_world_clock", return_value=clock),
            patch.object(
                LivingEntity.objects,
                "all_family",
                return_value=[self.char1],
            ),
        ):
            advance_clock(60)

        clock.advance.assert_called_once_with(
            60, AdvanceSource.GM, (self.char1,)
        )

    @covers_requirement(
        "defeat-aftermath-violation-sequence::each-attempt-advances-the-world-"
        "clock-by-its-declared-duration"
    )
    @covers_requirement(
        "party-time-settlement::other-advances-keep-their-scope"
    )
    def test_defeat_attempt_advance_keeps_its_scope(self):
        self.assertEqual(_violation_scope(self.char1), [])
        self.assertEqual(_recovery_scope(self.char1, None), [self.char1])
        clock = WorldClock(tick=0)
        calls = []
        real_advance = WorldClock.advance

        def spy(clock_self, seconds, source, entities):
            calls.append((seconds, source, list(entities)))
            return real_advance(clock_self, seconds, source, entities)

        with patch.object(WorldClock, "advance", spy):
            _advance_attempt_clock(clock, 60, [self.char1], [])

        self.assertEqual(calls[0][1], AdvanceSource.DEFEAT_AFTERMATH)
        self.assertEqual(calls[0][2], [self.char1])

    @covers_requirement(
        "world-clock::settle-combat-result-is-the-sanctioned-call-site-for-"
        "combat-sourced-advances"
    )
    @covers_requirement(
        "party-time-settlement::other-advances-keep-their-scope"
    )
    def test_settle_combat_result_keeps_its_entity_tuple(self):
        entities = [self.char1]
        with patch("world.rules.clock.get_world_clock") as get_clock:
            settle_combat_result(
                SimpleNamespace(total_seconds=6), entities
            )

        get_clock.return_value.advance.assert_called_once_with(
            6, AdvanceSource.COMBAT, entities
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
