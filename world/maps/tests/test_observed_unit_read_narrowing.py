"""Behaviour tests: a scoped pass enumerates only its own individuals.

A clock advance settles the observed units, so its presence read must be the
same read: the members of the pass's own groups and the individuals registered
on cells it covers, never every living row of the world. The proof is equality
of two reads of one world (the zone measures and the individual facts) plus
equality of state: the narrowed and the whole-world enumeration leave the same
world after the same advances, and one advance's statement count does not follow
how much an unobserved zone holds.

Every scenario is built from the synthetic two-zone world of
:func:`world.maps.tests.test_scoped_population_settlement.build_two_zone_world`;
no shipped zone, site, composition or individual is named, and no assertion is
a wall-clock or hardware-speed measurement.

The delta's two ADDED requirements have no canonical identifiers before the
archive sync, so no test here carries ``covers_requirement``.
"""

from __future__ import annotations

import contextlib
from unittest.mock import patch

from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext

from typeclasses.monsters import Monster

from world.maps import monster_activity, population_units, regional_population
from world.maps.monster_activity import create_group
from world.maps.tests._settlement_projection import (
    catch_up_world,
    settlement_projection,
)
from world.maps.tests.test_monster_activity import GROUP_ACTIVITY, SEED, SOLO_ACTIVITY
from world.maps.tests.test_population_catch_up import (
    _drop_attribute_caches,
    place_player,
)
from world.maps.tests.test_scoped_population_settlement import (
    ACTIVITY_B_WANDER,
    CELLS_A,
    ScopedSettlementFixture,
    START,
    WANDER_A,
    WANDER_B,
    ZONE_A,
    ZONE_B,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.movement_edges import LocationRef
from world.rules.surfaces import persisted_hp

#: The three intervals the observed advance is proven over.
INTERVALS = (300, 600, 600)

#: One cell in no authored rectangle of the fixture's region: its settlement
#: unit is the residual unit, which is never the observed zone's own unit.
RESIDUAL_CELL = (540, 700)


def _ref(cell: tuple[int, int]) -> LocationRef:
    """The wilderness locator of one cell."""
    return LocationRef.wilderness(WILDERNESS_NAME, *cell)


class ReadNarrowingFixture(ScopedSettlementFixture):
    """The two-zone world with the observed clock stage installed."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    def advance(self, seconds: int) -> list:
        """One command advance with no party in the advance's own scope."""
        return get_world_clock().advance(seconds, AdvanceSource.COMMAND, [])

    # -- world building -----------------------------------------------------

    def zone_group(
        self, cell: tuple[int, int], *, operation_id: str
    ) -> tuple[str, tuple]:
        """One group owned by zone A, its members homed and standing on ``cell``."""
        bodies = tuple(self._monster(cell, home_zone=ZONE_A) for _ in range(2))
        group_id = create_group(
            self.wilderness,
            operation_id=operation_id,
            owner_kind="zone",
            owner_key=ZONE_A,
            activity_key=GROUP_ACTIVITY,
            home=_ref(cell),
            position=_ref(cell),
            member_ids=tuple(int(body.pk) for body in bodies),
            seed=SEED,
            tick=START,
        )
        return group_id, bodies

    def registered_owner(self, cell: tuple[int, int]) -> Monster:
        """One living individual homed in zone A, on ``cell``, with no group."""
        return self._monster(cell, home_zone=ZONE_A)

    # -- reads --------------------------------------------------------------

    def observed_scope(self) -> population_units.PopulationScope:
        return population_units.build_scope(
            self.wilderness, population_units.observed_units(self.wilderness)
        )

    def whole_presence(self) -> dict:
        return regional_population.presence_at(self.wilderness)

    def scoped_presence(self, scope: population_units.PopulationScope) -> dict:
        with regional_population.reused_living_presence(scope=scope):
            return regional_population.presence_at(self.wilderness)

    @staticmethod
    def counts_for(zone_key: str, presence: dict):
        return regional_population.counts_from_presence(
            zone_key, presence, wilderness=WILDERNESS_NAME
        )

    def far_living_ids(self) -> set[int]:
        """The living individuals the unobserved zone holds."""
        return {
            int(body.pk) for body in self.bodies[ZONE_B] if persisted_hp(body) > 0
        }


class ScopedEnumerationTests(ReadNarrowingFixture):
    """A scoped read covers its own units and answers their whole-world counts."""

    def test_the_scoped_zone_counts_equal_the_whole_world_counts(self):
        self._build_scenario()
        place_player(self, WANDER_A)
        group_id, group_bodies = self.zone_group(
            CELLS_A[2], operation_id="narrow:local"
        )
        owner = self.registered_owner(CELLS_A[6])
        scope = self.observed_scope()
        # The scope is the first zone: the second zone is outside it.
        self.assertIn(self.unit_a, scope.units)
        self.assertNotIn(self.unit_b, scope.units)
        self.assertIn(group_id, scope.group_ids)
        whole = self.whole_presence()
        narrow = self.scoped_presence(scope)
        self.assertEqual(
            self.counts_for(ZONE_A, narrow), self.counts_for(ZONE_A, whole)
        )
        counts = self.counts_for(ZONE_A, whole)
        inside = {int(owner.pk)} | {int(body.pk) for body in group_bodies}
        # The compared counts are the real ones, from both enumeration sources.
        self.assertLessEqual(inside, counts.local_ids)
        self.assertLessEqual(inside, counts.home_ids)
        self.assertLessEqual(inside, set(narrow))
        # The read really was narrower: the other zone's individuals are gone.
        far = self.far_living_ids()
        self.assertTrue(far)
        self.assertLessEqual(far, set(whole))
        self.assertFalse(far & set(narrow))
        self.assertLessEqual(set(narrow), set(whole))

    def test_a_home_owned_member_standing_in_a_linked_unit_counts_at_home(self):
        self._build_scenario()
        self.assertEqual(
            self.world.unit(RESIDUAL_CELL), population_units.RESIDUAL_UNIT
        )
        member = self.registered_owner(RESIDUAL_CELL)
        # The group's home is zone A and its position is the other unit, so the
        # closure links that unit into the scope and the member is a member.
        create_group(
            self.wilderness,
            operation_id="narrow:linked",
            owner_kind="zone",
            owner_key=ZONE_A,
            activity_key=SOLO_ACTIVITY,
            home=_ref(WANDER_A),
            position=_ref(RESIDUAL_CELL),
            member_ids=(int(member.pk),),
            seed=SEED,
            tick=START,
        )
        scope = population_units.build_scope(self.wilderness, {self.unit_a})
        self.assertIn(population_units.RESIDUAL_UNIT, scope.units)
        whole = self.whole_presence()
        narrow = self.scoped_presence(scope)
        self.assertEqual(
            self.counts_for(ZONE_A, narrow), self.counts_for(ZONE_A, whole)
        )
        counts = self.counts_for(ZONE_A, narrow)
        self.assertIn(int(member.pk), narrow)
        self.assertIn(int(member.pk), counts.home_ids)
        self.assertNotIn(int(member.pk), counts.local_ids)

    def test_a_registered_individual_without_a_group_counts_locally_and_home(self):
        self._build_scenario()
        place_player(self, WANDER_A)
        owner = self.registered_owner(CELLS_A[6])
        grouped = {
            int(member_id)
            for group in monster_activity.read_monster_activity(
                self.wilderness
            ).groups.values()
            for member_id in group.member_ids
        }
        self.assertNotIn(owner.pk, grouped)
        scope = self.observed_scope()
        whole = self.whole_presence()
        narrow = self.scoped_presence(scope)
        self.assertEqual(
            self.counts_for(ZONE_A, narrow), self.counts_for(ZONE_A, whole)
        )
        counts = self.counts_for(ZONE_A, narrow)
        self.assertIn(int(owner.pk), counts.local_ids)
        self.assertIn(int(owner.pk), counts.home_ids)
        self.assertIn(int(owner.pk), narrow)
        self.assertFalse(self.far_living_ids() & set(narrow))


class UnchangedOutcomeTests(ReadNarrowingFixture):
    """The narrowed enumeration leaves the world a whole-world read leaves."""

    def run_scenario(self, *, narrow: bool) -> dict:
        """Advance three intervals, catch up everywhere, project the world."""
        self._build_scenario()
        place_player(self, WANDER_A)
        calls: list = []
        real = regional_population._scope_living_monsters

        def counting_scope(wilderness, scope):
            calls.append(scope)
            return real(wilderness, scope)

        def whole_world(wilderness, scope):
            calls.append(scope)
            return regional_population._living_monsters()

        scanner = (
            patch.object(
                regional_population, "_scope_living_monsters", counting_scope
            )
            if narrow
            else patch.object(
                regional_population, "_scope_living_monsters", whole_world
            )
        )
        with scanner:
            for seconds in INTERVALS:
                self.advance(seconds)
            catch_up_world(self.wilderness)
        self.assertTrue(calls, "the pass enumerated a roster")
        projection = settlement_projection(self.wilderness)
        group_id = self.group_ids[ZONE_B][0]
        self.assertGreater(
            monster_activity.read_monster_activity(self.wilderness)
            .groups[group_id]
            .sequence,
            0,
            "the catch-up settled the far zone, so neither side is untouched",
        )
        return projection

    def test_the_narrowed_and_whole_world_enumeration_settle_the_same_world(self):
        self.assertEqual(
            self.run_scenario(narrow=True), self.run_scenario(narrow=False)
        )


class AdvanceWorkTests(ReadNarrowingFixture):
    """One advance's statement count does not follow the unobserved units."""

    #: One short advance. Django keeps at most 9000 statements per capture, so
    #: the measured interval stays far below it (asserted in :meth:`capture`).
    INTERVAL = 60

    def build_world(
        self, *, groups: int, members: int, announced: list
    ) -> int:
        """Rebuild the world, add ``groups`` unobserved groups, warm it once."""
        self._build_scenario()
        for _ in range(groups):
            self._group(
                cell=WANDER_B,
                activity=ACTIVITY_B_WANDER,
                owner_key=ZONE_B,
                members=members,
            )
        state = monster_activity.read_monster_activity(self.wilderness)
        far_groups = len(
            [
                group
                for group in state.groups.values()
                if group.home_owner == ("zone", ZONE_B)
            ]
        )
        with population_units.announced_observation(announced):
            self.advance(0)
        # A cold attribute cache makes a whole-world enumeration really pay one
        # row read per individual instead of a live-cache hit.
        _drop_attribute_caches(self.wilderness, *Monster.objects.all_family())
        return far_groups

    def capture(self, announced: list) -> tuple[int, frozenset[str]]:
        """The statements and the observed set of one measured advance."""
        reset_queries()
        with population_units.announced_observation(announced):
            observed = population_units.observed_units(self.wilderness)
            with CaptureQueriesContext(connection) as queries:
                self.advance(self.INTERVAL)
        total = len(queries)
        self.assertLess(total, 9000, "the captured statements were not truncated")
        return total, observed

    def measure(
        self, *, groups: int, members: int, narrow: bool = True
    ) -> tuple[int, frozenset[str], int]:
        """One measured advance over a world with ``groups`` extra far groups.

        The advance carries no entity and announces one zone-A cell instead, so
        the observed set is the same in every measurement and the contact and
        forecast paths (whose presence read stays whole-world) are outside what
        is measured. Each world is warmed identically by one zero-second advance
        and one attribute-cache reset.

        The first advance of a fresh test process creates one attribute row that
        every rebuilt world afterwards only updates, so one whole measurement is
        discarded first: both compared sides are then measured from the same
        steady state, and the compared counts differ only in the far zone.
        """
        announced = [_ref(WANDER_A)]
        scanner = (
            contextlib.nullcontext()
            if narrow
            else patch.object(
                regional_population,
                "_scope_living_monsters",
                lambda wilderness, scope: regional_population._living_monsters(),
            )
        )
        with scanner:
            self.build_world(groups=groups, members=members, announced=announced)
            self.capture(announced)
            far_groups = self.build_world(
                groups=groups, members=members, announced=announced
            )
            total, observed = self.capture(announced)
        return total, observed, far_groups

    def test_growing_the_far_zone_keeps_the_advance_statement_count(self):
        one, one_units, one_groups = self.measure(groups=1, members=1)
        many, many_units, many_groups = self.measure(groups=6, members=3)
        self.assertNotIn(self.unit_b, one_units)
        self.assertEqual(one_units, many_units, "both advances observe the same units")
        self.assertLess(one_groups, many_groups, "the unobserved zone really grew")
        self.assertEqual(one, many)

    def test_the_whole_world_enumeration_would_pay_for_the_far_zone(self):
        many, _units, _groups = self.measure(groups=6, members=3)
        whole, _units, _groups = self.measure(groups=6, members=3, narrow=False)
        self.assertGreater(
            whole,
            many,
            "the unobserved rows cost statements when the enumeration is whole-world",
        )