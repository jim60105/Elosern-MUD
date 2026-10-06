"""Behavior tests for acceptance-time hunt target provisioning (task 3.1).

The ambient placement rows, sites, and species/variant identities are file-local
synthetic fixtures injected through the synthetic test-data kit's ``extra=``
seam, and every region key is read from the live terrain model at runtime, so no
shipped placement, species, variant, or region token is named as test content.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from django.db import transaction
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.lore.monster_placement import AmbientPlacementRule, MonsterSite
from world.maps.monster_provisioning import (
    PROVISION_NO_AMBIENT_RULE,
    PROVISION_NO_ELIGIBLE_VARIANT,
    PROVISION_CAPACITY_EXHAUSTED,
    PROVISION_WORLD_UNAVAILABLE,
    _candidate_cells,
    ensure_hunt_targets,
    restore_provisioning_surfaces,
    snapshot_provisioning_surfaces,
)
from world.maps.monster_sites import (
    SITE_STATE_CLEARED,
    settle_monster_sites,
    settle_site_recovery,
    site_state,
)
from world.maps.wilderness_population import (
    _population_key,
    _stored_hp,
    ensure_population,
)
from world.maps.wilderness_provider import (
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    is_footprint_cell,
    region_for_coordinates,
)
from world.rules.action import register_event_effect_planner
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.planner import quest_event_effect_planner
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    defeat,
    quest,
    register,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import (
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_VARIANTS,
    synthetic_registries,
)

_VARIANTS = tuple(SYNTH_MONSTER_VARIANTS)
ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]
SPECIES = SYNTH_MONSTER_SPECIES[next(iter(SYNTH_MONSTER_SPECIES))].key
assert SYNTH_MONSTER_VARIANTS[ORDINARY].species_key == SPECIES

#: A walkable south-western wild cell, far from the contract-pinned hunting band.
PROBE = (30, 30)

_SITE_KEY = "t_hunt_provisioning_site"
_SITE_RECOVERY_TICKS = 3600


def _first_cell_outside(regions: frozenset[str]) -> tuple[int, int]:
    """A walkable cell whose region is none of ``regions``."""
    for x in range(WILDERNESS_MAX_X + 1):
        for y in range(WILDERNESS_MAX_Y + 1):
            cell = (x, y)
            if is_footprint_cell(cell):
                continue
            if region_for_coordinates(x, y) in regions:
                continue
            return cell
    raise AssertionError("no walkable cell outside the requested regions")


class ProvisioningWorldFixture(BattlefieldIsolation):
    """One live wilderness with the authored placements these tests need.

    A plain mixin (never collected on its own): the tests below pair it with
    ``EvenniaTest``, so ``super().setUp()`` runs the battlefield isolation and
    the standard Evennia fixtures.
    """

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        self.region = region_for_coordinates(*PROBE)
        # The region's authored ambient population: one maintained individual
        # per covered coordinate, up to a hard ceiling of three.
        self.rule = AmbientPlacementRule(self.region, (ORDINARY, STRONGER), 1, 3, 1)
        # A second region whose authored ambient content cannot provide the
        # hunt's ordinary variant at all.
        self.stronger_region = region_for_coordinates(
            *_first_cell_outside(frozenset({self.region}))
        )
        self.rule_stronger = AmbientPlacementRule(
            self.stronger_region, (STRONGER,), 1, 1
        )
        # A third region with no authored ambient placement: its only authored
        # source is one recoverable site.
        self.bare_cell = _first_cell_outside(
            frozenset({self.region, self.stronger_region})
        )
        self.bare_region = region_for_coordinates(*self.bare_cell)
        self.site = MonsterSite(
            _SITE_KEY,
            "camp",
            self.bare_region,
            self.bare_cell,
            (ORDINARY,),
            1,
            False,
            _SITE_RECOVERY_TICKS,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "ambient_placements",
                "monster_sites",
                extra={
                    "ambient_placements": {
                        self.region: self.rule,
                        self.stronger_region: self.rule_stronger,
                    },
                    "monster_sites": {self.site.key: self.site},
                },
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location

    # -- shared fixture helpers --------------------------------------------

    def _occupancy(self) -> dict[int, tuple]:
        """The bookkept individuals' durable surfaces, keyed by dbref."""
        return {
            obj.pk: (
                obj.db.population_key,
                self.wilderness.db.itemcoordinates.get(obj),
                _stored_hp(obj),
                obj.db.site_key,
            )
            for obj in list(self.wilderness.db.itemcoordinates or {})
            if isinstance(obj, Monster)
        }

    def _living_ordinary(self, region_key: str) -> list[Monster]:
        """Living ordinary-eligible individuals the region's bookkeeping holds."""
        return [
            obj
            for obj, coordinates in list(
                (self.wilderness.db.itemcoordinates or {}).items()
            )
            if isinstance(obj, Monster)
            and coordinates is not None
            and region_for_coordinates(*coordinates) == region_key
            and _stored_hp(obj) > 0
            and obj.species_key == SPECIES
            and obj.variant_key == ORDINARY
        ]

    def _spawn_ordinary(
        self,
        cell: tuple[int, int],
        *,
        marker: str | None = None,
        variant_key: str = ORDINARY,
    ) -> Monster:
        individual = construct_species_individual(SPECIES, variant_key)
        individual.db.population_key = marker
        self.wilderness.db.itemcoordinates[individual] = cell
        return individual


class HuntProvisioningTests(ProvisioningWorldFixture, EvenniaTest):
    """The ambient/site owners' ensure API under capacity, ownership, and state."""

    def test_a_region_that_already_holds_enough_creates_nothing(self):
        if not self._living_ordinary(self.region):
            self._spawn_ordinary(PROBE, marker=_population_key(*PROBE))
        before = self._occupancy()
        available = len(self._living_ordinary(self.region))
        self.assertGreaterEqual(available, 1)
        result = ensure_hunt_targets(
            self.region, SPECIES, (ORDINARY,), available, wilderness=self.wilderness
        )
        self.assertTrue(result.satisfied)
        self.assertEqual(result.created, ())
        self.assertEqual(result.available, available)
        self.assertEqual(self._occupancy(), before)

    def test_availability_counts_every_owner_not_only_the_ambient_footprint(self):
        # A site-owned (or otherwise foreign-owned) living ordinary individual is
        # a reachable target: it satisfies the guarantee without the ambient
        # owner creating or touching anything.
        foreign = self._spawn_ordinary(PROBE, marker=None)
        foreign.db.site_key = _SITE_KEY
        foreign.traits.hp._data["current"] = 5
        before = self._occupancy()
        result = ensure_hunt_targets(
            self.region, SPECIES, (ORDINARY,), 1, wilderness=self.wilderness
        )
        self.assertTrue(result.satisfied)
        self.assertEqual(result.created, ())
        self.assertGreaterEqual(result.available, 1)
        self.assertEqual(self._occupancy(), before)
        self.assertEqual(foreign.db.site_key, _SITE_KEY)

    def test_a_shortfall_is_provisioned_through_the_ambient_owner(self):
        before = self._occupancy()
        available = len(self._living_ordinary(self.region))
        needed = self.rule.capacity
        result = ensure_hunt_targets(
            self.region, SPECIES, (ORDINARY,), needed, wilderness=self.wilderness
        )
        self.assertTrue(result.satisfied)
        self.assertEqual(result.available, available)
        self.assertEqual(result.required, needed)
        self.assertEqual(len(result.created), needed - available)
        self.assertEqual(len(self._living_ordinary(self.region)), needed)
        for pk in result.created:
            individual = Monster.objects.filter(pk=pk).first()
            self.assertIsNotNone(individual)
            cell = self.wilderness.db.itemcoordinates[individual]
            self.assertEqual(region_for_coordinates(*cell), self.region)
            self.assertEqual(individual.db.population_key, _population_key(*cell))
            self.assertEqual(individual.species_key, SPECIES)
            self.assertEqual(individual.variant_key, ORDINARY)
            self.assertGreater(_stored_hp(individual), 0)
            self.assertNotIn(pk, before)

    def test_provisioned_individuals_survive_the_ambient_pass(self):
        result = ensure_hunt_targets(
            self.region,
            SPECIES,
            (ORDINARY,),
            self.rule.capacity,
            wilderness=self.wilderness,
        )
        self.assertTrue(result.created)
        cells = {
            self.wilderness.db.itemcoordinates[Monster.objects.get(pk=pk)]
            for pk in result.created
        }
        for cell in cells:
            ensure_population(self.wilderness, cell)
        for pk in result.created:
            individual = Monster.objects.filter(pk=pk).first()
            self.assertIsNotNone(
                individual, "the ambient pass rebuilt a provisioned individual"
            )
            self.assertGreater(_stored_hp(individual), 0)
            self.assertIn(self.wilderness.db.itemcoordinates[individual], cells)

    def test_the_authored_capacity_ceiling_is_honored_per_coordinate(self):
        candidates = _candidate_cells(self.region, self.rule)
        self.assertTrue(candidates)
        saturated, *rest = candidates
        for _ in range(self.rule.capacity):
            self._spawn_ordinary(saturated, marker=_population_key(*saturated))
        before_saturated = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(saturated)
            if isinstance(obj, Monster) and _stored_hp(obj) > 0
        ]
        available = len(self._living_ordinary(self.region))
        result = ensure_hunt_targets(
            self.region,
            SPECIES,
            (ORDINARY,),
            available + 1,
            wilderness=self.wilderness,
        )
        self.assertTrue(result.satisfied)
        self.assertEqual(len(result.created), 1)
        created = Monster.objects.get(pk=result.created[0])
        placed = self.wilderness.db.itemcoordinates[created]
        self.assertIn(placed, rest)
        self.assertNotEqual(placed, saturated)
        after_saturated = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(saturated)
            if isinstance(obj, Monster) and _stored_hp(obj) > 0
        ]
        self.assertEqual(
            sorted(obj.pk for obj in after_saturated),
            sorted(obj.pk for obj in before_saturated),
        )

    def test_a_region_without_an_authored_rule_is_refused_without_state_change(self):
        before = self._occupancy()
        result = ensure_hunt_targets(
            self.bare_region, SPECIES, (ORDINARY,), 1, wilderness=self.wilderness
        )
        self.assertFalse(result.satisfied)
        self.assertEqual(result.reason, PROVISION_NO_AMBIENT_RULE)
        self.assertEqual(result.created, ())
        self.assertEqual(self._living_ordinary(self.bare_region), [])
        self.assertEqual(self._occupancy(), before)

    def test_a_rule_without_the_hunts_ordinary_variant_is_refused(self):
        before = self._occupancy()
        result = ensure_hunt_targets(
            self.stronger_region, SPECIES, (ORDINARY,), 1, wilderness=self.wilderness
        )
        self.assertFalse(result.satisfied)
        self.assertEqual(result.reason, PROVISION_NO_ELIGIBLE_VARIANT)
        self.assertEqual(result.created, ())
        self.assertEqual(self._occupancy(), before)

    def test_an_exhausted_authored_capacity_is_refused(self):
        # A region whose whole authored footprint already sits at its ceiling
        # cannot be topped up: the manager names the reason and creates nothing.
        # The footprint is narrowed to the one cell under test so the assertion
        # is about the ceiling, not about the size of the map.
        for _ in range(self.rule.capacity):
            self._spawn_ordinary(PROBE, marker=_population_key(*PROBE))
        before = self._occupancy()
        with patch(
            "world.maps.monster_provisioning._candidate_cells",
            return_value=(PROBE,),
        ):
            result = ensure_hunt_targets(
                self.region,
                SPECIES,
                (ORDINARY,),
                self.rule.capacity + 1,
                wilderness=self.wilderness,
            )
        self.assertFalse(result.satisfied)
        self.assertEqual(result.reason, PROVISION_CAPACITY_EXHAUSTED)
        self.assertEqual(result.created, ())
        self.assertEqual(result.available, self.rule.capacity)
        self.assertEqual(self._occupancy(), before)

    def test_a_cleared_site_is_never_recovered_by_provisioning(self):
        # The region's only authored source is one recoverable site. Once that
        # site is cleared and its authored in-game condition is not due, the hunt
        # cannot be satisfied: provisioning creates nothing and leaves the site's
        # durable state exactly as the lifecycle owner left it.
        settle_monster_sites(0, 1)
        members = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(self.bare_cell)
            if isinstance(obj, Monster) and obj.db.site_key == self.site.key
        ]
        self.assertTrue(members)
        for member in members:
            member.traits.hp._data["current"] = 0
        settle_monster_sites(1, 2)
        cleared = site_state(self.site.key, wilderness=self.wilderness)
        self.assertEqual(cleared.state, SITE_STATE_CLEARED)
        self.assertEqual(cleared.cleared_at_tick, 2)
        occupancy = self._occupancy()
        result = ensure_hunt_targets(
            self.bare_region, SPECIES, (ORDINARY,), 1, wilderness=self.wilderness
        )
        self.assertFalse(result.satisfied)
        self.assertEqual(result.reason, PROVISION_NO_AMBIENT_RULE)
        self.assertEqual(result.created, ())
        after = site_state(self.site.key, wilderness=self.wilderness)
        self.assertEqual((after.state, after.cleared_at_tick), (SITE_STATE_CLEARED, 2))
        self.assertEqual(self._occupancy(), occupancy)
        self.assertEqual(
            [
                obj
                for obj in self.wilderness.get_objs_at_coordinates(self.bare_cell)
                if isinstance(obj, Monster)
                and obj.db.site_key == self.site.key
                and _stored_hp(obj) > 0
            ],
            [],
        )

    def test_the_provisioning_snapshot_restores_bookkeeping_and_rooms(self):
        snapshot = snapshot_provisioning_surfaces()
        self.assertIsNotNone(snapshot)
        before = self._occupancy()
        created: list[int] = []
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                result = ensure_hunt_targets(
                    self.region,
                    SPECIES,
                    (ORDINARY,),
                    self.rule.capacity,
                    wilderness=self.wilderness,
                )
                created = list(result.created)
                self.assertTrue(created)
                raise RuntimeError("injected acceptance failure")
        self.assertNotEqual(self._occupancy(), before)
        restore_provisioning_surfaces(snapshot)
        self.assertEqual(self._occupancy(), before)
        for pk in created:
            self.assertFalse(Monster.objects.filter(pk=pk).exists())
            # The rolled-back instance is evicted, not served from the cache.
            self.assertIsNone(Monster.objects.filter(pk=pk).first())


class NoWorldProvisioningTests(EvenniaTest):
    """Provisioning before the wilderness exists refuses and snapshots nothing."""

    def test_an_absent_world_refuses_and_snapshots_nothing(self):
        region = region_for_coordinates(*PROBE)
        self.assertIsNone(snapshot_provisioning_surfaces())
        result = ensure_hunt_targets(region, SPECIES, (ORDINARY,), 1)
        self.assertFalse(result.satisfied)
        self.assertEqual(result.reason, PROVISION_WORLD_UNAVAILABLE)
        self.assertEqual(result.created, ())


class OwnerTargetSubstitutionTests(
    ProvisioningWorldFixture, QuestRegistryIsolation, EvenniaTest
):
    """Bound stages count only their own bindings (task 2.1 / lifecycle delta).

    A bound stage's progress counts exactly the record's
    ``objective_target_ids``: a same-species individual elsewhere, an ambient
    respawn, and a recovered site's fresh newcomer never satisfy an old binding,
    while a newly issued quest binds those fresh identities as its own.
    """

    def setUp(self):
        super().setUp()
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.bound_key = register(
            quest(
                "t_bound_substitution",
                stages=(QuestStage(0, defeat(bound=True, quantity=1)),),
            )
        ).key
        self.reissue_key = register(
            quest(
                "t_bound_substitution_reissue",
                stages=(QuestStage(0, defeat(bound=True, quantity=1)),),
            )
        ).key

    def tearDown(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        _EVENT_EFFECT_PLANNERS.pop("quest", None)
        super().tearDown()

    def _defeat_entry(self, actor, individual):
        from world.rules.event_log import EventEntry

        return EventEntry(
            kind="target_defeated",
            actor=str(actor.key),
            target=str(individual.key),
            data={
                "target_id": int(individual.pk),
                "monster_tier": getattr(individual, "threat_tier", None),
                "species_key": individual.species_key,
                "variant_key": individual.variant_key,
            },
            text_template="{actor} 擊敗了 {target}。",
        )

    def _plan(self, entries):
        from types import SimpleNamespace

        from world.rules.event_log import EventLog

        log = EventLog(
            actor=str(self.char1.key),
            skill_key="combat_upkeep",
            targets=tuple(
                entry.target for entry in entries if entry.target is not None
            ),
            entries=tuple(entries),
            time_cost_seconds=0,
        )
        request = SimpleNamespace(
            actor=self.char1, context=SimpleNamespace(battlefield=None)
        )
        return quest_event_effect_planner(request, log)

    def _commit(self, effects) -> None:
        for effect in effects:
            effect.apply()

    @staticmethod
    def _quest_log_writes(effects) -> list[str]:
        return [
            effect.description
            for effect in effects
            if effect.description.startswith("quest_log|")
        ]

    def _progress(self, quest_id: str) -> tuple[str, int]:
        from world.quests.runtime import read_records

        record = next(
            candidate
            for candidate in read_records(self.char1)
            if candidate.quest_id == quest_id
        )
        return record.state.value, record.stage_progress

    def test_a_recovered_site_newcomer_never_credits_an_old_binding(self):
        settle_monster_sites(0, 1)
        members = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(self.bare_cell)
            if isinstance(obj, Monster) and obj.db.site_key == self.site.key
        ]
        self.assertTrue(members)
        old = members[0]
        record = accept(self.char1, self.bound_key)
        bind_stage_runtime(self.char1, record.quest_id, objective_targets=(old,))
        old.traits.hp._data["current"] = 0
        settle_monster_sites(1, 2)
        self.assertTrue(settle_site_recovery(self.site.key, 2 + _SITE_RECOVERY_TICKS))
        newcomers = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(self.bare_cell)
            if isinstance(obj, Monster)
            and obj.db.site_key == self.site.key
            and _stored_hp(obj) > 0
        ]
        self.assertTrue(newcomers)
        newcomer = newcomers[0]
        self.assertNotEqual(newcomer.pk, old.pk)
        # The old hunt does not advance from the newcomers...
        self.assertEqual(
            self._quest_log_writes(self._plan([self._defeat_entry(self.char1, newcomer)])),
            [],
        )
        self.assertEqual(self._progress(record.quest_id), ("in_progress", 0))
        # ...while a freshly issued quest binds them as its own fresh targets.
        fresh = accept(self.char1, self.reissue_key)
        bind_stage_runtime(self.char1, fresh.quest_id, objective_targets=(newcomer,))
        self._commit(self._plan([self._defeat_entry(self.char1, newcomer)]))
        self.assertEqual(self._progress(fresh.quest_id), ("completed", 1))

    def test_a_same_species_individual_elsewhere_never_credits_a_binding(self):
        record = accept(self.char1, self.bound_key)
        bound = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(PROBE)
            if isinstance(obj, Monster) and _stored_hp(obj) > 0
        ]
        self.assertTrue(bound)
        bind_stage_runtime(self.char1, record.quest_id, objective_targets=(bound[0],))
        elsewhere = self._spawn_ordinary(
            self.bare_cell, marker=None, variant_key=bound[0].variant_key
        )
        self.assertEqual(elsewhere.species_key, bound[0].species_key)
        self.assertEqual(elsewhere.variant_key, bound[0].variant_key)
        self.assertNotEqual(elsewhere.pk, bound[0].pk)
        self.assertEqual(
            self._quest_log_writes(
                self._plan([self._defeat_entry(self.char1, elsewhere)])
            ),
            [],
        )
        self.assertEqual(self._progress(record.quest_id), ("in_progress", 0))
        self._commit(self._plan([self._defeat_entry(self.char1, bound[0])]))
        self.assertEqual(self._progress(record.quest_id), ("completed", 1))

    def test_an_ambient_respawn_never_credits_an_old_binding(self):
        record = accept(self.char1, self.bound_key)
        original = next(
            obj
            for obj in self.wilderness.get_objs_at_coordinates(PROBE)
            if isinstance(obj, Monster) and _stored_hp(obj) > 0
        )
        bind_stage_runtime(self.char1, record.quest_id, objective_targets=(original,))
        original.traits.hp._data["current"] = 0
        ensure_population(self.wilderness, PROBE)
        newcomers = [
            obj
            for obj in self.wilderness.get_objs_at_coordinates(PROBE)
            if isinstance(obj, Monster) and _stored_hp(obj) > 0
        ]
        self.assertTrue(newcomers)
        newcomer = newcomers[0]
        self.assertNotEqual(newcomer.pk, original.pk)
        self.assertEqual(
            self._quest_log_writes(self._plan([self._defeat_entry(self.char1, newcomer)])),
            [],
        )
        self.assertEqual(self._progress(record.quest_id), ("in_progress", 0))


if __name__ == "__main__":
    import unittest

    unittest.main()
