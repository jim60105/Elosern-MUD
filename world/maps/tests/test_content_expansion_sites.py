"""Data-contract test: content-expansion manual sites production smoke over the generic site, grouping, engagement and one-shot contracts

The authored mixed manual encounter and the two high-tier boss sites of the
content expansion are exercised here through the shipped registries, with no
registry patching: real wilderness world, real site lifecycle settlement, real
movement-group record, real ordinary whole-cell engagement, real combat rounds,
real escape journeys, real quest defeat credit and a real committed reload.
Every observation names the defect it detects, and no assertion pins a
coordinate, count or variant key that the authored declarations already own.

The change declares no delta specs (``skip_specs: true``): the site, row
binding, grouping, whole-cell engagement, identity-keyed defeat credit and
one-shot lifecycle requirements already exist in the main specs. This module
therefore carries no new requirement annotation; the hand-off lists the
existing requirement and scenario each observation establishes. Its
data-contract exemption is registered in ``tools/test_data_freeze.json`` and
``tools/test_data_lint_seed.json``.
"""

from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.lore.monster_activity import movement_units
from world.lore.monster_placement import (
    ECOLOGY_ZONE_REGISTRY,
    ENCOUNTER_COMPOSITION_REGISTRY,
    MONSTER_SITE_REGISTRY,
    composition_row_bindings,
    variant_species_key,
)
from world.maps import monster_activity, monster_sites
from world.maps.monster_activity import group_of_member, read_monster_activity
from world.maps.monster_sites import (
    SITE_READ_CLEARED,
    SITE_STAGE_KIND,
    SITE_STATE_CLEARED,
    SITE_STATE_POPULATED,
    site_living_members,
    site_occurrence_groups,
    site_state,
)
from world.maps.population_lifecycle import (
    register_regional_population,
    settle_population_lifecycle,
)
from world.maps.regional_population import initialize_population_seed
from world.maps.wilderness_population import population_view
from world.maps.wilderness_provider import WILDERNESS_NAME, ElosernWildernessMapProvider
from world.quests.definitions import ObjectiveKind, QuestObjective, QuestStage
from world.quests.planner import quest_event_effect_planner
from world.quests.runtime import (
    QuestState,
    QuestTargetsUnavailable,
    read_records,
    to_storage,
)
from world.quests.tests._fixtures import RegistryIsolationMixin, accept, quest, register
from world.rules import clock as clock_module
from world.rules.action import _EVENT_EFFECT_PLANNERS, register_event_effect_planner
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage_group,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.monster_behaviour import resolve_behaviour_profile
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import GeographyPublicationMixin

#: The authored mixed manual encounter this smoke exercises.
SITE_KEY = "abandoned_transfer_station_encounter"

SEED = 11
DAY = 86400


class TransferStationEncounterTests(
    GeographyPublicationMixin, BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest
):
    """One real site occurrence, one ordinary session, one durable one-shot clear."""

    def setUp(self):
        super().setUp()
        self.site = MONSTER_SITE_REGISTRY[SITE_KEY]
        self.composition = ENCOUNTER_COMPOSITION_REGISTRY[self.site.composition_key]
        register_regional_population()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.assertTrue(
            enter_wilderness(
                self.char1,
                coordinates=self.site.coordinates,
                name=WILDERNESS_NAME,
            )
        )
        self.room = self.char1.location
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        # The smoke is about the site's contracts, not about combat balance:
        # pin the dice-facing stats so one basic attack is lethal and the
        # player always acts first.
        self.char1.traits.hp.base = 600
        self.char1.traits.hp.current = 600
        self.char1.traits.atk_phys.base = 1000
        self.char1.traits.agility.base = 1000
        self._install_quest_planner()

    # -- fixtures -----------------------------------------------------------

    def _install_quest_planner(self) -> None:
        """Register the real quest planner and restore whatever was there."""
        previous = _EVENT_EFFECT_PLANNERS.get("quest")
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.addCleanup(self._restore_quest_planner, previous)

    @staticmethod
    def _restore_quest_planner(previous) -> None:
        if previous is None:
            _EVENT_EFFECT_PLANNERS.pop("quest", None)
        else:
            _EVENT_EFFECT_PLANNERS["quest"] = previous

    def _settle(self) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            settle_population_lifecycle(0, 0)

    def _living(self) -> tuple[Monster, ...]:
        return monster_sites._living_members(self.wilderness, self.site)

    def _rows(self, state) -> tuple[tuple[str, int], ...]:
        """The saved occurrence's sampled composition rows."""
        return site_occurrence_groups(
            self.site,
            seed=int(state.seed),
            sequence=int(state.generation_sequence),
        )

    def _accept_clear_out(self):
        """Register and accept the site's hand-written clear-out commission."""
        self.definition = register(
            quest(
                "t_transfer_station_clear_out",
                stages=(
                    QuestStage(
                        0,
                        QuestObjective(
                            kind=ObjectiveKind.DEFEAT,
                            quantity=len(self._living()),
                            requires_bound_targets=True,
                            site_key=SITE_KEY,
                        ),
                    ),
                ),
            )
        )
        return accept(self.char1, self.definition.key)

    def _record(self):
        return next(
            record
            for record in read_records(self.char1)
            if record.definition_key == self.definition.key
        )

    def _engage(self) -> tuple[Monster, ...]:
        members = self._living()
        engage_group(self.char1, members)
        return members

    def _defeat_round(self, member: Monster) -> dict:
        """Resolve one ordinary session round that must kill ``member``."""
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            result = submit_player_action(self.char1, BASIC_ATTACK_KEY, [member])
        self.assertIn(result["outcome"], ("round", "victory"), result)
        self.assertEqual(member.traits.hp.current, 0)
        return result

    # -- population ---------------------------------------------------------

    def test_settling_the_site_populates_its_complete_composition(self):
        self._settle()
        state = site_state(SITE_KEY, wilderness=self.wilderness)
        self.assertIsNotNone(state)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        members = monster_sites._members(self.wilderness, self.site)
        # Distinct persisted identities, all owned by this site: a truncated or
        # cycled occurrence would repeat or lose one.
        self.assertEqual(len({member.pk for member in members}), len(members))
        self.assertEqual(
            sorted(member.pk for member in members), sorted(state.member_ids)
        )
        self.assertEqual(
            Monster.objects.filter(pk__in=[member.pk for member in members]).count(),
            len(members),
        )
        for member in members:
            self.assertEqual(member.db.site_key, SITE_KEY)
            self.assertIs(member.location, self.room)
        # The variants are exactly the sampled composition rows.
        expected = Counter()
        for variant_key, count in self._rows(state):
            expected[variant_key] += count
        self.assertEqual(Counter(member.variant_key for member in members), expected)

    def test_the_site_forms_the_movement_groups_its_declarations_derive(self):
        self._settle()
        state = site_state(SITE_KEY, wilderness=self.wilderness)
        expected = movement_units(
            self._rows(state),
            composition_row_bindings(self.composition, site=self.site),
        )
        owned = [
            group
            for group in read_monster_activity(self.wilderness).groups.values()
            if group.home_owner == ("site", SITE_KEY)
        ]
        # One group per derived unit with its own binding and member count: a
        # whole-site grouping would collapse the pair and the stray into one.
        self.assertEqual(
            sorted((len(group.member_ids), group.activity_key) for group in owned),
            sorted(
                (len(unit.member_indices), unit.activity_key) for unit in expected
            ),
        )
        self.assertEqual(
            sorted(member_id for group in owned for member_id in group.member_ids),
            sorted(state.member_ids),
        )

    # -- engagement ---------------------------------------------------------

    def test_whole_cell_engagement_admits_all_three_as_distinct_targets(self):
        self._settle()
        members = self._engage()
        record = read_session(self.char1)
        self.assertIsNotNone(record)
        self.assertEqual(sorted(record.enemy_ids), sorted(member.pk for member in members))
        # Every roster entry is one actual individual: a duplicated or partial
        # admission would show a repeated id or a missing one.
        self.assertEqual(len(set(record.enemy_ids)), len(members))
        battlefield = reconstruct_battlefield(self.char1, record)
        foes = [
            entity
            for entity in battlefield.roster.values()
            if isinstance(entity, Monster)
        ]
        self.assertEqual(
            sorted(entity.pk for entity in foes),
            sorted(member.pk for member in members),
        )

    # -- defeat credit and the one-shot clear -------------------------------

    def test_defeating_all_three_credits_each_identity_once_and_clears_the_site(self):
        self._settle()
        record = self._accept_clear_out()
        members = self._engage()
        self.assertEqual(
            sorted(record.objective_target_ids), sorted(member.pk for member in members)
        )

        first = self._defeat_round(members[0])
        credited = self._record()
        self.assertEqual(credited.stage_progress, 1)
        self.assertEqual(credited.counted_defeat_ids, (members[0].pk,))

        # Redelivering the very event log that granted the credit plans no
        # quest write at all: a duplicate entry can never double-count.
        delivered = next(
            entry_log
            for entry_log in first["logs"]
            if any(entry.kind == "target_defeated" for entry in entry_log.entries)
        )
        before = to_storage(credited)
        effects = quest_event_effect_planner(
            SimpleNamespace(
                actor=self.char1, context=SimpleNamespace(battlefield=None)
            ),
            delivered,
        )
        self.assertEqual(
            [
                effect.description
                for effect in effects
                if effect.description.startswith("quest_log|")
            ],
            [],
        )
        self.assertEqual(to_storage(self._record()), before)

        for member in members[1:]:
            self._defeat_round(member)
        completed = self._record()
        self.assertEqual(completed.state, QuestState.COMPLETED)
        self.assertEqual(completed.stage_progress, len(members))
        self.assertIsNone(read_session(self.char1))

        # The one-shot site clears only at the next clock settlement, and its
        # clearing boundary is the committed loss occurrence.
        loss_tick = get_world_clock().tick
        get_world_clock().advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(SITE_KEY, wilderness=self.wilderness)
        self.assertEqual(cleared.state, SITE_STATE_CLEARED)
        self.assertEqual(cleared.cleared_at_tick, loss_tick)
        self.assertEqual(
            sorted(cleared.member_ids), sorted(member.pk for member in members)
        )

    def test_a_cleared_one_shot_site_stays_cleared_across_reload_settlement_read_and_acceptance(self):
        self._settle()
        self._accept_clear_out()
        members = self._engage()
        for member in members:
            self._defeat_round(member)
        self.assertIsNone(read_session(self.char1))
        loss_tick = get_world_clock().tick
        get_world_clock().advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(SITE_KEY, wilderness=self.wilderness)
        self.assertEqual(cleared.state, SITE_STATE_CLEARED)
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))

        # A committed reload drops the instance and attribute caches: identity
        # and lifecycle state must come back from the database.
        self.wilderness.flush_from_cache(force=True)
        self.wilderness.attributes.reset_cache()
        reloaded = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertIsNot(reloaded, self.wilderness)

        # A later clock settlement, the map's own population read and the
        # quest layer's binding read all observe the same cleared site.
        get_world_clock().advance(DAY, AdvanceSource.SKIP, [])
        state = site_state(SITE_KEY, wilderness=reloaded)
        self.assertEqual(state.state, SITE_STATE_CLEARED)
        self.assertEqual(state.cleared_at_tick, loss_tick)
        read = site_living_members(SITE_KEY, wilderness=reloaded)
        self.assertEqual(read.reason, SITE_READ_CLEARED)
        self.assertEqual(read.members, ())
        facts = population_view(reloaded, [self.site.coordinates])
        self.assertEqual([fact for fact in facts if fact.kind == "monster"], [])

        # No player action restores the site: a clear-out acceptance is refused
        # by name, and no individual is created.
        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.definition.key)
        self.assertEqual(caught.exception.region_key, SITE_KEY)
        self.assertEqual(caught.exception.reason, SITE_READ_CLEARED)
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )
        self.assertEqual(
            sorted(member.pk for member in monster_sites._members(reloaded, self.site)),
            sorted(member.pk for member in members),
        )


class HighTierBossSiteTests(
    GeographyPublicationMixin, BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest
):
    """Two labelled one-shot territorial bosses over the real site owner."""

    CROCODILE_SITE = "reservoir_crocodile_boss_site"
    BOAR_SITE = "ember_bristle_boss_site"

    def setUp(self):
        super().setUp()
        register_regional_population()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        # The smoke is about site, identity and escape contracts, not combat
        # balance: pin the dice-facing stats so the player always acts first.
        self.char1.traits.hp.base = 600
        self.char1.traits.hp.current = 600
        self.char1.traits.atk_phys.base = 1000
        self.char1.traits.agility.base = 1000
        self._install_quest_planner()

    # -- fixtures -----------------------------------------------------------

    def _install_quest_planner(self) -> None:
        """Register the real quest planner and restore whatever was there."""
        previous = _EVENT_EFFECT_PLANNERS.get("quest")
        register_event_effect_planner("quest", quest_event_effect_planner)
        self.addCleanup(self._restore_quest_planner, previous)

    @staticmethod
    def _restore_quest_planner(previous) -> None:
        if previous is None:
            _EVENT_EFFECT_PLANNERS.pop("quest", None)
        else:
            _EVENT_EFFECT_PLANNERS["quest"] = previous

    def _visit(self, site, *, neighbours: bool = False) -> None:
        """Enter a site's cell, creating the neighbouring rooms a flee needs."""
        if neighbours:
            x, y = site.coordinates
            for cell in (
                (x + 1, y),
                (x + 1, y + 1),
                (x, y + 1),
                (x - 1, y + 1),
                (x - 1, y),
                (x - 1, y - 1),
                (x, y - 1),
                (x + 1, y - 1),
            ):
                enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME)
        self.assertTrue(
            enter_wilderness(
                self.char1,
                coordinates=site.coordinates,
                name=WILDERNESS_NAME,
            )
        )

    def _settle(self) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            settle_population_lifecycle(0, 0)

    def _living(self, site) -> tuple[Monster, ...]:
        return monster_sites._living_members(self.wilderness, site)

    def _accept_clear_out(self, site_key: str):
        """Register and accept a hand-written clear-out for one boss site."""
        living = self._living(MONSTER_SITE_REGISTRY[site_key])
        self.definition = register(
            quest(
                f"t_boss_clear_out_{site_key}",
                stages=(
                    QuestStage(
                        0,
                        QuestObjective(
                            kind=ObjectiveKind.DEFEAT,
                            quantity=len(living),
                            requires_bound_targets=True,
                            site_key=site_key,
                        ),
                    ),
                ),
            )
        )
        return accept(self.char1, self.definition.key)

    def _record(self):
        return next(
            record
            for record in read_records(self.char1)
            if record.definition_key == self.definition.key
        )

    def _engage(self, site) -> tuple[Monster, ...]:
        members = self._living(site)
        engage_group(self.char1, members)
        return members

    def _defeat_round(self, member: Monster) -> dict:
        """Resolve one ordinary session round that must kill ``member``."""
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            result = submit_player_action(self.char1, BASIC_ATTACK_KEY, [member])
        self.assertIn(result["outcome"], ("round", "victory"), result)
        self.assertEqual(member.traits.hp.current, 0)
        return result

    @staticmethod
    def _resources(monster: Monster) -> tuple[float, float, float]:
        """The boss's actual HP, MP and SP currents."""
        return tuple(
            float(getattr(monster.traits, key).current)
            for key in ("hp", "mp", "sp")
        )

    # -- labelled one-shot populations --------------------------------------

    def test_each_boss_site_populates_one_labelled_territorial_individual(self):
        self._settle()
        pooled = {
            member.variant_key
            for zone in ECOLOGY_ZONE_REGISTRY.values()
            for row in zone.pool
            for member in ENCOUNTER_COMPOSITION_REGISTRY[row.composition_key].members
        }
        for site_key in (self.CROCODILE_SITE, self.BOAR_SITE):
            with self.subTest(site=site_key):
                site = MONSTER_SITE_REGISTRY[site_key]
                composition = ENCOUNTER_COMPOSITION_REGISTRY[site.composition_key]
                state = site_state(site_key, wilderness=self.wilderness)
                self.assertEqual(state.state, SITE_STATE_POPULATED)
                members = monster_sites._members(self.wilderness, site)
                # One persistent individual, keyed by the authored display
                # label while identity stays the composition's species/variant
                # pair: a label mistaken for identity, or a replaced row, fails.
                self.assertEqual(len(members), 1)
                (boss,) = members
                self.assertEqual(boss.key, site.individual_label_zh)
                self.assertEqual(boss.variant_key, composition.members[0].variant_key)
                self.assertEqual(boss.species_key, variant_species_key(boss.variant_key))
                self.assertEqual(boss.db.site_key, site_key)
                self.assertEqual(state.member_ids, (boss.pk,))
                groups = [
                    group
                    for group in read_monster_activity(self.wilderness).groups.values()
                    if group.home_owner == ("site", site_key)
                ]
                self.assertEqual(len(groups), 1)
                self.assertEqual(
                    groups[0].activity_key,
                    composition_row_bindings(composition, site=site)[0],
                )
                self.assertEqual(groups[0].member_ids, (boss.pk,))
                # Automatic birth must never select this boss's variant.
                self.assertNotIn(boss.variant_key, pooled)

    # -- one-shot defeat ----------------------------------------------------

    def test_defeating_the_crocodile_boss_leaves_the_site_cleared_across_reload_revisit_read_and_acceptance(
        self,
    ):
        site = MONSTER_SITE_REGISTRY[self.CROCODILE_SITE]
        self._visit(site)
        self._settle()
        self._accept_clear_out(self.CROCODILE_SITE)
        members = self._engage(site)
        self.assertEqual(len(members), 1)
        (boss,) = members
        self._defeat_round(boss)
        self.assertEqual(self._record().state, QuestState.COMPLETED)
        self.assertIsNone(read_session(self.char1))
        loss_tick = get_world_clock().tick
        get_world_clock().advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(self.CROCODILE_SITE, wilderness=self.wilderness)
        self.assertEqual(cleared.state, SITE_STATE_CLEARED)
        self.assertEqual(cleared.cleared_at_tick, loss_tick)
        self.assertEqual(cleared.member_ids, (boss.pk,))
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))

        # A committed reload drops both the wilderness and individual caches.
        self.wilderness.flush_from_cache(force=True)
        self.wilderness.attributes.reset_cache()
        boss.flush_from_cache(force=True)
        boss.attributes.reset_cache()
        reloaded = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        reloaded_boss = Monster.objects.get(pk=boss.pk)
        self.assertIsNot(reloaded, self.wilderness)
        self.assertIsNot(reloaded_boss, boss)

        # A later clock settlement, a real revisit, the map's own population
        # read and the quest layer's binding read observe one cleared site.
        get_world_clock().advance(DAY, AdvanceSource.SKIP, [])
        x, y = site.coordinates
        self.assertTrue(
            enter_wilderness(
                self.char1, coordinates=(x + 1, y), name=WILDERNESS_NAME
            )
        )
        self.assertTrue(
            enter_wilderness(
                self.char1, coordinates=site.coordinates, name=WILDERNESS_NAME
            )
        )
        state = site_state(self.CROCODILE_SITE, wilderness=reloaded)
        self.assertEqual(state.state, SITE_STATE_CLEARED)
        self.assertEqual(state.cleared_at_tick, loss_tick)
        self.assertEqual(state.member_ids, (boss.pk,))
        read = site_living_members(self.CROCODILE_SITE, wilderness=reloaded)
        self.assertEqual(read.reason, SITE_READ_CLEARED)
        self.assertEqual(read.members, ())
        facts = population_view(reloaded, [site.coordinates])
        self.assertEqual([fact for fact in facts if fact.kind == "monster"], [])

        # No player action restores the one-shot site, and no individual is
        # created.
        with self.assertRaises(QuestTargetsUnavailable) as caught:
            accept(self.char1, self.definition.key)
        self.assertEqual(caught.exception.region_key, self.CROCODILE_SITE)
        self.assertEqual(caught.exception.reason, SITE_READ_CLEARED)
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )
        self.assertEqual(
            sorted(member.pk for member in monster_sites._members(reloaded, site)),
            [boss.pk],
        )

    # -- living escape ------------------------------------------------------

    def test_an_escaped_boar_keeps_identity_ownership_and_resources_through_reload_and_reengagement(
        self,
    ):
        site = MONSTER_SITE_REGISTRY[self.BOAR_SITE]
        self._visit(site, neighbours=True)
        self._settle()
        (boss,) = self._living(site)

        # Journey passage regenerates every gauge by elapsed time. Pinning the
        # rates keeps the departure resources exactly observable, so a reset or
        # a replacement monster cannot hide behind a regenerated full bar.
        for key in ("hp", "mp", "sp"):
            getattr(boss.traits, key).rate = 0
        profile = resolve_behaviour_profile(boss)
        threshold = float(boss.traits.hp.max) * profile.flee_hp_fraction
        # The player's opening hit is one point of damage at this attack value:
        # the first round is a real fight above the boundary, and the second
        # round crosses it. MP and SP start below their maximums so an exit-time
        # refill cannot hide behind an already-full bar.
        boss.traits.hp.current = round(threshold) + 2
        boss.traits.mp.current = float(boss.traits.mp.max) - 1
        boss.traits.sp.current = float(boss.traits.sp.max) - 1
        self.char1.traits.atk_phys.base = 1

        engage_group(self.char1, [boss])
        record = read_session(self.char1)
        self.assertIsNotNone(record)
        self.assertEqual(record.enemy_ids, (boss.pk,))

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            first = submit_player_action(self.char1, BASIC_ATTACK_KEY, [boss])
        self.assertEqual(first["outcome"], "round", first)
        self.assertGreater(boss.traits.hp.current, threshold)

        with (
            patch(
                "world.rules.disengage._attempt_flee",
                return_value=(
                    True,
                    {"roll": 100, "actor_agility": 200.0, "pursuer_agility": 200.0},
                ),
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            second = submit_player_action(self.char1, BASIC_ATTACK_KEY, [boss])
        # The only foe has left, so the session settles terminally.
        self.assertEqual(second["outcome"], "victory", second)
        self.assertIsNone(read_session(self.char1))
        attempts = [
            entry
            for log in second["logs"]
            for entry in log.entries
            if entry.kind == "disengage_attempt"
        ]
        self.assertTrue(attempts, second)
        self.assertTrue(attempts[0].data["success"], attempts[0].data)
        self.assertIsNone(boss.location)

        journey = next(iter(read_monster_activity(self.wilderness).journeys.values()))
        self.assertEqual(journey.member_ids, (boss.pk,))
        group = group_of_member(self.wilderness, boss.pk)
        self.assertIsNotNone(group)
        self.assertEqual(group.home_owner, ("site", self.BOAR_SITE))

        # A site settlement after the departure must not clear a site whose own
        # member is alive but temporarily absent.
        monster_sites.settle_monster_sites_at(journey.depart_tick)
        self.assertEqual(
            site_state(self.BOAR_SITE, wilderness=self.wilderness).state,
            SITE_STATE_POPULATED,
        )

        departure = self._resources(boss)
        self.assertLess(departure[0], float(boss.traits.hp.max))
        self.assertLess(departure[1], float(boss.traits.mp.max))
        self.assertLess(departure[2], float(boss.traits.sp.max))

        monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )

        self.wilderness.flush_from_cache(force=True)
        self.wilderness.attributes.reset_cache()
        boss.flush_from_cache(force=True)
        boss.attributes.reset_cache()
        reloaded = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        reloaded_boss = Monster.objects.get(pk=boss.pk)
        self.assertIsNot(reloaded_boss, boss)

        # Identity, ownership and the actual remaining resources come back from
        # the database, not from an instance cache.
        self.assertEqual(self._resources(reloaded_boss), departure)
        self.assertEqual(reloaded_boss.db.site_key, self.BOAR_SITE)
        self.assertEqual(
            group_of_member(reloaded, boss.pk).home_owner,
            ("site", self.BOAR_SITE),
        )
        self.assertEqual(
            site_state(self.BOAR_SITE, wilderness=reloaded).state,
            SITE_STATE_POPULATED,
        )

        destination = (journey.destination.x, journey.destination.y)
        self.assertTrue(
            enter_wilderness(
                self.char1, coordinates=destination, name=WILDERNESS_NAME
            )
        )
        self.assertIs(reloaded_boss.location, self.char1.location)
        engage_group(self.char1, [reloaded_boss])
        session = read_session(self.char1)
        self.assertIsNotNone(session)
        self.assertIn(reloaded_boss.pk, session.enemy_ids)
        battlefield = reconstruct_battlefield(self.char1, session)
        foes = [
            entity
            for entity in battlefield.roster.values()
            if isinstance(entity, Monster)
        ]
        self.assertEqual(len(foes), 1)
        self.assertEqual(foes[0].pk, reloaded_boss.pk)
        # A new engagement starts with the departure resources; nothing resets
        # them on exit, re-entry or reload.
        self.assertEqual(self._resources(foes[0]), departure)
