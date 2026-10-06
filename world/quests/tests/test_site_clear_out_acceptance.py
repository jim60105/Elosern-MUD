"""Acceptance-time binding of an authored site's own individuals (tasks 3.x/4.x).

The site and species identities, the region's ambient placement row, and the
guild branch are synthetic fixtures; the region keys themselves are read from the
live terrain model at runtime, because the site owner resolves membership from the
provider's own coordinate partition. No shipped placement, species, variant,
region, item, or branch token is named here.

The requirement ids this change *adds* are change-local until the archive syncs
the delta specs into ``openspec/specs/``, so they are deliberately not annotated
here; the archive worker attaches them once the ids exist in the index. Every
``covers_requirement`` below names a requirement the delta *modifies*, which the
index already carries.
"""

from types import MappingProxyType
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.components import GuildStaff
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.lore.monster_placement import AmbientPlacementRule, MonsterSite
from world.maps import monster_sites
from world.maps.monster_sites import (
    SITE_READ_CLEARED,
    SITE_READ_UNKNOWN_SITE,
    SITE_READ_UNPOPULATED,
    SITE_READ_WORLD_UNAVAILABLE,
    SITE_STATE_CLEARED,
    SITE_STATE_POPULATED,
    site_state,
)
from world.maps.wilderness_population import _stored_hp
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.catalog import register_catalog
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
)
from world.quests.runtime import (
    SITE_CLEAR_OUT_SHORT,
    QuestTargetsUnavailable,
    abandon_quest,
    read_records,
    site_clear_out_available,
    site_clear_out_refusal,
    to_storage,
)
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    quest,
    register,
)
from world.rules.clock import AdvanceSource
from world.rules.guild import register_adventurer
from world.rules.guild_config import load_catalog_into_cache
from world.rules.guild_offers import (
    GuildQuestOffer,
    QuestReward,
    accept_guild_offer,
    list_guild_offers,
    register_guild_offer,
)
from world.rules.npc_intents import apply_npc_intent
from world.rules.service_view import build_services_view
from world.rules.tests._guild_service_probes import rank_reward_band
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import (
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    synthetic_registries,
)

_VARIANTS = tuple(SYNTH_MONSTER_VARIANTS)
ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]
SPECIES = SYNTH_MONSTER_SPECIES[next(iter(SYNTH_MONSTER_SPECIES))].key

#: A walkable south-western wild cell, far from the contract-pinned hunting band.
PROBE = (30, 30)
HOUR = 3600
_BRANCH = SYNTH_GUILD_BRANCH_KEY

NEST = "t_clear_out_nest"
CAMP = "t_clear_out_camp"
BOSS = "t_clear_out_boss"


class SiteClearOutAcceptanceTests(
    BattlefieldIsolation, QuestRegistryIsolation, EvenniaTest
):
    """The named guarantee, the stage-zero binding, and the board's rule."""

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )
        from world.rules import clock as clock_module
        from world.rules.clock import get_world_clock

        # The shipped affinity rulebook validates its cap-break quest key
        # against the live definition registry whenever it (re)loads, so the
        # catalog definitions stay registered (no shipped literal is named).
        register_catalog()
        # The shipped guild catalog is loaded against the live registries before
        # the synthetic scope narrows the branch registry, so the services panel
        # can be built inside the scope (it reads the cached catalog).
        load_catalog_into_cache()
        self.region = region_for_coordinates(*PROBE)
        self.rule = AmbientPlacementRule(self.region, (ORDINARY,), 1, 1, 0)
        self.sites = {
            NEST: MonsterSite(
                NEST, "nest", self.region, PROBE, (ORDINARY, STRONGER), 2, True
            ),
            CAMP: MonsterSite(
                CAMP, "camp", self.region, PROBE, (ORDINARY, STRONGER), 2, False, HOUR
            ),
            BOSS: MonsterSite(
                BOSS, "boss_site", self.region, PROBE, (STRONGER,), 1, True
            ),
        }
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "ambient_placements",
                "monster_sites",
                "guild_branches",
                extra={
                    "ambient_placements": {self.region: self.rule},
                    "monster_sites": self.sites,
                },
            )
        )
        monster_sites.register_monster_site_lifecycle()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, monster_sites.SITE_STAGE_KIND, None)

        self.char1.race = "human"
        self.char1.apply_race_baseline()
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.room.db.region_key = self.region
        self.clock = get_world_clock()

        self.nest_key = self._register_clear_out("nest", NEST, 2)
        self.camp_key = self._register_clear_out("camp", CAMP, 2)
        self.boss_key = self._register_clear_out("boss", BOSS, 1)
        # A non-clear-out offer beside the clear-outs: a tier-selected defeat
        # stage, never availability-filtered.
        self.plain_key = register(
            quest(
                "t_clear_out_plain_offer",
                rank="F",
                stages=(
                    QuestStage(
                        0,
                        QuestObjective(
                            kind=ObjectiveKind.DEFEAT,
                            quantity=1,
                            monster_tier=next(iter(SYNTH_MONSTER_TIERS)),
                        ),
                    ),
                ),
            )
        ).key
        self.staff = create_object(NPC, key="clear-out-staff", location=self.room)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="clear-out-staff", branch_key=_BRANCH)
        )

    # -- helpers ------------------------------------------------------------

    def _register_clear_out(self, suffix: str, site_key: str, quantity: int) -> str:
        return register(
            quest(
                f"t_clear_out_{suffix}",
                rank="F",
                stages=(
                    QuestStage(
                        0,
                        QuestObjective(
                            kind=ObjectiveKind.DEFEAT,
                            quantity=quantity,
                            requires_bound_targets=True,
                            site_key=site_key,
                        ),
                    ),
                ),
            )
        ).key

    def _settle(self, end_tick: int = 0) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            monster_sites.settle_monster_sites(0, end_tick)

    def _living(self, site_key: str) -> list[Monster]:
        site = self.sites[site_key]
        return [
            member
            for member in monster_sites._members(self.wilderness, site)
            if _stored_hp(member) > 0
        ]

    def _defeat(self, site_key: str) -> tuple[int, ...]:
        defeated = []
        for member in monster_sites._members(self.wilderness, self.sites[site_key]):
            member.traits.hp.current = 0
            defeated.append(member.pk)
        return tuple(defeated)

    def _clear(self, site_key: str) -> None:
        """Defeat a site and let the world clock's settlement declare it cleared."""
        self._defeat(site_key)
        self.clock.advance(60, AdvanceSource.SKIP, [])

    def _storage(self) -> list[dict]:
        return [to_storage(record) for record in read_records(self.char1)]

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

    def _monster_pks(self) -> list[int]:
        return sorted(Monster.objects.values_list("pk", flat=True))

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

    def _definition(self, definition_key: str) -> QuestDefinition:
        return QUEST_DEFINITION_REGISTRY[definition_key]

    # -- the guarantee and the stage-zero binding ---------------------------

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_standing_site_binds_exactly_its_living_set_and_creates_nothing(self):
        self._settle()
        living = {member.pk for member in self._living(NEST)}
        self.assertEqual(len(living), 2)
        monsters_before = self._monster_pks()
        occupancy_before = self._occupancy()

        record = accept(self.char1, self.nest_key)

        self.assertEqual(record.quest_id, f"{self.nest_key}:1")
        self.assertEqual(set(record.objective_target_ids), living)
        # No instance pin: a site is a permanent wilderness location.
        self.assertIsNone(record.stage_room_id)
        self.assertEqual(self._monster_pks(), monsters_before)
        self.assertEqual(self._occupancy(), occupancy_before)
        # The site's own individuals are unchanged in number, and the binding
        # is the site's living set exactly.
        self.assertEqual({member.pk for member in self._living(NEST)}, living)
        self.assertEqual(len(self._living(NEST)), self.sites[NEST].capacity)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_the_returned_record_is_the_persisted_bound_record(self):
        # The binder performs the acceptance's second full quest-log write, so a
        # caller that returned the value written a moment earlier would hand out
        # an empty target set.
        self._settle()
        living = {member.pk for member in self._living(NEST)}

        record = accept(self.char1, self.nest_key)

        self.assertTrue(record.objective_target_ids)
        self.assertEqual(set(record.objective_target_ids), living)
        stored = self._storage()[0]
        self.assertEqual(
            list(record.objective_target_ids), stored["objective_target_ids"]
        )
        self.assertEqual(stored["stage_room_id"], None)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_cleared_one_shot_site_refuses_permanently(self):
        self._settle()
        self._clear(NEST)
        state_before = dict(self.wilderness.db.monster_sites)
        occupancy_before = self._occupancy()
        records_before = self._storage()
        monsters_before = self._monster_pks()

        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.nest_key)

        self.assertEqual(caught.exception.reason, SITE_READ_CLEARED)
        self.assertEqual(caught.exception.region_key, NEST)
        self.assertEqual(self._storage(), records_before)
        self.assertEqual(dict(self.wilderness.db.monster_sites), state_before)
        self.assertEqual(self._occupancy(), occupancy_before)
        self.assertEqual(self._monster_pks(), monsters_before)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_cleared_recoverable_site_refuses_until_the_clock_recovers_it(self):
        self._settle()
        defeated = self._defeat(CAMP)
        self.clock.advance(60, AdvanceSource.SKIP, [])
        self.assertEqual(
            site_state(CAMP, wilderness=self.wilderness).state, SITE_STATE_CLEARED
        )
        monsters_before = self._monster_pks()

        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.camp_key)

        self.assertEqual(caught.exception.reason, SITE_READ_CLEARED)
        # Nothing was early-recovered and nothing was created.
        self.assertEqual(self._monster_pks(), monsters_before)
        self.assertEqual(
            site_state(CAMP, wilderness=self.wilderness).state, SITE_STATE_CLEARED
        )

        self.clock.advance(HOUR, AdvanceSource.SKIP, [])
        fresh = {member.pk for member in self._living(CAMP)}
        self.assertEqual(
            site_state(CAMP, wilderness=self.wilderness).state, SITE_STATE_POPULATED
        )
        self.assertFalse(fresh & set(defeated))

        record = accept(self.char1, self.camp_key)

        self.assertEqual(set(record.objective_target_ids), fresh)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_never_populated_site_refuses_and_stays_unpopulated(self):
        self.assertIsNone(site_state(NEST, wilderness=self.wilderness))
        monsters_before = self._monster_pks()

        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.nest_key)

        self.assertEqual(caught.exception.reason, SITE_READ_UNPOPULATED)
        self.assertIsNone(site_state(NEST, wilderness=self.wilderness))
        self.assertEqual(self._monster_pks(), monsters_before)
        self.assertEqual(self._living(NEST), [])

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_site_holding_fewer_living_individuals_refuses_as_short(self):
        self._settle()
        members = monster_sites._members(self.wilderness, self.sites[CAMP])
        members[0].traits.hp.current = 0
        occupancy_before = self._occupancy()
        records_before = self._storage()

        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.camp_key)

        self.assertEqual(caught.exception.reason, SITE_CLEAR_OUT_SHORT)
        self.assertEqual(self._storage(), records_before)
        self.assertEqual(self._occupancy(), occupancy_before)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_failure_after_the_record_write_leaves_no_record_and_no_binding(self):
        from world.quests import transitions

        self._settle()
        real_write = transitions.apply_quest_log_replacement
        records_before = self._storage()
        occupancy_before = self._occupancy()
        monsters_before = self._monster_pks()
        observed: dict[str, list[str]] = {}

        def _fail_after_the_record_write(*args, **kwargs):
            # Witness, inside the transaction, that the record already landed:
            # without this the test could pass vacuously.
            observed["records"] = [record.quest_id for record in read_records(self.char1)]
            raise RuntimeError("injected binder write failure")

        with patch(
            "world.quests.binding.apply_quest_log_replacement",
            side_effect=_fail_after_the_record_write,
        ):
            with self.assertRaises(RuntimeError):
                accept(self.char1, self.nest_key)

        self.assertEqual(observed["records"], [f"{self.nest_key}:1"])
        self.assertEqual(self._storage(), records_before)
        self.assertEqual(self._occupancy(), occupancy_before)
        self.assertEqual(self._monster_pks(), monsters_before)
        # The cached log is restored too, so a later acceptance sees no ghost.
        later = accept(self.char1, self.nest_key)
        self.assertEqual(later.quest_id, f"{self.nest_key}:1")
        self.assertTrue(later.objective_target_ids)

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_recovered_sites_newcomers_satisfy_only_a_later_clear_out(self):
        self._settle()
        first = accept(self.char1, self.camp_key)
        old_binding = set(first.objective_target_ids)
        self.assertTrue(old_binding)
        self._clear(CAMP)
        # While the commission is still active its bound set is its own: the
        # clearing did not add the recovered newcomers to it.
        active = next(
            record
            for record in read_records(self.char1)
            if record.quest_id == first.quest_id
        )
        self.assertEqual(set(active.objective_target_ids), old_binding)
        self.clock.advance(HOUR, AdvanceSource.SKIP, [])
        newcomers = {member.pk for member in self._living(CAMP)}
        self.assertTrue(newcomers and not newcomers & old_binding)
        still = next(
            record
            for record in read_records(self.char1)
            if record.quest_id == first.quest_id
        )
        self.assertEqual(set(still.objective_target_ids), old_binding)

        # Only a clear-out issued after the recovery binds the newcomers.
        abandon_quest(self.char1, first.quest_id)
        second = accept(self.char1, self.camp_key)

        self.assertEqual(set(second.objective_target_ids), newcomers)

    # -- the shared predicate ----------------------------------------------

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_the_predicate_and_the_refusal_agree_for_every_reason(self):
        definition = self._definition(self.nest_key)
        boss_definition = self._definition(self.boss_key)

        # (a) no world provisioned
        with patch("world.maps.monster_sites._wilderness", return_value=None):
            self.assertFalse(site_clear_out_available(definition))
            self.assertEqual(site_clear_out_refusal(definition), SITE_READ_WORLD_UNAVAILABLE)
            with self.assertRaises(QuestTargetsUnavailable) as caught:
                accept(self.char1, self.nest_key)
            self.assertEqual(caught.exception.reason, SITE_READ_WORLD_UNAVAILABLE)

        # (b) a site key the registry no longer knows (a definition registered
        # while the site existed, then the site removed behind it)
        with patch.object(
            monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({})
        ):
            self.assertFalse(site_clear_out_available(definition))
            self.assertEqual(site_clear_out_refusal(definition), SITE_READ_UNKNOWN_SITE)
            with self.assertRaises(QuestTargetsUnavailable) as caught:
                accept(self.char1, self.nest_key)
            self.assertEqual(caught.exception.reason, SITE_READ_UNKNOWN_SITE)

        # (c) never populated (no settlement has run yet)
        self.assertFalse(site_clear_out_available(boss_definition))
        self.assertEqual(site_clear_out_refusal(boss_definition), SITE_READ_UNPOPULATED)
        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.boss_key)
        self.assertEqual(caught.exception.reason, SITE_READ_UNPOPULATED)

        self._settle()

        # (d) a standing site, but fewer living individuals than the quantity
        monster_sites._members(self.wilderness, self.sites[NEST])[0].traits.hp.current = 0
        self.assertFalse(site_clear_out_available(definition))
        self.assertEqual(site_clear_out_refusal(definition), SITE_CLEAR_OUT_SHORT)
        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.nest_key)
        self.assertEqual(caught.exception.reason, SITE_CLEAR_OUT_SHORT)

        # (e) a cleared site
        self._clear(NEST)
        self.assertFalse(site_clear_out_available(definition))
        self.assertEqual(site_clear_out_refusal(definition), SITE_READ_CLEARED)
        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.nest_key)
        self.assertEqual(caught.exception.reason, SITE_READ_CLEARED)

        # (f) the positive case: a standing site answers yes and is accepted.
        self.assertTrue(site_clear_out_available(boss_definition))
        self.assertIsNone(site_clear_out_refusal(boss_definition))
        record = accept(self.char1, self.boss_key)
        self.assertEqual(
            set(record.objective_target_ids),
            {member.pk for member in self._living(BOSS)},
        )

    @covers_requirement(
        "quest-lifecycle::accept-quest-creates-one-deterministic-active-record"
    )
    def test_a_definition_that_is_not_a_clear_out_is_always_available(self):
        self.assertTrue(site_clear_out_available(self._definition(self.plain_key)))
        self.assertIsNone(site_clear_out_refusal(self._definition(self.plain_key)))

    # -- the board's availability rule -------------------------------------

    @covers_requirement(
        "guild-quest-board::guild-boards-expose-only-local-rank-eligible-offers"
    )
    def test_a_cleared_one_shot_sites_clear_out_leaves_the_board(self):
        self._settle()
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.nest_key)
        self._register_offer(self.plain_key)
        listed = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]
        self.assertIn(self.nest_key, listed)

        self._clear(NEST)

        after = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]
        self.assertNotIn(self.nest_key, after)
        # No other offer's eligibility or order changed.
        self.assertEqual(
            [key for key in after if key != self.nest_key],
            [key for key in listed if key != self.nest_key],
        )
        self.assertIn(self.plain_key, after)

    @covers_requirement(
        "guild-quest-board::guild-boards-expose-only-local-rank-eligible-offers"
    )
    def test_an_unpopulated_sites_clear_out_is_absent_until_the_world_settles_it(self):
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.nest_key)
        self._register_offer(self.plain_key)
        monsters_before = self._monster_pks()

        listed = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]

        self.assertNotIn(self.nest_key, listed)
        self.assertIn(self.plain_key, listed)
        # Listing creates no individual for the site.
        self.assertEqual(self._monster_pks(), monsters_before)
        self.assertIsNone(site_state(NEST, wilderness=self.wilderness))

        self._settle()

        self.assertIn(
            self.nest_key,
            [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)],
        )

    @covers_requirement(
        "guild-quest-board::guild-boards-expose-only-local-rank-eligible-offers"
    )
    def test_a_recovered_sites_clear_out_returns_to_the_board(self):
        self._settle()
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.camp_key)

        self.assertIn(
            self.camp_key,
            [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)],
        )

        self._clear(CAMP)

        self.assertNotIn(
            self.camp_key,
            [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)],
        )

        self.clock.advance(HOUR, AdvanceSource.SKIP, [])

        self.assertIn(
            self.camp_key,
            [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)],
        )

    @covers_requirement(
        "guild-quest-board::guild-boards-expose-only-local-rank-eligible-offers"
    )
    def test_availability_never_reorders_the_board_or_changes_the_summaries(self):
        self._settle()
        register_adventurer(self.char1, self.staff)
        for key in (self.nest_key, self.plain_key):
            self._register_offer(key)

        listed = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]
        summary_rows = [
            row.definition_key for row in build_services_view(self.char1).guild.board
        ]

        self.assertTrue(listed)
        self.assertEqual(summary_rows, listed)
        self._clear(NEST)
        listed_after = [
            offer.definition_key for offer in list_guild_offers(self.char1, self.staff)
        ]
        self.assertEqual(
            [row.definition_key for row in build_services_view(self.char1).guild.board],
            listed_after,
        )
        self.assertEqual(
            [key for key in listed_after if key != self.nest_key],
            [key for key in listed if key != self.nest_key],
        )

    # -- the board's acceptance path ---------------------------------------

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_a_board_listed_clear_out_is_accepted_without_a_supply_refusal(self):
        self._settle()
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.nest_key)
        living = {member.pk for member in self._living(NEST)}
        affinity_before = self._affinity_value(self.char1)

        listed = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]
        self.assertIn(self.nest_key, listed)

        record = accept_guild_offer(self.char1, self.staff, self.nest_key)

        self.assertEqual(set(record.objective_target_ids), living)
        self.assertEqual(self._affinity_value(self.char1), affinity_before + 1)

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_a_state_change_between_listing_and_acceptance_is_reported_by_name(self):
        self._settle()
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.nest_key)
        # The member takes the listing before the site changes state.
        listed = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]
        self.assertIn(self.nest_key, listed)

        self._clear(NEST)

        records_before = self._storage()
        occupancy_before = self._occupancy()
        affinity_before = self._affinity_value(self.char1)
        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept_guild_offer(self.char1, self.staff, self.nest_key)

        # The lifecycle's named refusal reaches the member: the board precheck
        # never presents the now-unsatisfiable offer as ineligible.
        self.assertEqual(caught.exception.reason, SITE_READ_CLEARED)
        self.assertEqual(self._storage(), records_before)
        self.assertEqual(self._occupancy(), occupancy_before)
        self.assertEqual(self._affinity_value(self.char1), affinity_before)

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_board_path_restores_the_binding_when_affinity_fails(self):
        self._settle()
        register_adventurer(self.char1, self.staff)
        self._register_offer(self.nest_key)
        records_before = self._storage()
        occupancy_before = self._occupancy()
        affinity_before = self._affinity_value(self.char1)

        with patch(
            "world.rules.affinity.apply_affinity_change",
            side_effect=RuntimeError("injected affinity failure"),
        ):
            with self.assertRaises(RuntimeError):
                accept_guild_offer(self.char1, self.staff, self.nest_key)

        self.assertEqual(self._storage(), records_before)
        self.assertEqual(self._occupancy(), occupancy_before)
        self.assertEqual(self._affinity_value(self.char1), affinity_before)

    @covers_requirement(
        "guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle"
    )
    def test_the_dialogue_path_reaches_the_runtime_for_an_unavailable_clear_out(self):
        # An assignment attempt is an acceptance attempt: the availability rule
        # narrows the listing only, so a cleared site's clear-out must reach the
        # lifecycle's refusal rather than being reported as ineligible.
        self._settle()
        register_adventurer(self.char1, self.staff)
        for key in (self.nest_key, self.boss_key):
            self._register_offer(key)
        self._clear(NEST)
        records_before = self._storage()

        outcome = apply_npc_intent(
            self.staff, self.char1, {"kind": "offer_quest", "quest_key": self.nest_key}
        )

        self.assertFalse(outcome.applied)
        self.assertNotIn("not rank-eligible", outcome.reason)
        self.assertEqual(self._storage(), records_before)

        # The positive control: a standing site's clear-out is assigned and
        # carries its bound set.
        boss_living = {member.pk for member in self._living(BOSS)}
        assigned = apply_npc_intent(
            self.staff, self.char1, {"kind": "offer_quest", "quest_key": self.boss_key}
        )

        self.assertTrue(assigned.applied)
        record = read_records(self.char1)[-1]
        self.assertEqual(record.definition_key, self.boss_key)
        self.assertEqual(set(record.objective_target_ids), boss_living)


if __name__ == "__main__":
    import unittest

    unittest.main()
