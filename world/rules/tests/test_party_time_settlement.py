"""Party-wide SKIP and movement settlement (party-rest-move-settlement).

Pins the widened settlement scopes: a commander-initiated rest, sleep, wait,
or movement advance settles the present party / travelling party, a member in
another room is never settled, and a failed advance restores every settled
member's gauges, buffs, and practice booking together with the tick. Church,
GM-console, defeat-aftermath, and combat settlements keep their existing
entity tuples.

Intended ``party-time-settlement`` requirement IDs (recorded here until the
capability reaches ``openspec/specs/``, per the party-member-authority
precedent; the decorators are added by the archive/sync step):

- ``party-time-settlement::skip-advances-settle-the-present-party``
- ``party-time-settlement::movement-advances-settle-the-travelling-party``
- ``party-time-settlement::other-advances-keep-their-scope``
- ``party-time-settlement::a-failed-party-advance-restores-every-settled-member``
"""

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
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules import church
from world.rules.buffs import BUFF_DEFINITIONS, apply_buff, entity_active_buffs
from world.rules.buffs.definitions import BuffDefinition
from world.rules.clock import (
    CLOCK_YAML,
    AdvanceSource,
    WorldClock,
    get_world_clock,
    settle_combat_result,
)
from world.rules.defeat_aftermath.aftermath import _recovery_scope
from world.rules.defeat_aftermath.violation import (
    _advance_attempt_clock,
    _violation_scope,
)
from world.rules.gm import advance_clock
from world.rules.movement import charge_movement
from world.rules.party import join_party
from world.rules.possession import enter_possession
from world.rules.time_skip import advance_skip
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

MOVE = CLOCK_YAML["command_defaults"]["move"]
WILDERNESS_MOVE = CLOCK_YAML["command_defaults"]["wilderness_move"]

#: File-local synthetic timed buff: expires inside every advance under test
#: and carries no modifiers, so it never changes gauge arithmetic.
_PROBE_BUFF = "t_party_probe_buff"

#: File-local synthetic ACTIVE skill: a companion's own booking settles and
#: rolls back against this row, never a shipped content key.
_PROBE_SKILL = SYNTH_SKILLS["t_cinder_cleave"].key


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
