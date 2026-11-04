"""Behaviour tests for the confirmed party retreat's physical route and edge.

The planner is exercised against a real wilderness world and a real combat
session: every projection, price and route comes from the canonical owners,
never from a shipped coordinate or count. The assertions establish the
mechanisms the retreat promises — the unpaid combat prefix plus the attempt,
only self-moving members pricing the route, carried knocked-out companions,
exact-zero arrival, the previous-edge fallback, one combat plus one traversal
charge, and an unaffordable attempt never moving anybody.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from math import ceil
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.maps import regional_population
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    PARTY_EXIT_RETREAT,
    confirm_party_exit,
    engage,
    read_session,
    request_party_exit,
    reconstruct_battlefield,
)
from world.rules.combat_identity import stable_actor_id
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.movement_edges import (
    PhysicalEdge,
    legal_edges,
    location_ref,
    record_completed_edge,
    resolve_direction_edge,
)
from world.rules.party import join_party
from world.rules.travel_cost import (
    plan_traversal,
    terrain_speed_m_per_hour,
    wilderness_distance_m,
    wilderness_terrain,
)
from world.rules.travel_plan import DIRECTION_ORDER, TravellerState
from world.rules.world_escape import plan_party_retreat
from world.tests.geography_fixture import publish_shipped_map_world

from ._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import grant_lineage

_PROBE = (500, 700)
_SEED = 3
_RESERVE = 360000
_SCOPE_LOGICALS = ("skills", "elements", "races", "subraces", "static_tiers")
_SEVERE_FOOT_FRACTION = Fraction(1, 2)


class PartyRetreatTravelTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=synth_innate_overlay())
        super().setUp()
        publish_shipped_map_world()
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        regional_population.initialize_population_seed(
            self.wilderness, seed=_SEED, tick=0
        )
        self.player = _player("retreat traveller")
        grant_lineage(self.player, [BASIC_ATTACK_KEY])
        self.player.traits.hp.base = 1000
        self.player.traits.hp.current = 1000
        self.player.traits.agility.base = 20
        staging = create_object(Room, key="retreat staging")
        self.player.location = staging
        self.companion = create_object(
            NPC, key="retreat companion", location=staging
        )
        self.companion.race = self.player.race
        self.companion.apply_race_baseline()
        self.companion.traits.hp.base = 500
        self.companion.traits.hp.current = 500
        join_party(self.companion, self.player)
        # Enter the companion first, then the player: the wilderness provider
        # recycles a room with no account inside, so the player must be the
        # last body to materialize the shared cell.
        self.assertTrue(
            enter_wilderness(self.companion, coordinates=_PROBE, name=WILDERNESS_NAME)
        )
        self.assertTrue(
            enter_wilderness(self.player, coordinates=_PROBE, name=WILDERNESS_NAME)
        )
        self.room = self.player.location
        write_fatigue_state(self.player, _RESERVE, SleepPosture.AWAKE)
        write_fatigue_state(self.companion, _RESERVE, SleepPosture.AWAKE)
        self.room = self.player.location
        self.monster = _monster("retreat wolf", hp=900)
        self.assertIsNotNone(self.room)
        self.monster.location = self.room
        self.monster.db_location = self.room
        self.room.contents_cache.add(self.monster)
        self.assertIs(self.monster.location, self.room)
        self.wilderness.db.itemcoordinates[self.monster] = _PROBE
        engage(self.player, self.monster)

    # -- fixtures -----------------------------------------------------------

    def _record(self):
        return read_session(self.player)

    def _field(self):
        return reconstruct_battlefield(self.player, self._record())

    def _edges(self):
        return tuple(
            edge
            for edge in legal_edges(
                self.player, location_ref(self.player), (self.player,)
            )
            if edge.destination.kind == "wilderness"
        )

    def _distance_terrain(self, edge):
        return (
            wilderness_distance_m(
                (edge.source.x, edge.source.y),
                (edge.destination.x, edge.destination.y),
            ),
            wilderness_terrain(
                (edge.source.x, edge.source.y),
                (edge.destination.x, edge.destination.y),
            ),
        )

    def _cost(self, edge, reserve):
        distance, terrain = self._distance_terrain(edge)
        return plan_traversal(
            ((distance, terrain),),
            (TravellerState(reserve, SleepPosture.AWAKE).detached(),),
        )

    def _exact_reserve(self, edge):
        """The reserve a severe-band traveller spends exactly on one edge."""
        distance, terrain = self._distance_terrain(edge)
        speed = Fraction(terrain_speed_m_per_hour(terrain)) * _SEVERE_FOOT_FRACTION
        seconds = ceil(Fraction(distance) / (speed / 3600))
        reserve = 8 * seconds
        self.assertLess(reserve, 72000)
        self.assertEqual(self._cost(edge, reserve).seconds, seconds)
        return reserve, seconds

    def _plan(self, *, preferred=None, record=None, field=None):
        return plan_party_retreat(
            self.player,
            self._record() if record is None else record,
            self._field() if field is None else field,
            operation_id="test:retreat:0",
            preferred=preferred,
        )

    def _record_reverse_edge(self, target):
        """Record the edge whose reverse is ``target`` (so it is preferred)."""
        destination = target.destination
        for direction in DIRECTION_ORDER:
            candidate = resolve_direction_edge(
                destination, (destination.x, destination.y), direction
            )
            if candidate is not None and candidate.destination == target.source:
                record_completed_edge(
                    self.player,
                    PhysicalEdge(
                        source=destination,
                        destination=target.source,
                        route=f"direction:{direction}",
                    ),
                )
                return
        raise AssertionError("the target edge has no reverse direction")

    # -- projection ---------------------------------------------------------

    @covers_requirement("player-combat-session::successful-retreat-carries-the-entire-present-party-and-counts-one-round")
    def test_the_plan_projects_the_unpaid_prefix_plus_the_attempt(self):
        record = replace(self._record(), rounds_elapsed=2, settled_rounds=0)
        plan = self._plan(record=record)
        self.assertIsNotNone(plan)
        # Two unpaid completed rounds plus the attempt: awake combat costs
        # exactly twelve reserve units per second.
        self.assertEqual(
            plan.states_after_attempt[0].reserve_units, _RESERVE - 3 * 72
        )
        self.assertIs(plan.states_after_attempt[0].posture, SleepPosture.AWAKE)
        # A cursor already at the completed count pays only the attempt.
        paid = replace(self._record(), rounds_elapsed=2, settled_rounds=2)
        paid_plan = self._plan(record=paid)
        self.assertEqual(
            paid_plan.states_after_attempt[0].reserve_units, _RESERVE - 72
        )

    @covers_requirement("player-combat-session::successful-retreat-carries-the-entire-present-party-and-counts-one-round")
    def test_only_self_moving_members_price_and_carried_members_are_listed(self):
        remote = create_object(NPC, key="remote companion", location=self.room)
        remote.race = self.player.race
        remote.apply_race_baseline()
        remote.traits.hp.base = 100
        remote.traits.hp.current = 100
        join_party(remote, self.player)
        record = self._record()
        field = self._field()
        field.knocked_out.add(stable_actor_id(self.companion))
        plan = plan_party_retreat(
            self.player,
            replace(record, knocked_out_ids=(int(self.companion.pk),)),
            field,
            operation_id="test:retreat:0",
            preferred=None,
        )
        self.assertIsNotNone(plan)
        self.assertIn(int(self.player.pk), plan.member_ids)
        self.assertIn(int(self.companion.pk), plan.member_ids)
        self.assertNotIn(int(remote.pk), plan.member_ids)
        self.assertEqual(plan.self_moving_ids, (int(self.player.pk),))
        self.assertEqual(plan.carried_ids, (int(self.companion.pk),))
        self.assertEqual(
            tuple(state.member_id for state in plan.states_after_attempt),
            (int(self.player.pk),),
        )

    @covers_requirement("player-combat-session::failed-retreat-consumes-all-allied-actions-and-runs-one-ordinary-enemy-upkeep-round")
    def test_post_attempt_depletion_is_no_route_even_without_pursuers(self):
        write_fatigue_state(self.player, 10, SleepPosture.AWAKE)
        write_fatigue_state(self.companion, 10, SleepPosture.AWAKE)
        self.monster.traits.hp.current = 0
        self.assertIsNone(self._plan())

    # -- pricing and selection ---------------------------------------------

    @covers_requirement("player-combat-session::retreat-contests-the-slowest-acting-ally-against-the-fastest-pursuer")
    def test_an_unaffordable_previous_edge_falls_back_to_a_lawful_neighbour(self):
        edges = self._edges()
        self.assertGreaterEqual(len(edges), 2)
        needs = {edge: self._exact_reserve(edge)[0] for edge in edges}
        cheapest = min(needs, key=needs.get)
        expensive = max(needs, key=needs.get)
        if needs[cheapest] == needs[expensive]:
            self.skipTest("every adjacent edge shares one canonical price")
        write_fatigue_state(
            self.player, needs[cheapest] + 72, SleepPosture.AWAKE
        )
        plan = self._plan(preferred=expensive)
        self.assertIsNotNone(plan)
        self.assertNotEqual(plan.edge, expensive)
        self.assertEqual(plan.edge.destination.kind, "wilderness")

    @covers_requirement("player-combat-session::successful-retreat-carries-the-entire-present-party-and-counts-one-round")
    def test_exact_zero_arrival_is_affordable_and_consumed_in_full(self):
        target = self._edges()[0]
        exact, seconds = self._exact_reserve(target)
        write_fatigue_state(self.player, exact + 72, SleepPosture.AWAKE)
        plan = self._plan(preferred=target)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.edge, target)
        self.assertEqual(int(plan.traversal.cost.seconds), seconds)
        arrived = TravellerState(exact, SleepPosture.AWAKE).advance(seconds)
        self.assertEqual(arrived.reserve_units, 0)
        self.assertIs(arrived.posture, SleepPosture.FORCED)
        # Below every adjacent edge's exact requirement the attempt is an
        # ordinary failure: no route, no partial move.
        cheapest = min(self._exact_reserve(edge)[0] for edge in self._edges())
        # The attempt consumes 72 units, so this leaves ``cheapest - 1``.
        write_fatigue_state(self.player, cheapest + 71, SleepPosture.AWAKE)
        self.assertIsNone(self._plan(preferred=target))

    # -- one atomic exit ----------------------------------------------------

    def _prompt(self):
        record = self._record()
        return request_party_exit(
            self.player,
            record.session_id,
            record.round_revision,
            PARTY_EXIT_RETREAT,
        )

    def _confirm(self, prompt):
        return confirm_party_exit(
            self.player,
            prompt["session_id"],
            prompt["round_revision"],
            prompt["operation"],
            prompt["confirmation_token"],
        )

    @covers_requirement("player-combat-session::successful-retreat-carries-the-entire-present-party-and-counts-one-round")
    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_a_success_moves_the_party_and_pays_combat_and_travel_once(self):
        from world.rules.clock import get_world_clock
        from world.rules.combat_session.lifecycle import _persist

        target = self._edges()[0]
        self._record_reverse_edge(target)
        # One unpaid interactive round plus a carried knocked-out companion:
        # the old encounter must pay that prefix and the attempt once, and the
        # companion must travel without walking, healing or waking.
        self.companion.traits.hp.current = 1
        record = replace(
            self._record(),
            rounds_elapsed=1,
            knocked_out_ids=(int(self.companion.pk),),
        )
        _persist(self.player, record)
        plan = plan_party_retreat(
            self.player,
            self._record(),
            self._field(),
            operation_id="test:retreat:0",
            preferred=target,
        )
        self.assertEqual(plan.edge, target)
        self.assertEqual(plan.self_moving_ids, (int(self.player.pk),))
        self.assertEqual(plan.carried_ids, (int(self.companion.pk),))
        before = int(get_world_clock().tick)
        prompt = self._prompt()
        with (
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch(
                "world.rules.movement_settlement._admit_arrival_contact"
            ) as admit,
        ):
            result = self._confirm(prompt)
        self.assertEqual(result["outcome"], "fled")
        admit.assert_called_once_with(self.player)
        travel_seconds = int(plan.traversal.cost.seconds)
        self.assertEqual(
            int(get_world_clock().tick) - before, 2 * 6 + travel_seconds
        )
        self.assertEqual(result["travel"]["seconds"], travel_seconds)
        destination = plan.edge.destination
        self.assertEqual(
            result["travel"]["destination"],
            {
                "kind": "wilderness",
                "map": WILDERNESS_NAME,
                "x": destination.x,
                "y": destination.y,
            },
        )
        self.assertEqual(location_ref(self.player), destination)
        self.assertEqual(location_ref(self.companion), destination)
        # Carried, not healed and not woken by the old encounter.
        self.assertEqual(self.companion.traits.hp.current, 1)

    @covers_requirement("player-combat-session::failed-retreat-consumes-all-allied-actions-and-runs-one-ordinary-enemy-upkeep-round")
    def test_an_unaffordable_attempt_fails_without_any_movement_or_payment(self):
        from world.rules.clock import get_world_clock

        write_fatigue_state(self.player, 10, SleepPosture.AWAKE)
        write_fatigue_state(self.companion, 10, SleepPosture.AWAKE)
        source = location_ref(self.player)
        before = int(get_world_clock().tick)
        rounds_before = self._record().rounds_elapsed
        prompt = self._prompt()
        with patch("world.rules.disengage.roll_d100") as roll:
            result = self._confirm(prompt)
        roll.assert_not_called()
        self.assertEqual(result["outcome"], "round")
        self.assertIsNone(result.get("travel"))
        self.assertEqual(location_ref(self.player), source)
        self.assertEqual(location_ref(self.companion), source)
        self.assertEqual(int(get_world_clock().tick), before)
        current = self._record()
        self.assertEqual(current.rounds_elapsed, rounds_before + 1)
        self.assertEqual(current.draft_entries, {})
        self.assertEqual(current.settled_rounds, 0)
