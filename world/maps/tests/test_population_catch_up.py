"""Behaviour tests: an action catches a lagging unit up before it reads it.

Every scenario is built from the synthetic two-zone world of
:func:`build_two_zone_world`; no shipped zone, site, composition or individual
is named, and no test asserts wall-clock time or hardware speed. The proof is
equality of state: a catch-up leaves the world exactly as one scoped pass over
the same set leaves it, a failed catch-up leaves every cached and durable value
as it was, and a current set is left untouched.

The synthetic world holds two settlement units, so "within the sight radius"
and "farther than the sight radius" are proven with the same second zone at two
player positions: the radius predicate is uniform over cells, which is what the
requirement states and what excludes any unit outside the radius.
"""

from __future__ import annotations

from unittest.mock import patch

from django.db import transaction
from django.test import override_settings

from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
from evennia.utils.create import create_object

from commands.localized.general import CmdLook

from typeclasses.characters import PlayerCharacter

from world.maps import (
    gm as map_gm,
    population_lifecycle,
    population_units,
    regional_population,
)
from world.maps.population_lifecycle import (
    ensure_locations_current,
    settle_population_scope,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_scoped_population_settlement import (
    ORDINARY,
    ScopedSettlementFixture,
    WANDER_A,
    WANDER_B,
    ZONE_A,
    ZONE_B,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import WorldClock, get_world_clock
from world.rules import gm as rules_gm
from world.rules.movement_edges import LocationRef, resolve_direction_edge
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS

START = 100
#: The tick a lagging unit has not settled: the world tick the test sets.
LAG_TICK = 700

SPECIES = next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key

#: One zone-A cell more than the sight radius away from every zone-B cell.
WEST_OF_ZONE_A = (505, 703)
#: One zone-A cell within a single step of zone B's western column.
EAST_OF_ZONE_A = (519, 703)


def place_player(fixture, cell: tuple[int, int]) -> PlayerCharacter:
    """Create a player character registered on one wilderness cell.

    The registration is the same one the fixture gives a monster: the live
    wilderness registration the movement owner reads, plus the pooled room when
    the cell is already materialized. Later changes import this helper.
    """
    player = create_object(PlayerCharacter, key="catch_up_traveller")
    player.ndb.wilderness = fixture.wilderness
    fixture.wilderness.db.itemcoordinates[player] = cell
    room = (fixture.wilderness.db.rooms or {}).get(cell)
    if room is not None:
        player.location = room
        room.contents_cache.add(player)
    return player


def _drop_attribute_caches(*entities) -> None:
    """Force the next read to come from the database, not a live cache."""
    for entity in entities:
        entity.attributes.reset_cache()
    for entity in entities[1:]:
        # The TraitHandler keeps its own decoded copy of the trait record.
        entity.traits.trait_data = entity.attributes.get(
            "traits", default={}, category="traits"
        )
        entity.traits._cache.clear()


class CatchUpFixture(ScopedSettlementFixture):
    """The two-zone world, a lag helper and the unit seeds every test uses."""

    def lag(self, tick: int = LAG_TICK) -> None:
        """Advance the world tick while every unit cursor stays at ``START``."""
        clock = get_world_clock()
        clock.tick = tick
        clock._persist(tick)

    def seed_units(self, cell: tuple[int, int]) -> frozenset[str]:
        """Every unit one locator seeds, exactly as the catch-up resolves it."""
        index = population_units.current_unit_index()
        return population_units.units_around(
            index, LocationRef.wilderness(WILDERNESS_NAME, *cell)
        )

    def catch_up(self, cell: tuple[int, int]) -> bool:
        return ensure_locations_current(
            [LocationRef.wilderness(WILDERNESS_NAME, *cell)]
        )


class CatchUpSettlementTests(CatchUpFixture):
    """A catch-up settles a lagging closed set, and leaves a current one alone."""

    def test_a_lagging_unit_is_settled_to_the_current_tick(self):
        self._build_scenario()
        self.lag()
        with (
            patch.object(population_lifecycle, "log_info") as logged,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settled = self.catch_up(WANDER_B)
        self.assertTrue(settled)
        self.assertEqual(
            self.cursor_record().units.get(self.unit_b), LAG_TICK
        )
        caught_up = settlement_projection(self.wilderness)
        events = [
            call
            for call in logged.call_args_list
            if call.args and call.args[0] == "population_caught_up"
        ]
        self.assertEqual(len(events), 1, "one event per settled catch-up")
        context = events[0].kwargs["context"]
        scope = population_units.build_scope(
            self.wilderness, self.seed_units(WANDER_B)
        )
        self.assertEqual(context["units"], len(scope.units))
        self.assertEqual(context["tick_from"], START)
        self.assertEqual(context["tick_to"], LAG_TICK)

        # The same set settled by one scoped pass leaves the same world.
        self._build_scenario()
        self.lag()
        settle_population_scope(
            self.wilderness,
            population_units.build_scope(
                self.wilderness, self.seed_units(WANDER_B)
            ).units,
            LAG_TICK,
        )
        self.assertEqual(caught_up, settlement_projection(self.wilderness))

    def test_a_current_unit_is_written_and_reported_nowhere(self):
        self._build_scenario()
        before = settlement_projection(self.wilderness)
        cursors = self.cursor_record()
        with (
            patch.object(population_lifecycle, "log_info") as logged,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settled = self.catch_up(WANDER_B)
        self.assertFalse(settled)
        self.assertEqual(settlement_projection(self.wilderness), before)
        self.assertEqual(self.cursor_record(), cursors)
        logged.assert_not_called()

    def test_a_failed_catch_up_restores_the_unit(self):
        self._build_scenario()
        self.lag()
        before = settlement_projection(self.wilderness)
        cursors = self.cursor_record()
        real = regional_population.record_population_transition
        calls = {"count": 0}

        def fail_after_the_first_write(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("injected catch-up fault")
            return real(*args, **kwargs)

        with patch.object(
            regional_population,
            "record_population_transition",
            side_effect=fail_after_the_first_write,
        ):
            with self.assertRaises(RuntimeError):
                self.catch_up(WANDER_B)
        self.assertGreaterEqual(
            calls["count"], 2, "the fault landed after a departure was written"
        )
        self.assertEqual(self.cursor_record(), cursors)
        self.assertEqual(settlement_projection(self.wilderness), before)
        _drop_attribute_caches(
            self.wilderness,
            *self.bodies[ZONE_A],
            *self.bodies[ZONE_B],
        )
        self.assertEqual(settlement_projection(self.wilderness), before)


class ObservedUnitTests(CatchUpFixture):
    """Observed units come from player positions and running announcements."""

    def test_the_sight_radius_bounds_the_observed_units(self):
        self._build_scenario()
        self.assertEqual(self.world.unit(WEST_OF_ZONE_A), self.unit_a)
        place_player(self, WEST_OF_ZONE_A)
        self.assertEqual(
            population_units.observed_units(self.wilderness),
            frozenset({population_units.RESIDUAL_UNIT, self.unit_a}),
            "a room-standing character adds only the residual unit, and a zone "
            "beyond the sight radius adds none",
        )
        place_player(self, EAST_OF_ZONE_A)
        self.assertEqual(
            population_units.observed_units(self.wilderness),
            frozenset(
                {
                    population_units.RESIDUAL_UNIT,
                    self.unit_a,
                    self.unit_b,
                }
            ),
        )

    def test_an_announced_location_is_observed_only_while_it_runs(self):
        self._build_scenario()
        place_player(self, WEST_OF_ZONE_A)
        announced = LocationRef.wilderness(WILDERNESS_NAME, *WANDER_B)
        self.assertNotIn(
            self.unit_b, population_units.observed_units(self.wilderness)
        )
        with population_units.announced_observation([announced]):
            self.assertIn(
                self.unit_b, population_units.observed_units(self.wilderness)
            )
        self.assertNotIn(
            self.unit_b, population_units.observed_units(self.wilderness)
        )


class CommandCatchUpTests(CatchUpFixture):
    """Every command catches the observed units up before it parses or runs."""

    def command(self, caller):
        from commands.command import Command

        command = Command()
        command.caller = caller
        command.key = "look"
        command.args = ""
        return command

    def test_a_command_settles_the_units_around_the_player(self):
        self._build_scenario()
        player = place_player(self, EAST_OF_ZONE_A)
        self.lag()
        with (
            patch.object(population_lifecycle, "log_info"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.command(player).at_pre_cmd()
        self.assertEqual(
            self.cursor_record().units.get(self.unit_b),
            LAG_TICK,
            "the neighbouring unit is current before the command's own code",
        )

    def test_a_failed_catch_up_is_reported_and_the_command_still_runs(self):
        self._build_scenario()
        player = place_player(self, EAST_OF_ZONE_A)
        self.lag()
        with (
            patch.object(
                population_lifecycle,
                "ensure_population_current",
                side_effect=RuntimeError("injected catch-up fault"),
            ),
            patch("commands.command.log_error") as logged,
            patch("commands.command.log_info") as boundary,
        ):
            self.assertIsNone(self.command(player).at_pre_cmd())
        self.assertEqual(
            [call.args[0] for call in logged.call_args_list],
            ["population_catch_up_failed"],
        )
        context = logged.call_args.kwargs["context"]
        self.assertEqual(context["char"], player.pk)
        self.assertEqual(context["cmd"], "look")
        self.assertIsInstance(logged.call_args.kwargs["exc"], RuntimeError)
        self.assertEqual(
            [call.args[0] for call in boundary.call_args_list], ["cmd_in"]
        )


class CommandSeamTests(CatchUpFixture):
    """A localized command inherits the same seam as the repository base."""

    def test_a_localized_command_settles_the_units_around_the_player(self):
        self._build_scenario()
        player = place_player(self, EAST_OF_ZONE_A)
        self.lag()
        command = CmdLook()
        command.caller = player
        with (
            patch.object(population_lifecycle, "log_info"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            command.at_pre_cmd()
        self.assertEqual(self.cursor_record().units.get(self.unit_b), LAG_TICK)


class OperatorCatchUpTests(CatchUpFixture):
    """The operator and quest entry points catch their target up first."""

    def test_a_gm_placement_settles_the_target_cell(self):
        self._build_scenario()
        enter_wilderness(self.char1, coordinates=EAST_OF_ZONE_A, name=WILDERNESS_NAME)
        room = self.char1.location
        self.lag()
        map_gm.spawn_monster(SPECIES, ORDINARY, f"#{room.pk}")
        self.assertEqual(self.cursor_record().units.get(self.unit_b), LAG_TICK)

    def test_a_gm_removal_settles_the_removed_entity(self):
        self._build_scenario()
        enter_wilderness(self.char1, coordinates=EAST_OF_ZONE_A, name=WILDERNESS_NAME)
        removed = self._monster(EAST_OF_ZONE_A, home_zone=ZONE_B)
        self.lag()
        map_gm.delete_entity(f"#{removed.pk}")
        self.assertEqual(self.cursor_record().units.get(self.unit_b), LAG_TICK)

    def test_a_gm_hit_point_edit_settles_the_target(self):
        self._build_scenario()
        enter_wilderness(self.char1, coordinates=EAST_OF_ZONE_A, name=WILDERNESS_NAME)
        monster = self._monster(EAST_OF_ZONE_A, home_zone=ZONE_B)
        self.lag()
        rules_gm.set_gauge(f"#{monster.pk}", "hp", 1)
        self.assertEqual(self.cursor_record().units.get(self.unit_b), LAG_TICK)


class CatchUpBoundaryTests(CatchUpFixture):
    """A catch-up never starts inside a pass and refuses another transaction."""

    def test_a_catch_up_inside_a_running_pass_writes_nothing(self):
        self._build_scenario()
        self.lag()
        cursors = self.cursor_record()
        with population_units.running_pass():
            settled = self.catch_up(WANDER_B)
        self.assertFalse(settled)
        self.assertEqual(self.cursor_record(), cursors)

    @override_settings(POPULATION_CATCH_UP_REFUSES_NESTED=True)
    def test_a_writing_catch_up_refuses_an_enclosing_transaction(self):
        self._build_scenario()
        self.lag()
        cursors = self.cursor_record()
        with self.assertRaises(population_units.PopulationCatchUpNested):
            with transaction.atomic():
                self.catch_up(WANDER_B)
        self.assertEqual(self.cursor_record(), cursors)


class MovementCatchUpTests(CatchUpFixture):
    """A movement edge catches its destination up before its own settlement."""

    def _crossing_step(self):
        """The first lawful east step from zone A into zone B, and its cell."""
        for y in range(700, 710):
            source = LocationRef.wilderness(WILDERNESS_NAME, 519, y)
            edge = resolve_direction_edge(source, (519, y), "east")
            if edge is None or edge.destination.kind != "wilderness":
                continue
            destination = (edge.destination.x, edge.destination.y)
            if (
                self.world.unit((519, y)) == self.unit_a
                and self.world.unit(destination) == self.unit_b
            ):
                return (519, y), destination
        return None, None

    def test_a_movement_edge_catches_the_destination_up_first(self):
        self._build_scenario()
        cell, destination = self._crossing_step()
        self.assertIsNotNone(
            cell, "the synthetic A/B boundary offers one lawful east step"
        )
        self.assertIsNotNone(self.world.unit(destination))
        enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME)
        exits = [exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == "east"]
        self.assertEqual(len(exits), 1, "the cell materializes its east exit")
        self.lag()

        order: list[tuple[str, object]] = []
        observed: dict[str, object] = {}
        real_ensure = population_lifecycle.ensure_population_current
        real_advance = WorldClock.advance

        def ensured(wilderness, seeds):
            result = real_ensure(wilderness, seeds)
            order.append(("catch_up", result))
            return result

        def advanced(clock_self, seconds, source, entities, **kwargs):
            observed["cursor"] = population_units.read_unit_cursors(
                self.wilderness
            ).units.get(self.unit_b)
            order.append(("advance", int(clock_self.tick)))
            return real_advance(clock_self, seconds, source, entities, **kwargs)

        with (
            patch.object(
                population_lifecycle, "ensure_population_current", side_effect=ensured
            ),
            patch.object(WorldClock, "advance", autospec=True, side_effect=advanced),
            self.captureOnCommitCallbacks(execute=False),
        ):
            exits[0].at_traverse(self.char1, self.char1.location)

        self.assertEqual(order[0][0], "catch_up")
        self.assertTrue(
            order[0][1], "the destination unit was behind and was settled"
        )
        self.assertEqual(
            observed["cursor"],
            LAG_TICK,
            "the unit is current before the edge's own settlement advances",
        )
        self.assertEqual(
            self.cursor_record().units.get(self.unit_b), LAG_TICK
        )