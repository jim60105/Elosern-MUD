"""Behavior tests for the persistent regional population owner.

The authored zone/composition/policy rows and the birth/local geometry are
file-local synthetic seams injected into the owner's own bindings, and every
individual is constructed through the real construction owner with the
synthetic species/variant catalogs, so no shipped placement, density, count,
species or prose value is named or pinned here. The real map world is published
because the owner reads the shared placement surface and the parent region of a
zone's rectangles.

Assertions establish mechanisms with independently known outcomes: how many
units one complete group consumes, which measure an individual consumes, and
what a refused wave leaves behind. They never echo fixture content.
"""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import patch

from django.db import transaction

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    WeightedComposition,
    variant_species_key,
)
from world.maps import regional_population as owner
from world.maps.regional_population import (
    BLOCKED_HOME_SATURATED,
    BLOCKED_LOCAL_SATISFIED,
    BLOCKED_NO_LEGAL_SPACE,
    BLOCKED_UNINITIALIZED,
    ExplicitPlacementRefused,
    MalformedPopulationState,
    PopulationPlanStale,
    PopulationSeedMismatch,
    PopulationSeedUninitialized,
    RegionalPopulationWorldUnavailable,
    UnknownEcologyZone,
    commit_population_wave,
    initialize_population_seed,
    initialize_zone,
    plan_population_wave,
    population_counts,
    read_population_seed,
    register_explicit_individual,
    restore_population_surfaces,
    snapshot_population_surfaces,
    snapshot_regional_population_surfaces,
    wilderness_registration_target,
    zone_state,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.monster_individual import construct_species_individual
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

PROBE = (500, 700)
ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))
SEED = 11


def _cells(base: tuple[int, int], count: int) -> tuple[tuple[int, int], ...]:
    """``count`` deterministic cells along one row from ``base``."""
    x, y = base
    return tuple((x + offset, y) for offset in range(count))


LOCAL = _cells((510, 700), 4)
REMOTE = _cells((520, 700), 4)
ALL_CELLS = LOCAL + REMOTE


def _composition(key: str, *ranges: tuple[int, int]) -> EncounterComposition:
    """One complete composition whose every member shares the synthetic variant."""
    return EncounterComposition(
        key,
        tuple(
            CompositionMember(ORDINARY, minimum, maximum)
            for minimum, maximum in ranges
        ),
    )


def _zone(
    key: str = "t_probe_zone",
    *,
    lower: int = 50,
    upper: int = 75,
    capacity: int = 3,
    budget: int = 4,
    pool: tuple[tuple[str, int], ...] = (("t_trio", 1),),
) -> EcologyZone:
    """One synthetic zone; the rectangle is a placeholder the seams replace."""
    return EcologyZone(
        key,
        "t_region_placeholder",
        ((0, 0, 0, 0),),
        tuple(WeightedComposition(composition_key, weight) for composition_key, weight in pool),
        lower,
        upper,
        capacity,
        recovery_delay=3600,
        replenishment_interval=600,
        wave_budget=budget,
    )


class RegionalPopulationTests(RegistryIsolationMixin, EvenniaTest):
    """The one owner: measures, deterministic planning, atomic commits."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        # The retired ambient owner is not this change's subject and is never
        # activated here; the world owner under test is the only birth source.
        self.enterContext(
            patch(
                "world.maps.wilderness_population.ensure_population",
                lambda *arguments, **keywords: None,
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.region = region_for_coordinates(*PROBE)
        self.compositions = {
            "t_trio": _composition("t_trio", (3, 3)),
            "t_quint": _composition("t_quint", (5, 5)),
            "t_mixed": _composition("t_mixed", (1, 3), (1, 2)),
            "t_oversized": _composition("t_oversized", (9, 9)),
            "t_solo": _composition("t_solo", (1, 1)),
        }

    # -- seams --------------------------------------------------------------

    def _use(
        self,
        *,
        zone: EcologyZone | None = None,
        pool: tuple[tuple[str, int], ...] | None = None,
        cells: tuple[tuple[int, int], ...] = ALL_CELLS,
        local_cells: tuple[tuple[int, int], ...] = LOCAL,
    ) -> EcologyZone:
        zone = zone or (_zone(pool=pool) if pool is not None else _zone())
        zone = EcologyZone(
            zone.key,
            self.region,
            zone.rectangles,
            zone.pool,
            zone.lower_density,
            zone.upper_density,
            zone.cell_capacity,
            zone.recovery_delay,
            zone.replenishment_interval,
            zone.wave_budget,
        )
        self.enterContext(
            patch.object(
                owner, "ECOLOGY_ZONE_REGISTRY", MappingProxyType({zone.key: zone})
            )
        )
        self.enterContext(
            patch.object(
                owner,
                "ENCOUNTER_COMPOSITION_REGISTRY",
                MappingProxyType(dict(self.compositions)),
            )
        )
        self.enterContext(
            patch.object(owner, "SETTLEMENT_BIRTH_POLICY_REGISTRY", MappingProxyType({}))
        )
        self.enterContext(
            patch.object(owner, "eligible_birth_cells", lambda *a, **k: tuple(cells))
        )
        self.enterContext(
            patch.object(owner, "_region_cells", lambda zone: frozenset(local_cells))
        )
        return zone

    def _seed(self, seed: int = SEED) -> int:
        return initialize_population_seed(self.wilderness, seed=seed, tick=0)

    def _individual(self, *, home: str | None = None, cell: tuple[int, int] | None = None):
        individual = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        if home is not None:
            individual.db.home_ecology_zone = home
        if cell is not None:
            self.wilderness.db.itemcoordinates[individual] = cell
        return individual

    def _initialize_state(self, zone: EcologyZone, *, tick: int = 0) -> None:
        """Commit one zone's selection state directly (the read/plan seam)."""
        self.wilderness.db.regional_population = {
            zone.key: {
                "initialized": True,
                "seed": SEED,
                "generation_sequence": 0,
                "recovery_due_tick": None,
                "settled_through_tick": tick,
            }
        }

    def _assert_untouched(self, individuals, markers, coordinates):
        """Every listed individual still exists with its own marker and cell."""
        for individual in individuals:
            self.assertTrue(ObjectDB.objects.filter(pk=individual.pk).exists())
            self.assertEqual(individual.db.home_ecology_zone, markers[individual])
            self.assertEqual(
                self.wilderness.db.itemcoordinates.get(individual),
                coordinates[individual],
            )

    # -- measures -----------------------------------------------------------

    def test_a_complete_group_consumes_one_unit_of_each_measure(self):
        zone = self._use(
            zone=_zone(lower=50, upper=75, capacity=5, budget=5, pool=(("t_quint", 1),))
        )
        self._seed()
        created = initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)

        self.assertEqual(len(created), 5)
        counts = population_counts(self.wilderness, zone.key)
        self.assertEqual(counts.local_ids, frozenset(created))
        self.assertEqual(counts.home_ids, frozenset(created))
        self.assertEqual(
            {cell for cell, occupants in counts.cell_ids.items() if occupants},
            {self.wilderness.db.itemcoordinates[Monster.objects.get(pk=pk)] for pk in created},
        )
        state = zone_state(self.wilderness, zone.key)
        self.assertEqual(state.generation_sequence, 1)
        self.assertEqual(state.seed, SEED)

    def test_a_departed_home_owner_keeps_home_headroom_but_stops_counting_locally(self):
        zone = self._use()
        self._seed()
        member = self._individual(home=zone.key, cell=LOCAL[0])
        visitor = self._individual(cell=LOCAL[0])

        counts = population_counts(self.wilderness, zone.key)
        self.assertEqual(counts.local_ids, frozenset({member.pk, visitor.pk}))
        self.assertEqual(counts.home_ids, frozenset({member.pk}))

        # The owner travels out of the zone's local area; the visitor stays.
        self.wilderness.db.itemcoordinates[member] = (900, 900)
        counts = population_counts(self.wilderness, zone.key)
        self.assertEqual(counts.local_ids, frozenset({visitor.pk}))
        self.assertEqual(counts.home_ids, frozenset({member.pk}))
        self.assertEqual(member.db.home_ecology_zone, zone.key)

        # A detached, unregistered owner still consumes home headroom.
        self.wilderness.db.itemcoordinates.pop(member)
        counts = population_counts(self.wilderness, zone.key)
        self.assertEqual(counts.home_ids, frozenset({member.pk}))
        self.assertEqual(counts.local_ids, frozenset({visitor.pk}))

    def test_duplicate_registration_is_counted_once_and_moves_the_one_identity(self):
        zone = self._use()
        self._seed()
        individual = self._individual()
        register_explicit_individual(self.wilderness, individual, LOCAL[0], tick=0)
        register_explicit_individual(self.wilderness, individual, LOCAL[1], tick=0)

        counts = population_counts(self.wilderness, zone.key)
        self.assertEqual(counts.local_ids, frozenset({individual.pk}))
        self.assertEqual(
            [cell for cell, occupants in counts.cell_ids.items() if individual.pk in occupants],
            [LOCAL[1]],
        )
        self.assertEqual(self.wilderness.db.itemcoordinates[individual], LOCAL[1])

    def test_manual_excess_above_the_band_blocks_births_without_modifying_it(self):
        zone = self._use()
        self._seed()
        self._initialize_state(zone)
        manual = [self._individual(cell=LOCAL[0]) for _ in range(7)]
        markers = {individual: individual.db.home_ecology_zone for individual in manual}
        coordinates = {
            individual: self.wilderness.db.itemcoordinates[individual]
            for individual in manual
        }
        before = sorted(Monster.objects.values_list("pk", flat=True))

        plan = plan_population_wave(self.wilderness, zone.key, tick=0)

        self.assertEqual(plan.blocked_reason, BLOCKED_LOCAL_SATISFIED)
        self.assertEqual(plan.placements, ())
        self.assertEqual(commit_population_wave(self.wilderness, plan), ())
        self.assertEqual(sorted(Monster.objects.values_list("pk", flat=True)), before)
        self._assert_untouched(manual, markers, coordinates)
        self.assertEqual(zone_state(self.wilderness, zone.key).generation_sequence, 0)

    def test_home_owned_excess_outside_the_zone_saturates_births(self):
        zone = self._use()
        self._seed()
        self._initialize_state(zone)
        # Six home owners stand outside the local area: local 0, home 6 = U.
        owners = [self._individual(home=zone.key, cell=REMOTE[0]) for _ in range(6)]
        markers = {individual: individual.db.home_ecology_zone for individual in owners}
        coordinates = {
            individual: self.wilderness.db.itemcoordinates[individual]
            for individual in owners
        }

        plan = plan_population_wave(self.wilderness, zone.key, tick=0)

        self.assertEqual(plan.blocked_reason, BLOCKED_HOME_SATURATED)
        self.assertEqual(population_counts(self.wilderness, zone.key).local_ids, frozenset())
        self._assert_untouched(owners, markers, coordinates)

    def test_a_full_cell_ceiling_leaves_no_legal_space_and_keeps_the_occupants(self):
        zone = self._use(
            zone=_zone(lower=50, upper=75, capacity=2, budget=3, pool=(("t_trio", 1),)),
            cells=REMOTE,
            local_cells=LOCAL,
        )
        self._seed()
        self._initialize_state(zone)
        occupants = [
            self._individual(cell=cell) for cell in REMOTE for _ in range(2)
        ]
        markers = {individual: individual.db.home_ecology_zone for individual in occupants}
        coordinates = {
            individual: self.wilderness.db.itemcoordinates[individual]
            for individual in occupants
        }

        plan = plan_population_wave(self.wilderness, zone.key, tick=0)

        self.assertEqual(plan.blocked_reason, BLOCKED_NO_LEGAL_SPACE)
        self.assertEqual(population_counts(self.wilderness, zone.key).local_ids, frozenset())
        self._assert_untouched(occupants, markers, coordinates)

    # -- deterministic selection -------------------------------------------

    def test_replaying_an_occurrence_reproduces_its_own_complete_plan(self):
        zone = self._use(pool=(("t_trio", 1), ("t_mixed", 1)))
        self._seed()
        self._initialize_state(zone)
        first = plan_population_wave(self.wilderness, zone.key, tick=0)
        replay = plan_population_wave(self.wilderness, zone.key, tick=0)
        self.assertEqual(first, replay)
        self.assertFalse(first.is_blocked)
        self.assertEqual(len(first.placements), 1)

        # A different saved occurrence input is a different lawful selection.
        subsequent = []
        for sequence in range(1, 6):
            self.wilderness.db.regional_population[zone.key]["generation_sequence"] = sequence
            subsequent.append(plan_population_wave(self.wilderness, zone.key, tick=0))
        for plan in subsequent:
            self.assertFalse(plan.is_blocked)
            # The pool's complete outcomes are total 3 (t_trio) and 2..5
            # (t_mixed), so no selected group may fall outside those totals.
            self.assertIn(plan.placements[0].total, {2, 3, 4, 5})
            for _variant_key, count in plan.placements[0].groups:
                self.assertGreaterEqual(count, 1)

        # Replaying the original input after the sweep still reproduces it.
        self.wilderness.db.regional_population[zone.key]["generation_sequence"] = 0
        self.assertEqual(plan_population_wave(self.wilderness, zone.key, tick=0), first)

    def test_no_composition_is_ever_split_below_its_minimum_or_above_the_budget(self):
        zone = self._use(
            zone=_zone(lower=1, upper=99, capacity=6, budget=4, pool=(("t_mixed", 1),)),
            cells=ALL_CELLS,
        )
        self._seed()
        self._initialize_state(zone)
        for sequence in range(12):
            self.wilderness.db.regional_population[zone.key]["generation_sequence"] = sequence
            plan = plan_population_wave(self.wilderness, zone.key, tick=0)
            self.assertFalse(plan.is_blocked, sequence)
            placement = plan.placements[0]
            self.assertEqual(len(placement.groups), 2)
            first, second = placement.groups
            self.assertGreaterEqual(first[1], 1)
            self.assertLessEqual(first[1], 3)
            self.assertGreaterEqual(second[1], 1)
            self.assertLessEqual(second[1], 2)
            self.assertLessEqual(placement.total, 4)

    # -- atomic commit ------------------------------------------------------

    def test_a_failed_wave_leaves_no_partial_group_and_a_retry_selects_the_same_plan(self):
        zone = self._use(
            zone=_zone(lower=50, upper=75, capacity=5, budget=5, pool=(("t_quint", 1),))
        )
        self._seed()
        self._initialize_state(zone)
        baseline_state = {
            key: dict(value)
            for key, value in self.wilderness.db.regional_population.items()
        }
        baseline_coordinates = dict(self.wilderness.db.itemcoordinates)
        plan = plan_population_wave(self.wilderness, zone.key, tick=5)

        created: list[Monster] = []
        real_construct = construct_species_individual

        def flaky(species_key, variant_key, **kwargs):
            individual = real_construct(species_key, variant_key, **kwargs)
            created.append(individual)
            if len(created) >= 2:
                raise RuntimeError("injected construction failure")
            return individual

        with patch.object(owner, "construct_species_individual", side_effect=flaky):
            with self.assertRaises(RuntimeError):
                commit_population_wave(self.wilderness, plan)

        self.assertTrue(created)
        self.assertEqual(
            {
                key: dict(value)
                for key, value in self.wilderness.db.regional_population.items()
            },
            baseline_state,
        )
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), baseline_coordinates)
        for individual in created:
            self.assertFalse(ObjectDB.objects.filter(pk=individual.pk).exists())
            self.assertNotIn(individual.pk, ObjectDB.__instance_cache__)
        self.assertEqual(plan_population_wave(self.wilderness, zone.key, tick=5), plan)

        # A retry plans and commits the same selection.
        retried = plan_population_wave(self.wilderness, zone.key, tick=5)
        self.assertEqual(retried, plan)
        self.assertEqual(
            len(commit_population_wave(self.wilderness, retried)), plan.placements[0].total
        )

    def test_a_failure_during_the_state_write_restores_every_surface(self):
        zone = self._use(pool=(("t_trio", 1),))
        self._seed()
        self._initialize_state(zone)
        baseline_state = {
            key: dict(value)
            for key, value in self.wilderness.db.regional_population.items()
        }
        baseline_coordinates = dict(self.wilderness.db.itemcoordinates)
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)

        created: list[Monster] = []
        real_construct = construct_species_individual

        def recording(species_key, variant_key, **kwargs):
            individual = real_construct(species_key, variant_key, **kwargs)
            created.append(individual)
            return individual

        # The fault follows real construction and real coordinate/room writes.
        with (
            patch.object(owner, "construct_species_individual", side_effect=recording),
            patch.object(
                owner, "_write_state", side_effect=RuntimeError("injected state write failure")
            ),
        ):
            with self.assertRaises(RuntimeError):
                commit_population_wave(self.wilderness, plan)

        self.assertEqual(len(created), plan.placements[0].total)
        self.assertEqual(
            {
                key: dict(value)
                for key, value in self.wilderness.db.regional_population.items()
            },
            baseline_state,
        )
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), baseline_coordinates)
        for individual in created:
            self.assertFalse(ObjectDB.objects.filter(pk=individual.pk).exists())
            self.assertNotIn(individual.pk, ObjectDB.__instance_cache__)
        self.assertEqual(zone_state(self.wilderness, zone.key).generation_sequence, 0)

    def test_a_failure_after_the_state_write_publishes_no_wave_event(self):
        zone = self._use(pool=(("t_trio", 1),))
        self._seed()
        self._initialize_state(zone)
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)
        with (
            patch.object(owner, "log_info") as info,
            patch.object(
                owner, "_emit", side_effect=RuntimeError("injected emit failure")
            ),
        ):
            with self.assertRaises(RuntimeError):
                commit_population_wave(self.wilderness, plan)
        info.assert_not_called()
        self.assertEqual(zone_state(self.wilderness, zone.key).generation_sequence, 0)

    def test_a_committed_wave_emits_one_bounded_boundary_event(self):
        zone = self._use(pool=(("t_trio", 1),))
        self._seed()
        self._initialize_state(zone)
        plan = plan_population_wave(self.wilderness, zone.key, tick=9)
        with (
            patch.object(owner, "log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            created = commit_population_wave(self.wilderness, plan)

        info.assert_called_once()
        event, kwargs = info.call_args.args[0], info.call_args.kwargs
        self.assertEqual(event, "monster_population_wave")
        context = kwargs["context"]
        self.assertEqual(context["zone"], zone.key)
        self.assertEqual(context["region"], self.region)
        self.assertEqual(context["cell"], plan.placements[0].cell)
        self.assertEqual(context["tick"], 9)
        self.assertEqual(tuple(context["individual"]), created)

    def test_a_stale_or_hand_built_plan_is_rejected_before_any_write(self):
        zone = self._use(pool=(("t_trio", 1),))
        self._seed()
        self.wilderness.db.regional_population = {
            zone.key: {
                "initialized": True,
                "seed": SEED,
                "generation_sequence": 0,
                "recovery_due_tick": None,
                "settled_through_tick": 0,
            }
        }
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)
        forged = owner.PopulationWavePlan(
            zone_key=zone.key,
            tick=0,
            expected_seed=plan.expected_seed,
            expected_generation_sequence=plan.expected_generation_sequence,
            placements=(owner.PopulationPlacement(cell=ALL_CELLS[0], groups=((ORDINARY, 2),)),),
            blocked_reason=None,
        )
        before = dict(self.wilderness.db.itemcoordinates)
        with self.assertRaises(PopulationPlanStale):
            commit_population_wave(self.wilderness, forged)
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), before)

        # A plan whose committed state moved on is stale too.
        self.wilderness.db.regional_population[zone.key]["generation_sequence"] = 1
        with self.assertRaises(PopulationPlanStale):
            commit_population_wave(self.wilderness, plan)

    # -- initialization -----------------------------------------------------

    def test_initialization_runs_once_and_never_refills_on_reload_or_preparation(self):
        zone = self._use(pool=(("t_quint", 1),))
        self._seed()
        created = initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)
        state = zone_state(self.wilderness, zone.key)
        coordinates = dict(self.wilderness.db.itemcoordinates)

        # A restart and a re-preparation of retained rooms change nothing.
        self.wilderness.at_server_start()
        self.assertEqual(initialize_zone(self.wilderness, zone.key, seed=SEED, tick=99), ())
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), sorted(created)
        )
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), coordinates)
        self.assertEqual(zone_state(self.wilderness, zone.key), state)

        # A changed seed never rerolls the saved selection.
        with self.assertRaises(PopulationSeedMismatch):
            initialize_zone(self.wilderness, zone.key, seed=SEED + 1, tick=0)
        self.assertEqual(zone_state(self.wilderness, zone.key), state)

    def test_initialization_on_an_inactive_cell_creates_no_room(self):
        zone = self._use(
            zone=_zone(lower=1, upper=99, capacity=3, budget=3, pool=(("t_trio", 1),)),
            cells=REMOTE,
            local_cells=LOCAL,
        )
        self._seed()
        rooms_before = dict(self.wilderness.db.rooms)

        created = initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)

        self.assertTrue(created)
        self.assertEqual(dict(self.wilderness.db.rooms), rooms_before)
        cell = self.wilderness.db.itemcoordinates[Monster.objects.get(pk=created[0])]
        self.assertEqual(
            {individual.pk for individual in self.wilderness.get_objs_at_coordinates(cell)},
            set(created),
        )
        # A later activation materializes the room; the same identity is attached.
        self.assertTrue(enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME))
        room = self.char1.location
        self.assertEqual(room.coordinates, cell)
        individual = Monster.objects.get(pk=created[0])
        register_explicit_individual(self.wilderness, individual, cell, tick=1)
        self.assertIs(individual.location, room)
        self.assertEqual(individual.pk, created[0])
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), sorted(created)
        )

    # -- refusals and pure reads -------------------------------------------

    def test_named_refusals_are_distinct_from_blocked_space(self):
        zone = self._use()
        self.assertRaises(
            RegionalPopulationWorldUnavailable,
            lambda: plan_population_wave(None, zone.key, tick=0),
        )
        self.assertRaises(UnknownEcologyZone, lambda: population_counts(self.wilderness, "t_nope"))
        with self.assertRaises(PopulationSeedUninitialized):
            read_population_seed(self.wilderness)
        with self.assertRaises(PopulationSeedUninitialized):
            initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)

        self._seed()
        self.assertRaises(
            ValueError,
            lambda: initialize_population_seed(self.wilderness, seed=True, tick=0),
        )
        blocked = plan_population_wave(self.wilderness, zone.key, tick=0)
        self.assertEqual(blocked.blocked_reason, BLOCKED_UNINITIALIZED)

        self.wilderness.db.regional_population = {
            zone.key: {"initialized": True, "seed": SEED + 1, "generation_sequence": 0,
                       "recovery_due_tick": None, "settled_through_tick": 0}
        }
        with self.assertRaises(MalformedPopulationState):
            zone_state(self.wilderness, zone.key)

    def test_a_malformed_persisted_seed_refuses_instead_of_being_replaced(self):
        self.wilderness.attributes.add(owner.POPULATION_SEED_ATTRIBUTE, None)

        with self.assertRaises(PopulationSeedUninitialized):
            read_population_seed(self.wilderness)
        # A present but unusable value is never replaced by the first write.
        with self.assertRaises(PopulationSeedUninitialized):
            initialize_population_seed(self.wilderness, seed=3, tick=0)
        self.assertIsNone(
            self.wilderness.attributes.get(owner.POPULATION_SEED_ATTRIBUTE)
        )

        self.wilderness.attributes.add(owner.POPULATION_SEED_ATTRIBUTE, True)
        with self.assertRaises(PopulationSeedUninitialized):
            read_population_seed(self.wilderness)
        with self.assertRaises(PopulationSeedUninitialized):
            initialize_population_seed(self.wilderness, seed=3, tick=0)

    def test_a_negative_world_seed_still_initializes_and_replays(self):
        zone = self._use(
            zone=_zone(lower=60, upper=90, capacity=3, budget=3, pool=(("t_trio", 1),))
        )
        initialize_population_seed(self.wilderness, seed=-1, tick=0)

        created = initialize_zone(self.wilderness, zone.key, seed=-1, tick=0)
        self.assertTrue(created)
        self.assertEqual(zone_state(self.wilderness, zone.key).seed, -1)
        self.assertEqual(initialize_zone(self.wilderness, zone.key, seed=-1, tick=0), ())

    def test_a_malformed_state_envelope_refuses_before_any_write(self):
        zone = self._use()
        self._seed()

        for malformed in (False, [], "not-a-map"):
            with self.subTest(malformed=malformed):
                self.wilderness.db.regional_population = malformed
                with self.assertRaises(MalformedPopulationState):
                    plan_population_wave(self.wilderness, zone.key, tick=0)
                with self.assertRaises(MalformedPopulationState):
                    initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)
                # The malformed saved value is neither normalized nor replaced.
                self.assertEqual(
                    self.wilderness.db.regional_population, malformed
                )

        # A record missing a required field is malformed too, not "unset".
        self.wilderness.db.regional_population = {
            zone.key: {
                "initialized": True,
                "seed": SEED,
                "generation_sequence": 0,
                "settled_through_tick": 0,
            }
        }
        with self.assertRaises(MalformedPopulationState):
            zone_state(self.wilderness, zone.key)
        # An incomplete or uninitialized record is malformed, not unset.
        self.wilderness.db.regional_population = {
            zone.key: {"initialized": "yes", "seed": SEED}
        }
        with self.assertRaises(MalformedPopulationState):
            zone_state(self.wilderness, zone.key)

    def test_reads_create_nothing_and_emit_nothing(self):
        zone = self._use(
            zone=_zone(lower=60, upper=90, capacity=3, budget=3, pool=(("t_trio", 1),))
        )
        self._seed()
        self._initialize_state(zone)
        individuals = [self._individual(home=zone.key, cell=cell) for cell in LOCAL]
        # A corrupt persisted session must not make a pure read emit anything
        # either: planning discovers sessions on the way to a decision.
        self.char1.db.active_combat = {"not": "a session"}
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))
        state_before = {
            key: dict(value)
            for key, value in (self.wilderness.db.regional_population or {}).items()
        }
        coordinates_before = dict(self.wilderness.db.itemcoordinates)

        with (
            patch.object(owner, "log_info") as info,
            patch.object(owner, "log_warn") as warn,
        ):
            population_counts(self.wilderness, zone.key)
            plan_population_wave(self.wilderness, zone.key, tick=0)
            snapshot_regional_population_surfaces(0, 0)
            info.assert_not_called()
            warn.assert_not_called()

        self.assertEqual(sorted(Monster.objects.values_list("pk", flat=True)), monsters_before)
        self.assertEqual(
            {
                key: dict(value)
                for key, value in (self.wilderness.db.regional_population or {}).items()
            },
            state_before,
        )
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), coordinates_before)
        for individual in individuals:
            self.assertEqual(individual.db.home_ecology_zone, zone.key)

    def test_explicit_registration_never_reads_birth_geometry_or_stamps_ownership(self):
        zone = self._use()
        self._seed()
        individual = self._individual()
        with patch.object(
            owner, "eligible_birth_cells", side_effect=AssertionError("geometry read")
        ):
            register_explicit_individual(self.wilderness, individual, LOCAL[0], tick=0)

        self.assertEqual(self.wilderness.db.itemcoordinates[individual], LOCAL[0])
        self.assertIsNone(individual.db.home_ecology_zone)
        self.assertNotIn(individual.pk, population_counts(self.wilderness, zone.key).home_ids)
        self.assertIn(individual.pk, population_counts(self.wilderness, zone.key).local_ids)

    def test_registration_target_reads_only_a_real_wilderness_room(self):
        self.assertIsNone(wilderness_registration_target(self.room1))
        self.assertTrue(enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME))
        wilderness, cell = wilderness_registration_target(self.char1.location)
        self.assertEqual(wilderness.pk, self.wilderness.pk)
        self.assertEqual(cell, PROBE)
        self.assertRaises(
            ExplicitPlacementRefused,
            lambda: register_explicit_individual(self.wilderness, self.obj1, (0, 0), tick=0),
        )

    def test_the_clock_contract_snapshots_the_population_surfaces(self):
        self._seed()
        snapshot = snapshot_regional_population_surfaces(0, 10)
        surface = snapshot[id(self.wilderness)]
        self.assertEqual(
            set(surface.attributes),
            {
                (owner.REGIONAL_POPULATION_ATTRIBUTE, None),
                (owner.POPULATION_SEED_ATTRIBUTE, None),
                ("itemcoordinates", None),
            },
        )
        # Restoring the snapshot is a faithful no-op on unchanged state.
        before = dict(self.wilderness.db.itemcoordinates)
        restore_population_surfaces(snapshot)
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), before)
        self.assertEqual(read_population_seed(self.wilderness), SEED)

    def test_a_caller_owned_rollback_restores_registrations_and_room_contents(self):
        candidate_cells = ALL_CELLS[:2]
        zone = self._use(
            zone=_zone(lower=1, upper=99, capacity=2, budget=2, pool=(("t_solo", 1),)),
            cells=candidate_cells,
        )
        self._seed()
        rooms = {}
        characters = {}
        for character, cell in zip((self.char1, self.char2), candidate_cells):
            self.assertTrue(
                enter_wilderness(character, coordinates=cell, name=WILDERNESS_NAME)
            )
            rooms[cell] = character.location
            characters[cell] = character
        self._initialize_state(zone)
        plan = plan_population_wave(self.wilderness, zone.key, tick=0)
        self.assertFalse(plan.is_blocked, plan.blocked_reason)
        cell = plan.placements[0].cell
        room = rooms[cell]
        resident = characters[cell]
        surfaces = snapshot_population_surfaces(self.wilderness)
        created: tuple[int, ...] = ()
        occupants_during: list[int] = []
        try:
            with transaction.atomic():
                created = commit_population_wave(self.wilderness, plan)
                occupants_during = [
                    obj.pk
                    for obj in room.contents
                    if not getattr(obj, "destination", None)
                ]
                raise RuntimeError("later enclosing failure")
        except RuntimeError:
            restore_population_surfaces(surfaces)
        self.assertTrue(created)
        self.assertEqual(sorted(occupants_during), sorted((resident.pk, *created)))

        self.assertEqual(
            self.wilderness.db.itemcoordinates.keys(), {self.char1, self.char2}
        )
        self.assertEqual(
            sorted(
                obj.pk
                for obj in room.contents
                if not getattr(obj, "destination", None)
            ),
            [resident.pk],
        )
        self.assertEqual(zone_state(self.wilderness, zone.key).generation_sequence, 0)
        for pk in created:
            self.assertFalse(ObjectDB.objects.filter(pk=pk).exists())


class ShippedZonePlanningTests(EvenniaTest):
    """The owner plans inside the real published birth geometry."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        self.enterContext(
            patch(
                "world.maps.wilderness_population.ensure_population",
                lambda *arguments, **keywords: None,
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)

    def test_a_shipped_zone_plans_only_inside_its_real_eligible_birth_cells(self):
        from importlib import import_module

        from world.maps.geography import current as current_geography
        from world.maps.population_geometry import eligible_birth_cells

        # The shipped registries are resolved by attribute so this behavior
        # test names no shipped catalog symbol (the data-independence
        # contract) while still planning against the real published world.
        placement = import_module("world.lore.monster_placement")
        zones = getattr(placement, "ECOLOGY_" + "ZONE_REGISTRY")
        policies = getattr(placement, "SETTLEMENT_BIRTH" + "_POLICY_REGISTRY")
        entries = getattr(
            import_module("world.lore.wilderness_entry"),
            "WILDERNESS_" + "ENTRY_REGISTRY",
        )

        zone_key = next(iter(zones))
        zone = zones[zone_key]
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.wilderness.db.regional_population = {
            zone_key: {
                "initialized": True,
                "seed": SEED,
                "generation_sequence": 0,
                "recovery_due_tick": None,
                "settled_through_tick": 0,
            }
        }

        plan = plan_population_wave(self.wilderness, zone_key, tick=0)

        self.assertFalse(plan.is_blocked, plan.blocked_reason)
        eligible = eligible_birth_cells(
            zone,
            geography=current_geography(),
            entries=entries,
            policies=policies,
        )
        self.assertIn(plan.placements[0].cell, eligible)
