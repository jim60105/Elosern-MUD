"""Boundary tests for the read-only contact forecast and its skip consumers.

Every test drives a production path: the registered clock stages through
``WorldClock.advance``/``advance_wait``, the owning sleep writers, or a real
``settle_movement`` edge. The synthetic seams are the same file-local
registries the other field-behaviour suites use (species, variants, tiers,
activity areas, activities, compositions, ecology zones and sites), so no
shipped density, timing or wording value is pinned here.

The assertions establish mechanisms with independently known outcomes: which
tick a forecast reports, that forecasting writes nothing, that a distant
maintenance fact never returns control, that the accepted wait/sleep interval
matches the forecast, and that a physical edge is never clipped.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
)
from world.maps import monster_activity, monster_sites, population_lifecycle
from world.maps import regional_population
from world.maps.monster_activity import create_group
from world.maps.population_forecast import (
    FORECAST_SOURCE_BIRTH,
    capture_activity_snapshot,
    project_activity_window,
)
from world.maps.population_lifecycle import (
    next_population_lifecycle_boundary,
    register_regional_population,
)
from world.maps.regional_population import (
    initialize_population_seed,
    read_population_timeline,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.rules.clock import AdvanceSource, advance_scope, get_world_clock
from world.rules.combat_session import forfeit, read_session
from world.rules.fatigue import (
    SleepPosture,
    project_fatigue_status,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.field_contact import (
    evaluate_field_contact,
    forecast_observers,
    register_field_contact_stage,
)
from world.rules.mental_time import plan_for
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import LocationRef
from world.rules.time_skip import (
    advance_wait,
    begin_sleep,
    continue_sleep,
    continue_owner_sleep,
)
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

_VARIANT = next(iter(SYNTH_MONSTER_VARIANTS))
_SPECIES = SYNTH_MONSTER_VARIANTS[_VARIANT].species_key

from ._combat_session_helpers import BattlefieldIsolation, _player

_ANCHOR = (500, 700)
_ZONE_CELLS = ((510, 700), (511, 700), (512, 700), (513, 700))
_SITE_CELL = (520, 700)
_SEED = 11
_CONTACT = "t_boundary_contact"
_PASSIVE = "t_boundary_passive"
_GROUND = "t_boundary_ground"
_ZONE_KEY = "t_boundary_zone"
_SITE_KEY = "t_boundary_site"
_CONTACT_SITE_KEY = "t_boundary_contact_site"
_CONTACT_COMPOSITION = "t_boundary_contact_composition"
_PASSIVE_COMPOSITION = "t_boundary_passive_composition"


def _write(entity, reserve, posture=SleepPosture.AWAKE):
    write_fatigue_state(entity, reserve, posture)
    project_fatigue_status(entity)


def _activity(key: str, *, aggression: AggressionCondition, interval: int = 20):
    return MonsterActivity(key, "solitary_roaming", _GROUND, interval, aggression)


class _BoundaryBase(BattlefieldIsolation, EvenniaTestCase):
    """A provisioned wilderness whose future facts are known exactly."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "encounter_compositions",
            )
        )
        self.probe, self.neighbour = self._same_region_pair()
        self.region = region_for_coordinates(*self.probe)
        region = self.region
        self.ground = ActivityArea(
            _GROUND,
            region,
            (
                (
                    min(self.probe[0], self.neighbour[0]),
                    max(self.probe[0], self.neighbour[0]),
                    min(self.probe[1], self.neighbour[1]),
                    max(self.probe[1], self.neighbour[1]),
                ),
            ),
        )
        self.zone = EcologyZone(
            _ZONE_KEY,
            region,
            ((0, 0, 0, 0),),
            (WeightedComposition(_PASSIVE_COMPOSITION, 1),),
            75,
            99,
            1,
            recovery_delay=5,
            replenishment_interval=5,
            wave_budget=1,
        )
        self.compositions = {
            _CONTACT_COMPOSITION: EncounterComposition(
                _CONTACT_COMPOSITION,
                _CONTACT,
                (CompositionMember(_VARIANT, 1, 1),),
            ),
            _PASSIVE_COMPOSITION: EncounterComposition(
                _PASSIVE_COMPOSITION,
                _PASSIVE,
                (CompositionMember(_VARIANT, 1, 1),),
            ),
        }
        self.site = MonsterSite(
            key=_SITE_KEY,
            kind="camp",
            region_key=region,
            coordinates=_SITE_CELL,
            composition_key=_PASSIVE_COMPOSITION,
            capacity=1,
            one_shot=False,
            recover_after_ticks=20,
            activity_key=_PASSIVE,
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType({self.zone.key: self.zone}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "eligible_birth_cells",
                lambda *args, **kwargs: _ZONE_CELLS,
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "_region_cells",
                lambda zone: frozenset(_ZONE_CELLS),
            )
        )
        self.enterContext(
            patch.object(
                regional_population, "SETTLEMENT_BIRTH_POLICY_REGISTRY", MappingProxyType({})
            )
        )
        self.contact_site = MonsterSite(
            key=_CONTACT_SITE_KEY,
            kind="camp",
            region_key=region,
            coordinates=self.probe,
            composition_key=_CONTACT_COMPOSITION,
            capacity=1,
            one_shot=False,
            recover_after_ticks=20,
            activity_key=_CONTACT,
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType(
                    {self.site.key: self.site, self.contact_site.key: self.contact_site}
                ),
            )
        )
        self.enterContext(
            patch(
                "world.lore.monster_activity.MONSTER_ACTIVITY_REGISTRY",
                {
                    _CONTACT: _activity(
                        _CONTACT, aggression=AggressionCondition("contact")
                    ),
                    _PASSIVE: _activity(
                        _PASSIVE, aggression=AggressionCondition("passive")
                    ),
                },
            )
        )
        self.enterContext(
            patch(
                "world.lore.monster_activity.ACTIVITY_AREA_REGISTRY",
                {_GROUND: self.ground},
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=_SEED, tick=0)
        register_regional_population()
        register_field_contact_stage()
        self.clock = get_world_clock()
        self.clock._persist(0)
        self.clock.tick = 0
        self.origin = create_object(Room, key="boundary origin")
        self.far = create_object(Room, key="boundary far")
        self.player = _player("boundary player")
        self.assertTrue(
            enter_wilderness(self.player, coordinates=self.probe, name=WILDERNESS_NAME)
        )
        self.player.traits.hp.base = 5000
        self.player.traits.hp.current = 5000
        _write(self.player, 360000)

    def _same_region_pair(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Two adjacent wilderness cells in one published region."""
        here = region_for_coordinates(*_ANCHOR)
        for step in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
            cell = (_ANCHOR[0] + step[0], _ANCHOR[1] + step[1])
            if region_for_coordinates(*cell) == here:
                return _ANCHOR, cell
        raise AssertionError("no adjacent cell shares the anchor's region")

    # -- fixtures ----------------------------------------------------------
    def _future_facts(
        self,
        *,
        due: int = 105,
        site_cleared_at: int = 90,
        contact_cleared_at: int = 10**6,
    ) -> None:
        """The durable state a wait from 100 must plan around.

        ``due`` is a distant zone recovery, ``site_cleared_at`` a distant
        passive site recovery at ``site_cleared_at + recover_after_ticks``.
        """
        self.clock._persist(100)
        self.clock.tick = 100
        self.wilderness.db.regional_population = {
            _ZONE_KEY: {
                "initialized": True,
                "seed": _SEED,
                "generation_sequence": 0,
                "recovery_due_tick": due,
                "settled_through_tick": 100,
            }
        }
        self.wilderness.db.population_timeline = {
            "settled_through_tick": 100,
            "transitions": [],
            "protection": [],
        }
        self.wilderness.db.monster_sites = {
            _SITE_KEY: {
                "state": monster_sites.SITE_STATE_CLEARED,
                "cleared_at_tick": site_cleared_at,
                "seed": _SEED,
                "generation_sequence": 0,
                "member_ids": [999999],
            },
            _CONTACT_SITE_KEY: {
                "state": monster_sites.SITE_STATE_CLEARED,
                "cleared_at_tick": contact_cleared_at,
                "seed": _SEED,
                "generation_sequence": 0,
                "member_ids": [999998],
            },
        }

    def _place_group(self, *, seed: int) -> object:
        """One real contact group standing at the neighbouring cell."""
        operation_id = "boundary:group"
        cell = self.neighbour
        enemy = construct_species_individual(_SPECIES, _VARIANT)
        enemy.traits.hp.base = 1000
        enemy.traits.hp.current = 1000
        # The individual stands at its registered wilderness cell without
        # sharing the observer's room, so its presence is the projection's
        # own fact rather than a same-room shortcut.
        enemy.location = self.far
        self.far.contents_cache.add(enemy)
        self.wilderness.db.itemcoordinates[enemy] = cell
        _write(enemy, 360000)
        create_group(
            self.wilderness,
            operation_id=operation_id,
            owner_kind="zone",
            owner_key=_ZONE_KEY,
            activity_key=_CONTACT,
            home=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            position=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            member_ids=(enemy.pk,),
            seed=seed,
            tick=100,
        )
        return enemy

    def _departing_group(self) -> tuple[object, int]:
        """One real group at the neighbouring cell that departs at 120.

        The saved occurrence seed is selected by asking the real planner,
        not by re-deriving its draw: the first seed whose 120 decision is a
        departure is kept, and every other candidate is released through the
        owner's own staged-group cleanup.
        """
        operation_id = "boundary:group"
        group_id = monster_activity.group_id_for(operation_id, 0)
        for seed in range(1, 64):
            enemy = self._place_group(seed=seed)
            decision = monster_activity.plan_group_decision(
                self.wilderness, group_id, tick=120
            )
            if decision.edge is not None:
                return enemy, seed
            monster_activity.release_group(self.wilderness, group_id)
            enemy.delete()
        raise AssertionError("no occurrence seed makes the group depart at 120")

    def _tick(self) -> int:
        """The committed world tick, read the way production reads it."""
        return int(get_world_clock().tick)

    def _observer(self):
        return forecast_observers()

    def _scoped(self, call):
        """Run one pure query under the settled-body scope the clock binds."""
        with advance_scope((self.player,)):
            return call()

    def _forecast(self, *, start: int = 100, end: int = 2000):
        def query():
            return project_activity_window(
                capture_activity_snapshot(start_tick=start),
                start_tick=start,
                end_tick=end,
                observers=self._observer(),
                wilderness=WILDERNESS_NAME,
            )

        return self._scoped(query)

    def _departure_arrival(self, enemy, seed: int) -> int:
        """The committed arrival tick of the group's 120 departure."""
        from world.rules.movement_edges import quote_edge
        from world.rules.world_escape import build_journey_plan

        group_id = monster_activity.group_of_member(self.wilderness, int(enemy.pk)).group_id
        decision = monster_activity.plan_group_decision(
            self.wilderness, group_id, tick=120
        )
        self.assertIsNotNone(
            decision.edge, f"reason={decision.reason} group={group_id} seed={seed}"
        )
        bodies = monster_activity.living_member_bodies(
            self.wilderness, decision.group_id
        )
        states = monster_activity.projected_member_states(
            self.wilderness, decision.group_id, tick=120
        )
        resolution = quote_edge(bodies[0], decision.edge, bodies, states=states)
        plan = build_journey_plan(bodies, resolution, states)
        self.assertTrue(seed)
        return 120 + int(plan["seconds"])


class ForecastPurityTests(_BoundaryBase):
    """The projection answers the first contact and writes nothing."""

    def test_the_first_contact_is_the_intermediate_arrivals_tick(self):
        self._future_facts()
        enemy, seed = self._departing_group()
        arrival = self._departure_arrival(enemy, seed)
        self.assertGreater(arrival, 120)

        before = {
            "tick": int(self.clock.tick),
            "activity": dict(self.wilderness.db.monster_activity or {}),
            "zones": dict(self.wilderness.db.regional_population or {}),
            "sites": dict(self.wilderness.db.monster_sites or {}),
            "timeline": read_population_timeline(self.wilderness),
            "monsters": type(enemy).objects.count(),
            "coordinates": len(self.wilderness.db.itemcoordinates or {}),
        }
        first = self._forecast()
        second = self._forecast()
        self.assertEqual(first.first_tick, arrival)
        self.assertEqual(second.first_tick, arrival)
        self.assertEqual(first.contact_sources, (FORECAST_SOURCE_BIRTH,))
        # No write, no entity, no draw: the same inputs still describe the
        # same world.
        self.assertEqual(int(self.clock.tick), before["tick"])
        self.assertEqual(dict(self.wilderness.db.monster_activity or {}), before["activity"])
        self.assertEqual(dict(self.wilderness.db.regional_population or {}), before["zones"])
        self.assertEqual(dict(self.wilderness.db.monster_sites or {}), before["sites"])
        self.assertEqual(read_population_timeline(self.wilderness), before["timeline"])
        self.assertEqual(type(enemy).objects.count(), before["monsters"])
        self.assertEqual(
            len(self.wilderness.db.itemcoordinates or {}), before["coordinates"]
        )

    def test_the_registered_query_reports_the_same_contact(self):
        self._future_facts()
        enemy, seed = self._departing_group()
        arrival = self._departure_arrival(enemy, seed)
        self.assertEqual(
            self._scoped(lambda: next_population_lifecycle_boundary(100, 2000)),
            arrival,
        )
        # Nothing between the interval start and that tick is interactive.
        self.assertIsNone(
            self._scoped(lambda: next_population_lifecycle_boundary(100, arrival - 1))
        )

    def test_a_distant_group_decision_never_interrupts(self):
        self._future_facts(due=105, site_cleared_at=1000)
        # A group whose authored extent holds only its own cell: its 120
        # decision is a lawful stay, so the projection never reports it.
        self.enterContext(
            patch(
                "world.lore.monster_activity.ACTIVITY_AREA_REGISTRY",
                {
                    _GROUND: ActivityArea(
                        _GROUND,
                        self.region,
                        (
                            (
                                self.neighbour[0],
                                self.neighbour[0],
                                self.neighbour[1],
                                self.neighbour[1],
                            ),
                        ),
                    )
                },
            )
        )
        enemy = self._place_group(seed=_SEED)
        self.assertIsNone(
            self._scoped(lambda: next_population_lifecycle_boundary(100, 1000))
        )
        self.assertIsNone(self._forecast().first_tick)
        del enemy

    def test_projection_preserves_every_owner_surface(self):
        self._future_facts()
        self._departing_group()
        snapshot = capture_activity_snapshot(start_tick=100)
        self.assertTrue(snapshot.groups)
        self.assertTrue(snapshot.zones)
        self.assertTrue(snapshot.sites)
        self.assertTrue(snapshot.presence)
        # A snapshot is detached: reading it again never re-reads a live row
        # nor changes the durable owner state it came from.
        states_before = dict(self.wilderness.db.regional_population or {})
        self._scoped(
            lambda: project_activity_window(
                snapshot,
                start_tick=100,
                end_tick=1000,
                observers=self._observer(),
                wilderness=WILDERNESS_NAME,
            )
        )
        self.assertEqual(dict(self.wilderness.db.regional_population or {}), states_before)


class WaitBoundaryTests(_BoundaryBase):
    """An ordinary wait stops at the projected contact, keeping its receipt."""

    @covers_requirement(
        "time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary"
    )
    def test_the_wait_stops_at_the_projected_contact(self):
        self._future_facts()
        enemy, seed = self._departing_group()
        arrival = self._departure_arrival(enemy, seed)
        reserve_before = read_optional_fatigue_state(self.player).reserve_units
        result = advance_wait(self.player, 2000)
        self.assertEqual(result.requested_seconds, 2000)
        self.assertEqual(result.elapsed_seconds, arrival - 100)
        self.assertEqual(self._tick(), arrival)
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(record.started_tick, arrival)
        self.assertIn(int(enemy.pk), record.enemy_ids)
        # Physiology settled exactly the accepted interval.
        after = read_optional_fatigue_state(self.player)
        self.assertLess(after.reserve_units, reserve_before)
        self.assertIs(after.posture, SleepPosture.AWAKE)

    @covers_requirement(
        "time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary"
    )
    def test_the_interruption_boundary_is_logged_once_on_commit(self):
        self._future_facts(contact_cleared_at=90)
        contact_tick = 90 + self.contact_site.recover_after_ticks
        with patch("world.rules.time_skip.log_info") as info, (
            self.captureOnCommitCallbacks(execute=True)
        ):
            result = advance_wait(self.player, 2000)
        rows = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "field_contact_interrupted"
        ]
        self.assertEqual(len(rows), 1)
        context = rows[0].kwargs["context"]
        self.assertEqual(context["char"], str(int(self.player.pk)))
        self.assertEqual(context["operation"], result.operation_id)
        self.assertEqual(context["sleep"], "")
        self.assertEqual(context["requested_seconds"], 2000)
        self.assertEqual(context["elapsed_seconds"], contact_tick - 100)
        self.assertEqual(context["tick"], contact_tick)
        self.assertTrue(context["session"])

    def test_a_distant_maintenance_fact_does_not_interrupt_the_wait(self):
        self._future_facts(due=105, site_cleared_at=1000)
        result = advance_wait(self.player, 300)
        self.assertEqual(result.elapsed_seconds, 300)
        self.assertFalse(result.interrupted)
        self.assertIsNone(read_session(self.player))
        # The zone's own maintenance still ran inside the interval.
        self.assertGreater(
            regional_population.zone_state(self.wilderness, _ZONE_KEY).generation_sequence,
            0,
        )


class SleepBoundaryTests(_BoundaryBase):
    """Sleep stops at the projected contact and keeps its accepted receipt."""

    @covers_requirement(
        "time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary"
    )
    def test_continue_sleep_stops_at_the_projected_birth_contact(self):
        self._future_facts(contact_cleared_at=90)
        contact_tick = 90 + self.contact_site.recover_after_ticks
        self.assertEqual(self._forecast().first_tick, contact_tick)
        _write(self.player, 100000)
        outcome = begin_sleep(self.player, mode="duration", seconds=6000, allow_continue=False)
        self.assertIsNotNone(outcome.entry)
        from world.rules.sleep_receipt import read_sleep_receipt

        receipt = read_sleep_receipt(self.player)
        with patch("world.rules.time_skip.log_info") as info, (
            self.captureOnCommitCallbacks(execute=True)
        ):
            result = continue_sleep(self.player)
        rows = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "field_contact_interrupted"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kwargs["context"]["sleep"], receipt.sleep_id)
        self.assertEqual(self._tick(), contact_tick)
        self.assertEqual(result.elapsed_seconds, contact_tick - 100)
        self.assertTrue(result.interrupted)
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(record.started_tick, contact_tick)
        after = read_optional_fatigue_state(self.player)
        self.assertIs(after.posture, SleepPosture.AWAKE)
        self.assertGreater(after.reserve_units, 100000)
        updated = read_sleep_receipt(self.player)
        self.assertEqual(updated.settled_through_tick, contact_tick)
        self.assertFalse(updated.sleeping)
        self.assertNotEqual(updated.revision, receipt.revision)

    @covers_requirement(
        "time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary"
    )
    def test_owner_continuation_is_revoked_by_the_contact(self):
        self._future_facts(contact_cleared_at=90)
        contact_tick = 90 + self.contact_site.recover_after_ticks
        from world.rules.sleep_receipt import (
            CONTINUATION_COMPLETE,
            CONTINUATION_PENDING,
            STATE_INTERRUPTED,
            read_sleep_receipt,
            read_sleep_view_decision,
            read_sleep_view_generation,
        )
        from world.rules.time_skip import authorize_owner_sleep_continuation

        _write(self.player, 1000)
        outcome = begin_sleep(self.player, mode="duration", seconds=6000, allow_continue=False)
        self.assertIsNotNone(outcome.entry)
        receipt = read_sleep_receipt(self.player)
        authorize_owner_sleep_continuation(
            self.player,
            sleep_id=receipt.sleep_id,
            revision=receipt.revision,
            generation=read_sleep_view_generation(self.player),
        )
        result = continue_owner_sleep(self.player)
        self.assertEqual(result.elapsed_seconds, contact_tick - 100)
        self.assertTrue(result.interrupted)
        # The contact interruption revokes the accepted sleep through its
        # owner, so nothing resumable remains: the continuation ends without a
        # pending authorization the player could replay.
        self.assertEqual(result.continuation, CONTINUATION_COMPLETE)
        self.assertEqual(read_sleep_receipt(self.player).state, STATE_INTERRUPTED)
        decision = read_sleep_view_decision(self.player)
        self.assertNotEqual(decision["continuation"], CONTINUATION_PENDING)

    def test_a_forced_receipt_keeps_its_threshold(self):
        self._future_facts(contact_cleared_at=90)
        arrival = 90 + self.contact_site.recover_after_ticks
        from world.rules.sleep_receipt import (
            KIND_FORCED,
            MODE_FORCED_THRESHOLD,
            STATE_SLEEPING,
            SleepReceipt,
            read_sleep_receipt,
            write_sleep_receipt,
        )

        _write(self.player, 50000, SleepPosture.FORCED)
        write_sleep_receipt(
            self.player,
            SleepReceipt(
                sleep_id="forced:boundary:0",
                body_id=int(self.player.pk),
                owner_id=None,
                kind=KIND_FORCED,
                mode=MODE_FORCED_THRESHOLD,
                entry_tick=100,
                target_tick=10000,
                limit_tick=10000,
                settled_through_tick=100,
                revision=0,
                state=STATE_SLEEPING,
                accepted_seconds=10000,
                partial=False,
            ),
        )
        from world.rules.combat_session import policies as session_policies

        with (
            patch.object(
                session_policies,
                "_enemy_policy",
                side_effect=lambda entity, field, record: (
                    session_policies._basic_attack_request(entity, field, record)
                ),
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.rounds.continue_incapacitated_hostile_rounds",
                return_value={"continued_rounds": 0},
            ),
        ):
            result = continue_sleep(self.player)
        # The accepted skip interval is exactly the projected boundary; every
        # later second is separately billed enemy-round combat time, never
        # extra skip duration or extra receipt recovery.
        self.assertEqual(result.elapsed_seconds, arrival - 100)
        self.assertGreaterEqual(self._tick(), arrival)
        admitted = [
            event for event in result.events if event.kind == "field_contact_admitted"
        ]
        self.assertTrue(admitted)
        self.assertEqual(int(admitted[0].due_tick), arrival)
        persisted = read_sleep_receipt(self.player)
        self.assertIs(read_optional_fatigue_state(self.player).posture, SleepPosture.FORCED)
        self.assertIn(persisted.state, (STATE_SLEEPING,))
        self.assertEqual(persisted.kind, KIND_FORCED)
        self.assertEqual(persisted.mode, MODE_FORCED_THRESHOLD)
        # The accepted cap is untouched; only the derived natural-wake target
        # of the reserved threshold may track the recovered reserve.
        self.assertEqual(persisted.limit_tick, 10000)
        self.assertLessEqual(persisted.target_tick, persisted.limit_tick)
        self.assertGreater(
            read_optional_fatigue_state(self.player).reserve_units, 50000
        )


class IndivisibleEdgeTests(_BoundaryBase):
    """A committed physical edge completes its whole cost before contact."""

    def test_an_edge_completes_once_and_admits_at_its_arrival(self):
        from world.rules.movement_settlement import settle_movement

        enemy = construct_species_individual(
            _SPECIES,
            _VARIANT,
        )
        enemy.traits.hp.base = 1000
        enemy.traits.hp.current = 1000
        self.player.location = self.origin
        self.wilderness.db.itemcoordinates.pop(self.player, None)
        enemy.location = self.player.location
        destination = self.wilderness.db.rooms.get(self.probe)
        self.assertIsNotNone(destination)
        cell = self.probe
        enemy.location = destination
        destination.contents_cache.add(enemy)
        self.wilderness.db.itemcoordinates[enemy] = cell
        _write(enemy, 360000)
        create_group(
            self.wilderness,
            operation_id="boundary:edge",
            owner_kind="zone",
            owner_key=_ZONE_KEY,
            activity_key=_CONTACT,
            home=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            position=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            member_ids=(enemy.pk,),
            seed=_SEED,
            tick=100,
        )
        start = int(self.clock.tick)
        settle_movement(
            self.player,
            self.origin,
            destination=destination,
            traverse=lambda: self.player.move_to(destination, quiet=True),
            wilderness_coordinates=cell,
            route="direction:north",
            window_seconds=150,
        )
        self.assertEqual(self._tick(), start)
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(record.started_tick, start)
        self.assertIn(int(enemy.pk), record.enemy_ids)
        forfeit(self.player)
        self.assertIsNone(read_session(self.player))


class FaultRestorationTests(_BoundaryBase):
    """A late failure restores every surface the accepted interval wrote."""

    def test_a_failed_interval_restores_clock_and_physiology(self):
        self._future_facts()
        enemy, seed = self._departing_group()
        self._departure_arrival(enemy, seed)
        state_before = read_optional_fatigue_state(self.player)
        tick_before = int(self.clock.tick)
        zones_before = dict(self.wilderness.db.regional_population or {})
        with patch(
            "world.rules.combat_session.rounds.continue_incapacitated_hostile_rounds",
            side_effect=RuntimeError("injected post-admission failure"),
        ), patch("world.rules.time_skip.log_info") as info, (
            self.captureOnCommitCallbacks(execute=True)
        ):
            with self.assertRaises(RuntimeError):
                advance_wait(self.player, 2000)
        # A rolled-back interval publishes no interruption boundary.
        self.assertEqual(
            [
                call
                for call in info.call_args_list
                if call.args and call.args[0] == "field_contact_interrupted"
            ],
            [],
        )
        self.assertEqual(int(self.clock.tick), tick_before)
        self.assertEqual(read_optional_fatigue_state(self.player), state_before)
        self.assertEqual(dict(self.wilderness.db.regional_population or {}), zones_before)
        self.assertIsNone(read_session(self.player))
