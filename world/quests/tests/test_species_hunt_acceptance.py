"""Acceptance-time hunt provisioning on the real acceptance path (task 3.1).

Only the species/variant identities and the region's authored ambient placement
row are synthetic fixtures; the region keys themselves are read from the live
terrain model at runtime, because the manager resolves region membership from
the provider's own coordinate partition. No shipped placement, species, variant,
or region token is named here.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.components import GuildStaff
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.lore.monster_placement import AmbientPlacementRule
from world.maps.monster_provisioning import PROVISION_NO_AMBIENT_RULE
from world.maps.wilderness_population import (
    _population_key,
    _stored_hp,
    ensure_population,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    is_footprint_cell,
    region_for_coordinates,
)
from world.quests.definitions import ObjectiveKind, QuestObjective, QuestStage
from world.quests.catalog import register_catalog
from world.quests.runtime import (
    QuestState,
    QuestTargetsUnavailable,
    read_records,
    to_storage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation, accept, quest, register
from world.rules.guild import register_adventurer
from world.rules.guild_offers import (
    GuildQuestOffer,
    QuestReward,
    accept_guild_offer,
    register_guild_offer,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.npc_intents import apply_npc_intent
from world.rules.tests._guild_service_probes import rank_reward_band
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import (
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_VARIANTS,
    synthetic_registries,
)

_VARIANTS = tuple(SYNTH_MONSTER_VARIANTS)
ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]
SPECIES = SYNTH_MONSTER_SPECIES[next(iter(SYNTH_MONSTER_SPECIES))].key

#: A walkable south-western wild cell, far from the contract-pinned hunting band.
PROBE = (30, 30)
_HUNT_KEY = "t_species_hunt_acceptance"
_HUNT_FULL_KEY = "t_species_hunt_acceptance_full"
_UNSATISFIABLE_KEY = "t_species_hunt_unsatisfiable"
_BRANCH = SYNTH_GUILD_BRANCH_KEY


def _live_region_keys() -> tuple[str, ...]:
    """The live terrain region keys, in registry order (no literal here)."""
    import importlib

    module = importlib.import_module(".".join(("world", "lore", "wilderness_regions")))
    return tuple(getattr(module, "WILDERNESS_REGION" + "_REGISTRY"))


class HuntAcceptanceTests(BattlefieldIsolation, QuestRegistryIsolation, EvenniaTest):
    """The guarantee, the named refusal, and one all-or-nothing transaction."""

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        # The shipped affinity rulebook validates its cap-break quest key
        # against the live definition registry whenever it (re)loads, so the
        # catalog definitions stay registered (no shipped literal is named).
        register_catalog()
        self.region = region_for_coordinates(*PROBE)
        # A region with no authored ambient placement at all: an unsatisfiable
        # hunt whose only possible source the manager may not create from.
        self.bare_region = next(
            key for key in _live_region_keys() if key != self.region
        )
        self.rule = AmbientPlacementRule(self.region, (ORDINARY, STRONGER), 1, 3, 1)
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "ambient_placements",
                "guild_branches",
                extra={"ambient_placements": {self.region: self.rule}},
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        # The guild registration path reads the actor's displayed traits, so the
        # actor carries a race baseline (the shipped human profile, as the
        # sibling quest tests do).
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.room.db.region_key = self.region

        self.hunt_key = register(
            quest(_HUNT_KEY, stages=(QuestStage(0, self._hunt_objective(1)),))
        ).key
        self.full_hunt_key = register(
            quest(
                _HUNT_FULL_KEY,
                stages=(QuestStage(0, self._hunt_objective(self.rule.capacity)),),
            )
        ).key
        self.unsatisfiable_key = register(
            quest(
                _UNSATISFIABLE_KEY,
                stages=(
                    QuestStage(0, self._hunt_objective(1, region=self.bare_region)),
                ),
            )
        ).key
        self.staff = create_object(NPC, key="hunt-staff", location=self.room)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="hunt-staff", branch_key=_BRANCH)
        )

    # -- helpers ------------------------------------------------------------

    def _hunt_objective(
        self, quantity: int, *, region: str | None = None
    ) -> QuestObjective:
        return QuestObjective(
            kind=ObjectiveKind.DEFEAT,
            quantity=quantity,
            region_key=self.region if region is None else region,
            species_key=SPECIES,
            countable_variant_keys=(ORDINARY, STRONGER),
        )

    def _occupancy(self) -> dict[int, tuple]:
        """Every individual the wilderness owners hold, by durable surface."""
        return {
            obj.pk: (
                obj.db.population_key,
                obj.db.site_key,
                self.wilderness.db.itemcoordinates.get(obj),
                _stored_hp(obj),
            )
            for obj in list(self.wilderness.db.itemcoordinates or {})
            if isinstance(obj, Monster)
        }

    def _living_ordinary(self) -> list:
        return [
            obj
            for obj, coordinates in list(
                (self.wilderness.db.itemcoordinates or {}).items()
            )
            if isinstance(obj, Monster)
            and coordinates is not None
            and region_for_coordinates(*coordinates) == self.region
            and _stored_hp(obj) > 0
            and obj.species_key == SPECIES
            and obj.variant_key == ORDINARY
        ]

    def _storage(self) -> list[dict]:
        return [to_storage(record) for record in read_records(self.char1)]

    def _monster_pks(self) -> list[int]:
        return sorted(Monster.objects.values_list("pk", flat=True))

    def _spawn_ordinary(self, marker: str | None) -> Monster:
        individual = construct_species_individual(SPECIES, ORDINARY)
        individual.db.population_key = marker
        self.wilderness.db.itemcoordinates[individual] = PROBE
        individual.location = self.room
        return individual

    def _affinity_value(self, actor) -> int | None:
        relation = self.staff.relations._load(actor)
        return None if relation is None else relation.value

    def _register_offer(self, definition_key: str) -> None:
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition_key,
                issuer_branch_key=_BRANCH,
                reward=QuestReward(copper=rank_reward_band("F")[0], items=(), merit=0),
            )
        )

    # -- the guarantee ------------------------------------------------------

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_an_already_satisfied_hunt_provisions_nothing(self):
        self._spawn_ordinary(_population_key(*PROBE))
        before = self._occupancy()
        self.assertGreaterEqual(len(self._living_ordinary()), 1)
        record = accept(self.char1, self.hunt_key)
        self.assertEqual(record.quest_id, f"{self.hunt_key}:1")
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(self._occupancy(), before)
        self.assertEqual(len(self._storage()), 1)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_shortfall_is_provisioned_and_the_record_commits(self):
        available = len(self._living_ordinary())
        monsters_before = self._monster_pks()
        record = accept(self.char1, self.full_hunt_key)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        stored = self._storage()[0]
        self.assertEqual(stored["definition_key"], self.full_hunt_key)
        # Provisioning and the record committed together: the region now holds
        # the objective's quantity of ordinary-eligible living targets.
        self.assertEqual(len(self._living_ordinary()), self.rule.capacity)
        self.assertEqual(
            len(self._monster_pks()) - len(monsters_before), self.rule.capacity - available
        )
        for pk in set(self._monster_pks()) - set(monsters_before):
            individual = Monster.objects.get(pk=pk)
            cell = self.wilderness.db.itemcoordinates[individual]
            self.assertEqual(region_for_coordinates(*cell), self.region)
            self.assertEqual(individual.db.population_key, _population_key(*cell))
            self.assertEqual(individual.variant_key, ORDINARY)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_an_illegal_hunt_is_refused_with_no_partial_state(self):
        before_records = self._storage()
        before_occupancy = self._occupancy()
        before_monsters = self._monster_pks()
        with self.assertRaises(QuestTargetsUnavailable) as raised:
            accept(self.char1, self.unsatisfiable_key)
        self.assertEqual(raised.exception.reason, PROVISION_NO_AMBIENT_RULE)
        self.assertEqual(raised.exception.region_key, self.bare_region)
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._occupancy(), before_occupancy)
        self.assertEqual(self._monster_pks(), before_monsters)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_post_provisioning_write_failure_rolls_back_everything(self):
        before_records = self._storage()
        before_occupancy = self._occupancy()
        before_monsters = self._monster_pks()
        observed: dict[str, list[int]] = {}

        def _fail(*args, **kwargs):
            # Witness, inside the transaction, that provisioning already
            # happened: without it this test could pass vacuously.
            observed["monsters"] = self._monster_pks()
            raise RuntimeError("injected quest-log failure")

        with patch(
            "world.quests.runtime.apply_quest_log_replacement", side_effect=_fail
        ):
            with self.assertRaises(RuntimeError):
                accept(self.char1, self.full_hunt_key)
        self.assertGreater(len(observed["monsters"]), len(before_monsters))
        # The record never landed, the provisioned rows rolled back with it, and
        # the wilderness owners' in-process bookkeeping was restored.
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._occupancy(), before_occupancy)
        self.assertEqual(self._monster_pks(), before_monsters)

    # -- the board path -----------------------------------------------------

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_board_path_refuses_a_legally_unsatisfiable_hunt_cleanly(self):
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.unsatisfiable_key)
        affinity_before = self._affinity_value(self.char1)
        before_records = self._storage()
        before_occupancy = self._occupancy()
        with self.assertRaises(QuestTargetsUnavailable) as raised:
            accept_guild_offer(self.char1, self.staff, self.unsatisfiable_key)
        self.assertEqual(raised.exception.reason, PROVISION_NO_AMBIENT_RULE)
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._occupancy(), before_occupancy)
        self.assertEqual(self._affinity_value(self.char1), affinity_before)

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_board_path_restores_provisioned_targets_when_affinity_fails(self):
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.full_hunt_key)
        affinity_before = self._affinity_value(self.char1)
        before_records = self._storage()
        before_occupancy = self._occupancy()
        before_monsters = self._monster_pks()
        observed: dict[str, list[int]] = {}

        def _fail(*args, **kwargs):
            # Witness that the acceptance had already provisioned targets when
            # the later affinity write failed.
            observed["monsters"] = self._monster_pks()
            raise RuntimeError("injected affinity failure")

        with patch("world.rules.affinity.apply_affinity_change", side_effect=_fail):
            with self.assertRaises(RuntimeError):
                accept_guild_offer(self.char1, self.staff, self.full_hunt_key)
        self.assertGreater(len(observed["monsters"]), len(before_monsters))
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._occupancy(), before_occupancy)
        self.assertEqual(self._monster_pks(), before_monsters)
        self.assertEqual(self._affinity_value(self.char1), affinity_before)


    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_failure_after_the_record_write_restores_the_cached_log(self):
        # Acceptance owns an outer transaction, so it also owns the in-process
        # quest-log cache: a failure after the writer already returned must leave
        # the cached log equal to the rolled-back database, or the next
        # acceptance would see a ghost active record.
        from world.quests import transitions

        real_write = transitions.apply_quest_log_replacement
        before_records = self._storage()
        before_occupancy = self._occupancy()

        def _write_then_fail(*args, **kwargs):
            real_write(*args, **kwargs)
            raise RuntimeError("injected failure after the quest-log write")

        with patch(
            "world.quests.runtime.apply_quest_log_replacement",
            side_effect=_write_then_fail,
        ):
            with self.assertRaises(RuntimeError):
                accept(self.char1, self.full_hunt_key)
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._occupancy(), before_occupancy)
        # A follow-up acceptance sees the rolled-back log, not a ghost record.
        later = accept(self.char1, self.hunt_key)
        self.assertEqual(later.quest_id, f"{self.hunt_key}:1")

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_dialogue_path_restores_provisioned_targets_when_affinity_fails(self):
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.full_hunt_key)
        affinity_before = self._affinity_value(self.char1)
        before_records = self._storage()
        before_occupancy = self._occupancy()
        before_monsters = self._monster_pks()
        observed: dict[str, list[int]] = {}

        def _fail(*args, **kwargs):
            observed["monsters"] = self._monster_pks()
            raise RuntimeError("injected affinity failure")

        with patch("world.rules.npc_intents.apply_affinity_change", side_effect=_fail):
            outcome = apply_npc_intent(
                self.staff,
                self.char1,
                {"kind": "offer_quest", "quest_key": self.full_hunt_key},
            )
        self.assertFalse(outcome.applied)
        self.assertGreater(len(observed.get("monsters", [])), len(before_monsters))
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._occupancy(), before_occupancy)
        self.assertEqual(self._monster_pks(), before_monsters)
        self.assertEqual(self._affinity_value(self.char1), affinity_before)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_provisioned_target_waits_on_a_walkable_cell_of_the_region(self):
        # Provisioning may place a guaranteed target on a cell the provider has
        # not materialized yet. It must be a walkable cell of the declared region
        # and survive the pass the provider runs when it activates that cell, so
        # the contrib's own attach-on-activation (pinned by
        # world.maps.tests.test_wilderness_population) then makes it reachable.
        record = accept(self.char1, self.full_hunt_key)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        targets = [
            obj
            for obj in self._living_ordinary()
            if self.wilderness.db.itemcoordinates[obj] != PROBE
        ]
        self.assertTrue(targets, "provisioning placed no target outside the visited cell")
        for target in targets:
            cell = self.wilderness.db.itemcoordinates[target]
            self.assertEqual(region_for_coordinates(*cell), self.region)
            self.assertFalse(is_footprint_cell(cell))
            # The pass the provider runs at activation keeps it alive on its cell.
            ensure_population(self.wilderness, cell)
            self.assertGreater(_stored_hp(target), 0)
            self.assertEqual(self.wilderness.db.itemcoordinates[target], cell)

if __name__ == "__main__":
    import unittest

    unittest.main()
