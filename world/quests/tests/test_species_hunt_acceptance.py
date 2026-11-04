"""Regional hunt acceptance against sparse authored supply (task 1.1).

Only the species/variant identities and the region's authored ecology zone are
synthetic fixtures; the region keys themselves are read from the live terrain
model at runtime. No shipped placement, species, variant, or region token is
named here.

The contract under test: a published, source-backed hunt accepts with fewer
living targets than its quantity — including none — and acceptance creates no
individual and writes no population state. Publication is where a selector
without a lawful authored source is refused.
"""

from tools.spec_traceability import covers_requirement

import importlib.util
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.components import GuildStaff
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.lore.monster_placement import (
    EcologyZone,
    WeightedComposition,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.definitions import (
    ObjectiveKind,
    QUEST_DEFINITION_REGISTRY,
    QuestDefinitionError,
    QuestObjective,
    QuestStage,
)
from world.quests.runtime import (
    QuestState,
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
from world.rules.tests._guild_service_probes import rank_reward_band
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
_BIG_HUNT_KEY = "t_species_hunt_acceptance_wide"
_UNSOURCED_KEY = "t_species_hunt_unsourced"
_BRANCH = SYNTH_GUILD_BRANCH_KEY

#: The synthetic habitat's per-cell automatic-birth ceiling. The wide hunt's
#: quantity is deliberately larger, so no one cell could ever hold it.
ZONE_CELL_CAPACITY = 3
WIDE_QUANTITY = 10


def _live_region_keys() -> tuple[str, ...]:
    """The live terrain region keys, in registry order (no literal here)."""
    from world.lore.wilderness_regions import regions

    return tuple(regions())


from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    publish_shipped_geography()


class HuntAcceptanceTests(
    QuestRegistryIsolation, EvenniaTest
):
    """Sparse acceptance, publication refusal and the board path."""

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
        )

        # The shipped affinity rulebook validates its cap-break quest key
        # against the live definition registry whenever it (re)loads, so the
        # catalog definitions stay registered (no shipped literal is named).
        from world.quests.catalog import register_catalog

        register_catalog()
        self.region = region_for_coordinates(*PROBE)
        # A live region with no authored source under this scope: the only
        # ecology zone is the synthetic one in ``self.region`` and the shipped
        # sites live in other regions.
        from world.lore.monster_placement import MONSTER_SITE_REGISTRY

        site_regions = {site.region_key for site in MONSTER_SITE_REGISTRY.values()}
        self.bare_region = next(
            key
            for key in _live_region_keys()
            if key != self.region and key not in site_regions
        )
        self.zone = EcologyZone(
            "t_probe_habitat",
            self.region,
            ((PROBE[0] - 1, PROBE[0] + 1, PROBE[1] - 1, PROBE[1] + 1),),
            (WeightedComposition("t_whisper_quail_pair", 1),),
            1,
            3,
            ZONE_CELL_CAPACITY,
            3600,
            600,
            3,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "guild_branches",
                "ecology_zones",
                extra={
                    "ecology_zones": {self.zone.key: self.zone},
                },
            )
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)

        self.hunt_key = register(
            quest(_HUNT_KEY, stages=(QuestStage(0, self._hunt_objective(1)),))
        ).key
        self.wide_hunt_key = register(
            quest(
                _BIG_HUNT_KEY,
                stages=(QuestStage(0, self._hunt_objective(WIDE_QUANTITY)),),
            )
        ).key

        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.staff = create_object(NPC, key="hunt-staff", location=self.char1.location)
        staff_component = GuildStaff.create(
            self.staff, service_id="hunt-staff", branch_key=_BRANCH
        )
        staff_component.service_binding = "place"
        staff_component.anchor_room_id = self.char1.location.pk
        self.staff.components.add(staff_component)

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

    def _population_state(self) -> tuple:
        """Every durable surface acceptance must leave untouched."""
        wilderness = self.wilderness
        return (
            dict(wilderness.db.regional_population or {}),
            wilderness.db.regional_population_seed,
            {
                int(obj.pk): tuple(cell)
                for obj, cell in (wilderness.db.itemcoordinates or {}).items()
            },
            tuple(sorted(Monster.objects.values_list("pk", flat=True))),
            dict(wilderness.db.monster_sites or {}),
        )

    def _storage(self) -> list[dict]:
        return [to_storage(record) for record in read_records(self.char1)]

    def _affinity_value(self) -> int | None:
        relation = self.staff.relations._load(self.char1)
        return None if relation is None else relation.value

    def _register_offer(self, definition_key: str) -> None:
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition_key,
                issuer_branch_key=_BRANCH,
                reward=QuestReward(
                    copper=rank_reward_band("F")[0], items=(), merit=0
                ),
            )
        )

    # -- sparse acceptance --------------------------------------------------

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_an_undersupplied_hunt_accepts_without_creating_a_target(self):
        before = self._population_state()
        record = accept(self.char1, self.hunt_key)
        self.assertEqual(record.quest_id, f"{self.hunt_key}:1")
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.objective_target_ids, ())
        self.assertIsNone(record.deadline_tick)
        self.assertEqual(len(self._storage()), 1)
        self.assertEqual(self._population_state(), before)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_hunt_wider_than_one_cell_accepts_without_generating_members(self):
        self.assertGreater(WIDE_QUANTITY, self.zone.cell_capacity)
        before = self._population_state()
        record = accept(self.char1, self.wide_hunt_key)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        # No cell, site, wave, or one-shot cap limits the published quantity:
        # completion may span encounters and recovery waves.
        self.assertEqual(
            self._storage()[0]["definition_key"], self.wide_hunt_key
        )
        self.assertEqual(self._population_state(), before)

    def test_a_species_with_no_authored_source_is_rejected_at_publication(self):
        before = dict(QUEST_DEFINITION_REGISTRY)
        with self.assertRaises(QuestDefinitionError):
            register(
                quest(
                    _UNSOURCED_KEY,
                    stages=(
                        QuestStage(
                            0,
                            self._hunt_objective(1, region=self.bare_region),
                        ),
                    ),
                )
            )
        self.assertNotIn(_UNSOURCED_KEY, QUEST_DEFINITION_REGISTRY)
        self.assertEqual(dict(QUEST_DEFINITION_REGISTRY), before)

    # -- the board path -----------------------------------------------------

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_board_accepts_an_undersupplied_hunt_without_targets(self):
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.wide_hunt_key)
        affinity_before = self._affinity_value()
        before = self._population_state()
        record = accept_guild_offer(self.char1, self.staff, self.wide_hunt_key)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(self._affinity_value() or 0, (affinity_before or 0) + 1)
        self.assertEqual(len(self._storage()), 1)
        self.assertEqual(self._population_state(), before)

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_board_rolls_back_the_record_when_the_affinity_write_fails(self):
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.wide_hunt_key)
        affinity_before = self._affinity_value()
        before_records = self._storage()
        before = self._population_state()
        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=RuntimeError("injected affinity failure"),
        ):
            with self.assertRaises(RuntimeError):
                accept_guild_offer(self.char1, self.staff, self.wide_hunt_key)
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._population_state(), before)
        self.assertEqual(self._affinity_value(), affinity_before)

    # -- accepted-record atomicity -----------------------------------------

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
        before = self._population_state()

        def _write_then_fail(*args, **kwargs):
            real_write(*args, **kwargs)
            raise RuntimeError("injected failure after the quest-log write")

        with patch(
            "world.quests.runtime.apply_quest_log_replacement",
            side_effect=_write_then_fail,
        ):
            with self.assertRaises(RuntimeError):
                accept(self.char1, self.wide_hunt_key)
        self.assertEqual(self._storage(), before_records)
        self.assertEqual(self._population_state(), before)
        # A follow-up acceptance sees the rolled-back log, not a ghost record.
        later = accept(self.char1, self.hunt_key)
        self.assertEqual(later.quest_id, f"{self.hunt_key}:1")

    # -- removed provisioning ----------------------------------------------

    def test_no_provisioning_module_or_helper_survives(self):
        self.assertIsNone(
            importlib.util.find_spec("world.maps.monster_provisioning")
        )
        from world.quests import runtime

        for helper in (
            "_provision_hunt_targets",
            "provisioning_snapshot_for",
            "restore_provisioning",
            "_stage_zero_hunt",
        ):
            self.assertFalse(hasattr(runtime, helper), helper)


if __name__ == "__main__":
    import unittest

    unittest.main()
