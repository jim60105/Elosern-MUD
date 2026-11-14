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
    PopulationTransition,
    initialize_zone,
    presence_of,
    record_population_transition,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_monster_activity import (
    GROUP_ACTIVITY,
    PROBE,
    SOLO_ACTIVITY,
    ActivityFixture,
)
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


class ScenarioSettlementFixture(ActivityFixture):
    """A synthetic world with two groups, a deficit zone and a due site."""

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
        self.enterContext(
            patch.object(
                monster_sites,
                "MONSTER_SITE_REGISTRY",
                MappingProxyType({SITE_KEY: self.site}),
            )
        )
        self._wandering_seed: int | None = None
        self._travelling_seed: int | None = None

    # -- scenario seams -----------------------------------------------------

    def _stay_seed_at(self, cell: tuple[int, int]) -> int:
        """A seed whose first decision at the probe's cadence is a stay."""
        if self._wandering_seed is not None:
            return self._wandering_seed
        interval = monster_activity.activity_decision_interval(GROUP_ACTIVITY)
        for seed in range(64):
            self._reset_activity(tick=START)
            group_id, _bodies = self._group(cell=cell, seed=seed, tick=START)
            decision = monster_activity.plan_group_decision(
                self.wilderness, group_id, tick=START + interval
            )
            if decision.edge is None:
                self._wandering_seed = seed
                return seed
        raise AssertionError("no seed produced a lawful stay at the first decision")

    def _departure_seed_at(self, cell: tuple[int, int], wandering: int) -> int:
        """A seed whose first decision is a lawful departure, after group one."""
        if self._travelling_seed is not None:
            return self._travelling_seed
        interval = monster_activity.activity_decision_interval(SOLO_ACTIVITY)
        for seed in range(64):
            self._reset_activity(tick=START)
            self._group(cell=WANDERING_CELL, seed=wandering, tick=START)
            group_id, _bodies = self._group(
                cell=cell, seed=seed, tick=START, activity=SOLO_ACTIVITY
            )
            decision = monster_activity.plan_group_decision(
                self.wilderness, group_id, tick=START + interval
            )
            if decision.edge is not None:
                self._travelling_seed = seed
                return seed
        raise AssertionError("no seed produced a lawful departure at the first decision")

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

    def _build_scenario(self) -> tuple[int, ...]:
        """Rebuild the identical starting world of the differential test."""
        wandering = self._stay_seed_at(WANDERING_CELL)
        travelling = self._departure_seed_at(TRAVELLING_CELL, wandering)
        self._reset_activity(tick=START)
        self.wilderness.db.regional_population = {}
        self.wilderness.db.monster_sites = self._cleared_site_record()
        self._group(cell=WANDERING_CELL, seed=wandering, tick=START)
        self._group(
            cell=TRAVELLING_CELL,
            seed=travelling,
            tick=START,
            activity=SOLO_ACTIVITY,
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
        self.assertEqual(reference["sites"][SITE_KEY]["state"], monster_sites.SITE_STATE_POPULATED)
        self.assertTrue(reference["activity"]["journeys"])
