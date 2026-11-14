"""Behaviour tests: reused settlement reads never change a settled result.

Every scenario here is built from the synthetic catalogues and the file-local
registry seams of :class:`ActivityFixture`; no shipped zone, site, composition
or individual is named. The differential test asserts equality of two runs of
the same scenario, so no expected value is produced by the code under test in
a second mode.
"""

from __future__ import annotations

import contextlib
from types import MappingProxyType
from unittest.mock import patch

from django.db import transaction

from tools.spec_traceability import covers_requirement
from typeclasses.monsters import Monster

from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
)
from world.maps import (
    monster_activity,
    monster_sites,
    population_lifecycle,
    regional_population,
)
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.regional_population import (
    POPULATION_SEED_ATTRIBUTE,
    MalformedPopulationState,
    PopulationTransition,
    initialize_zone,
    presence_of,
    read_population_timeline,
    record_population_protection,
    record_population_transition,
    restore_population_surfaces,
    snapshot_population_surfaces,
    zone_states,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_monster_activity import (
    GROUP_ACTIVITY,
    PROBE,
    SOLO_ACTIVITY,
    ActivityFixture,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.movement_edges import LocationRef
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS

ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))
SEED = 11
START = 100
#: The wandering group stays at the activity probe cell.
WANDERING_CELL = PROBE
#: The travelling group starts one step away and departs on its first decision.
TRAVELLING_CELL = (501, 701)
ZONE_KEY = "t_decode_zone"
SITE_KEY = "t_decode_site"
COMPOSITION_KEY = "t_decode_solo"
#: Four synthetic eligible cells at 75/99 per hundred give one exact band of 3.
CELLS = tuple((510 + offset, 700) for offset in range(4))
LOWER_DENSITY = 75
UPPER_DENSITY = 99
RECOVERY_DELAY = 10
REPLENISHMENT = 5
SITE_RECOVERY_TICKS = 40
#: One identity no living row carries: the site's already-defeated member.
DEFEATED_ID = 999999

ZONE_RECORD = {
    "initialized": True,
    "seed": SEED,
    "generation_sequence": 0,
    "recovery_due_tick": None,
    "settled_through_tick": 0,
}


def _timeline_record(settled_through_tick: int) -> dict:
    """One complete stored timeline value at one settled tick."""
    return {
        "settled_through_tick": settled_through_tick,
        "transitions": [],
        "protection": [],
    }


def _cell_ref(cell: tuple[int, int]) -> LocationRef:
    """One wilderness locator for a protection decision."""
    return LocationRef.wilderness(WILDERNESS_NAME, *cell)


class DecodeReuseTests(ActivityFixture):
    """A stored population record is decoded once per stored value."""

    def setUp(self):
        super().setUp()
        self.wilderness.db.regional_population = {ZONE_KEY: dict(ZONE_RECORD)}
        self.wilderness.db.population_timeline = _timeline_record(0)

    @staticmethod
    def _decoding(name: str):
        """Count the decode calls of one private decode function."""
        return patch.object(
            regional_population, name, wraps=getattr(regional_population, name)
        )

    @covers_requirement(
        "regional-population::stored-population-records-are-decoded-once-per-stored-value"
    )
    def test_repeated_reads_decode_each_record_once(self):
        with self._decoding("_zone_map_from_raw") as zone_decode:
            maps = [regional_population._state_map(self.wilderness) for _ in range(5)]
        self.assertEqual(zone_decode.call_count, 1)
        for zone_map in maps[1:]:
            self.assertEqual(zone_map, maps[0])
        with (
            self._decoding("_timeline_from_raw") as timeline_decode,
            self._decoding("_zone_state_from_record") as record_decode,
        ):
            timelines = [read_population_timeline(self.wilderness) for _ in range(5)]
            zones = [zone_states(self.wilderness) for _ in range(5)]
        self.assertEqual(timeline_decode.call_count, 1)
        self.assertEqual(record_decode.call_count, 1)
        self.assertIs(timelines[0], timelines[-1])
        for timeline in timelines[1:]:
            self.assertEqual(timeline, timelines[0])
        for zone_map in zones[1:]:
            self.assertEqual(zone_map, zones[0])
        self.assertIs(zones[0][ZONE_KEY], zones[-1][ZONE_KEY])
        self.assertEqual(zones[0][ZONE_KEY].settled_through_tick, 0)

    @covers_requirement(
        "regional-population::stored-population-records-are-decoded-once-per-stored-value"
    )
    def test_a_read_follows_every_kind_of_timeline_write(self):
        first = read_population_timeline(self.wilderness)
        self.assertIs(read_population_timeline(self.wilderness), first)
        # One whole-value write replaces the stored value object.
        self.wilderness.db.population_timeline = _timeline_record(5)
        self.assertEqual(
            read_population_timeline(self.wilderness).settled_through_tick, 5
        )
        # One in-place mutation of the stored value does too.
        self.wilderness.db.population_timeline["settled_through_tick"] = 9
        self.assertEqual(
            read_population_timeline(self.wilderness).settled_through_tick, 9
        )
        # A rolled-back write is restored through the owner's own surface
        # contract, and the read follows the restored value again.
        snapshot = snapshot_population_surfaces(self.wilderness)
        with self.assertRaises(ZeroDivisionError):
            with transaction.atomic():
                self.wilderness.db.population_timeline = _timeline_record(99)
                self.assertEqual(
                    read_population_timeline(self.wilderness).settled_through_tick, 99
                )
                raise ZeroDivisionError
        restore_population_surfaces(snapshot)
        self.assertEqual(
            read_population_timeline(self.wilderness).settled_through_tick, 9
        )

    @covers_requirement(
        "regional-population::stored-population-records-are-decoded-once-per-stored-value"
    )
    def test_a_zone_read_follows_every_kind_of_record_and_seed_write(self):
        self.assertEqual(
            zone_states(self.wilderness)[ZONE_KEY].settled_through_tick, 0
        )
        self.wilderness.db.regional_population = {
            ZONE_KEY: {**ZONE_RECORD, "settled_through_tick": 4}
        }
        self.assertEqual(
            zone_states(self.wilderness)[ZONE_KEY].settled_through_tick, 4
        )
        self.wilderness.db.regional_population[ZONE_KEY]["generation_sequence"] = 2
        self.assertEqual(
            zone_states(self.wilderness)[ZONE_KEY].generation_sequence, 2
        )
        # A rolled-back write is restored through the owner's own contract, and
        # the read follows the restored record again.
        snapshot = snapshot_population_surfaces(self.wilderness)
        with self.assertRaises(ZeroDivisionError):
            with transaction.atomic():
                self.wilderness.db.regional_population = {
                    ZONE_KEY: {**ZONE_RECORD, "settled_through_tick": 40}
                }
                self.assertEqual(
                    zone_states(self.wilderness)[ZONE_KEY].settled_through_tick, 40
                )
                raise ZeroDivisionError
        restore_population_surfaces(snapshot)
        restored = zone_states(self.wilderness)[ZONE_KEY]
        self.assertEqual(restored.settled_through_tick, 4)
        self.assertEqual(restored.generation_sequence, 2)
        # The seed every record is validated against is part of those facts.
        self.wilderness.attributes.add(POPULATION_SEED_ATTRIBUTE, SEED + 1)
        with self.assertRaises(MalformedPopulationState):
            zone_states(self.wilderness)


class SettlementScenarioFixture(ActivityFixture):
    """A synthetic ecology zone and composition the settlement can write."""

    def setUp(self):
        super().setUp()
        self.zone = EcologyZone(
            ZONE_KEY,
            self.region,
            ((0, 0, 0, 0),),
            (WeightedComposition(COMPOSITION_KEY, 1),),
            LOWER_DENSITY,
            UPPER_DENSITY,
            3,
            recovery_delay=RECOVERY_DELAY,
            replenishment_interval=REPLENISHMENT,
            wave_budget=1,
        )
        self.composition = EncounterComposition(
            COMPOSITION_KEY,
            SOLO_ACTIVITY,
            (CompositionMember(ORDINARY, 1, 1),),
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType({ZONE_KEY: self.zone}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType({COMPOSITION_KEY: self.composition}),
            )
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType({COMPOSITION_KEY: self.composition}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "SETTLEMENT_BIRTH_POLICY_REGISTRY",
                MappingProxyType({}),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "eligible_birth_cells",
                lambda *args, **kwargs: tuple(CELLS),
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "_region_cells",
                lambda zone: frozenset(CELLS),
            )
        )

    def _kill(self, individual: Monster, tick: int) -> None:
        """Zero one individual's HP and record its loss at that tick."""
        before = presence_of(self.wilderness, individual)
        individual.traits.hp.current = 0
        record_population_transition(
            self.wilderness,
            PopulationTransition(
                source_id=f"scenario-loss:{tick}",
                individual_id=int(individual.pk),
                occurred_tick=tick,
                before=before,
                after=presence_of(self.wilderness, individual, alive=False),
            ),
        )

    def _deficit_zone(self) -> tuple[int, ...]:
        """A fresh zone one member below its lower density at ``START``."""
        self._reset_activity(tick=START)
        self.wilderness.db.regional_population = {}
        created = initialize_zone(self.wilderness, ZONE_KEY, seed=SEED, tick=START)
        self._kill(Monster.objects.get(pk=created[0]), START)
        return created

    def _seed_for(
        self,
        *,
        depart: bool,
        activity: str,
        cell: tuple[int, int],
        prefix: tuple[str, int] | None = None,
    ) -> int:
        """A seed whose first scheduled decision departs (or stays)."""
        interval = monster_activity.activity_decision_interval(activity)
        for seed in range(64):
            self._reset_activity(tick=START)
            if prefix is not None:
                self._group(
                    cell=WANDERING_CELL,
                    seed=prefix[1],
                    tick=START,
                    activity=prefix[0],
                    owner_key=ZONE_KEY,
                )
            group_id, _bodies = self._group(
                cell=cell,
                seed=seed,
                tick=START,
                activity=activity,
                owner_key=ZONE_KEY,
            )
            decision = monster_activity.plan_group_decision(
                self.wilderness, group_id, tick=START + interval
            )
            if (decision.edge is not None) == depart:
                return seed
        raise AssertionError("no seed produced the requested first decision")


class PassFactTests(SettlementScenarioFixture):
    """One pass reads each pass-stable population fact once."""

    @covers_requirement(
        "regional-population::a-settlement-pass-reuses-pass-stable-population-facts"
    )
    def test_a_quiet_pass_over_many_boundaries_reads_each_fact_once(self):
        staying = self._seed_for(depart=False, activity=GROUP_ACTIVITY, cell=PROBE)
        departing = self._seed_for(
            depart=True,
            activity=SOLO_ACTIVITY,
            cell=TRAVELLING_CELL,
            prefix=(GROUP_ACTIVITY, staying),
        )
        self._reset_activity(tick=START)
        staying_group, _bodies = self._group(
            cell=PROBE, seed=staying, tick=START, owner_key=ZONE_KEY
        )
        self._group(
            cell=TRAVELLING_CELL,
            seed=departing,
            tick=START,
            activity=SOLO_ACTIVITY,
            owner_key=ZONE_KEY,
        )
        with (
            patch.object(
                regional_population,
                "_living_monsters",
                wraps=regional_population._living_monsters,
            ) as living_scan,
            patch.object(
                regional_population,
                "_active_session_protection",
                wraps=regional_population._active_session_protection,
            ) as session_scan,
        ):
            settle_population_lifecycle(START, START + 300)
        # The pass really crossed several boundaries.
        self.assertGreaterEqual(
            monster_activity.read_monster_activity(self.wilderness)
            .groups[staying_group]
            .sequence,
            2,
        )
        self.assertEqual(living_scan.call_count, 1)
        self.assertEqual(session_scan.call_count, 1)

    @covers_requirement(
        "regional-population::a-settlement-pass-reuses-pass-stable-population-facts"
    )
    def test_a_birth_inside_the_pass_is_read_with_its_home_zone(self):
        created = self._deficit_zone()
        scans: list[tuple[int, ...]] = []
        living_scan = regional_population._living_monsters

        def recording_scan():
            rows = living_scan()
            scans.append(tuple(int(row.pk) for row in rows))
            return rows

        with patch.object(regional_population, "_living_monsters", recording_scan):
            settle_population_lifecycle(START, START + RECOVERY_DELAY + 20)
        newborn_ids = {
            int(row.pk)
            for row in Monster.objects.all_family()
            if int(row.pk) not in set(created)
            and row.db.home_ecology_zone == ZONE_KEY
        }
        self.assertTrue(newborn_ids)
        # A later read of the same pass enumerated the newborn individuals; the
        # first one could not have, and no read rescanned the roster again.
        self.assertEqual(len(scans), 2)
        self.assertNotIn(newborn_ids, [set(scan) for scan in scans[:1]])
        self.assertTrue(
            any(newborn_ids <= set(scan) for scan in scans[1:]),
            msg=f"newborn {sorted(newborn_ids)} missing from a later scan",
        )
        presence = regional_population.presence_at(self.wilderness)
        for newborn_id in newborn_ids:
            self.assertTrue(presence[newborn_id].alive)
            self.assertEqual(presence[newborn_id].home_zone, ZONE_KEY)

    @covers_requirement(
        "regional-population::a-settlement-pass-reuses-pass-stable-population-facts"
    )
    def test_protected_cells_are_computed_once_per_tick(self):
        self._reset_activity(tick=START)
        record_population_protection(
            self.wilderness,
            engagement_id="scenario-engagement",
            cell=WANDERING_CELL,
            start_tick=START,
            end_tick=None,
        )
        cells = (WANDERING_CELL, TRAVELLING_CELL, CELLS[0])
        with patch.object(
            regional_population,
            "_protected_cells_at",
            wraps=regional_population._protected_cells_at,
        ) as shared_compute:
            with regional_population.reused_living_presence():
                shared = [
                    monster_activity._destination_blocked(
                        self.wilderness, _cell_ref(cell), START
                    )
                    for cell in cells
                ]
        unaided_compute = patch.object(
            regional_population,
            "_protected_cells_at",
            wraps=regional_population._protected_cells_at,
        )
        with unaided_compute as unshared_compute:
            unaided = [
                monster_activity._destination_blocked(
                    self.wilderness, _cell_ref(cell), START
                )
                for cell in cells
            ]
        self.assertEqual(shared_compute.call_count, 1)
        self.assertEqual(unshared_compute.call_count, len(cells))
        self.assertEqual(shared, unaided)
        self.assertEqual(shared, [True, False, False])
        # A timeline write at the same tick is a new stored value.
        with patch.object(
            regional_population,
            "_protected_cells_at",
            wraps=regional_population._protected_cells_at,
        ) as recompute:
            with regional_population.reused_living_presence():
                before = regional_population.protected_cells(
                    self.wilderness, at_tick=START
                )
                record_population_protection(
                    self.wilderness,
                    engagement_id="second-engagement",
                    cell=TRAVELLING_CELL,
                    start_tick=START,
                    end_tick=None,
                )
                after = regional_population.protected_cells(
                    self.wilderness, at_tick=START
                )
        self.assertEqual(recompute.call_count, 2)
        self.assertNotIn(TRAVELLING_CELL, before)
        self.assertIn(TRAVELLING_CELL, after)


class ScenarioSettlementFixture(SettlementScenarioFixture):
    """A synthetic world with two groups, a deficit zone and a due site."""

    def setUp(self):
        super().setUp()
        self.site = MonsterSite(
            key=SITE_KEY,
            kind="camp",
            region_key=self.region,
            coordinates=CELLS[0],
            composition_key=COMPOSITION_KEY,
            activity_key=SOLO_ACTIVITY,
            capacity=1,
            one_shot=False,
            recover_after_ticks=SITE_RECOVERY_TICKS,
        )
        self.enterContext(
            patch.object(
                monster_sites,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType({SITE_KEY: self.site}),
            )
        )
        self._wandering_seed: int | None = None
        self._travelling_seed: int | None = None

    def _stay_seed(self, cell: tuple[int, int]) -> int:
        """A seed whose first decision is a stay, with no earlier group."""
        if self._wandering_seed is None:
            self._wandering_seed = self._seed_for(
                depart=False, activity=GROUP_ACTIVITY, cell=cell
            )
        return self._wandering_seed

    def _departure_seed(self, cell: tuple[int, int], wandering: int) -> int:
        """A seed whose first decision departs, after the wandering group."""
        if self._travelling_seed is None:
            self._travelling_seed = self._seed_for(
                depart=True,
                activity=SOLO_ACTIVITY,
                cell=cell,
                prefix=(GROUP_ACTIVITY, wandering),
            )
        return self._travelling_seed

    def _cleared_site_record(self) -> dict:
        """One cleared, recoverable site that repopulates inside the scenario."""
        return {
            SITE_KEY: {
                "state": monster_sites.SITE_STATE_CLEARED,
                "cleared_at_tick": START,
                "seed": monster_sites._site_seed(self.wilderness, self.site),
                "generation_sequence": 0,
                # The defeated identities stay recorded across a clear; no
                # recovered group ever reuses one.
                "member_ids": [DEFEATED_ID],
            }
        }

    def _build_scenario(self) -> tuple[int, ...]:
        """Rebuild the identical starting world of the differential test."""
        wandering = self._stay_seed(WANDERING_CELL)
        travelling = self._departure_seed(TRAVELLING_CELL, wandering)
        self._reset_activity(tick=START)
        self.wilderness.db.regional_population = {}
        self.wilderness.db.monster_sites = self._cleared_site_record()
        self._group(cell=WANDERING_CELL, seed=wandering, tick=START, owner_key=ZONE_KEY)
        self._group(
            cell=TRAVELLING_CELL,
            seed=travelling,
            tick=START,
            activity=SOLO_ACTIVITY,
            owner_key=ZONE_KEY,
        )
        created = initialize_zone(self.wilderness, ZONE_KEY, seed=SEED, tick=START)
        # One loss leaves the zone exactly one member below its lower density,
        # so the pass has a real due episode and a real mid-pass birth.
        self._kill(Monster.objects.get(pk=created[0]), START)
        return created

    def _reuse(self, enabled: bool):
        if enabled:
            return contextlib.nullcontext()
        return patch.object(
            regional_population, "reused_living_presence", contextlib.nullcontext
        )

    def _settle(self, parts: tuple[int, ...], *, reuse: bool) -> dict:
        """Rebuild the scenario, settle each duration in turn, project the state."""
        self._build_scenario()
        tick = START
        with self._reuse(reuse):
            for part in parts:
                settle_population_lifecycle(tick, tick + part)
                tick += part
        return settlement_projection(self.wilderness)


class DifferentialSettlementTests(ScenarioSettlementFixture):
    """Reuse on and off leave the same state under every interval partition."""

    @covers_requirement(
        "regional-population::reuse-leaves-settlement-results-unchanged"
    )
    def test_reuse_leaves_the_same_state_under_every_partition(self):
        partitions = ((1500,), (700, 800), (61, 1439))
        projections = {
            (parts, reuse): self._settle(parts, reuse=reuse)
            for parts in partitions
            for reuse in (True, False)
        }
        reference = projections[((1500,), True)]
        for (parts, reuse), projection in projections.items():
            self.assertEqual(
                projection,
                reference,
                msg=f"partition {parts} with reuse={reuse}",
            )
        # The scenario really settled: a due episode, a site recovery and a
        # journey all happened, so the equality above is not an untouched state.
        self.assertGreater(reference["zones"][ZONE_KEY]["generation_sequence"], 0)
        self.assertEqual(
            reference["sites"][SITE_KEY]["state"],
            monster_sites.SITE_STATE_POPULATED,
        )
        self.assertTrue(reference["activity"]["journeys"])
