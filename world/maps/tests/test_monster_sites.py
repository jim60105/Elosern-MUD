"""Behavior tests for the monster site lifecycle owner (monster-site-placement).

Site and ambient rows here are file-local synthetic fixtures injected through
the synthetic test-data kit's ``extra=`` seam, and the individuals' identities
come from the kit's synthetic species/variant catalogs, so no shipped
placement, species, or variant key is named. The probe cell's region key is
read from the live terrain model at runtime.

The local rows exercise execution, not authoring validation (the lore tests own
that): habitat compatibility speaks the shipped region vocabulary while a
region's cells come from the live terrain model, so a local row pairs a
synthetic species with a runtime-read region key.
"""

from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.objects.models import ObjectDB
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    RECOVERY_CONDITION_FIELDS,
    AmbientPlacementRule,
    MonsterSite,
    variant_species_key,
)
from world.maps import monster_sites
from world.maps.bootstrap import sync_wilderness
from world.maps.monster_sites import (
    SITE_STAGE_KIND,
    SITE_STATE_CLEARED,
    SITE_STATE_POPULATED,
    settle_monster_sites,
    settle_site_recovery,
    site_state,
    snapshot_monster_site_surfaces,
)
from world.maps.wilderness_population import (
    _population_key,
    _stored_hp,
    ensure_population,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules import clock as clock_module
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.monster_individual import construct_species_individual
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import (
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    synthetic_registries,
)

_VARIANTS = tuple(SYNTH_MONSTER_VARIANTS)
ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]
_WITNESS_TIER = next(iter(SYNTH_MONSTER_TIERS))

#: A walkable south-western wild cell: outside the capital's and the village's
#: anchor footprints and far from the contract-pinned hunting band.
PROBE = (30, 30)
NEST_KEY = "t_probe_nest"
CAMP_KEY = "t_probe_camp"
HOUR = 3600


def _local_row(ordinary, habitat: str, **overrides) -> AmbientPlacementRule:
    """One synthetic ambient rule for the probe's region."""
    fields = {
        "region_key": habitat,
        "variant_keys": (ordinary,),
        "quantity": 1,
        "capacity": 1,
        "selection_salt": 0,
    }
    fields.update(overrides)
    return AmbientPlacementRule(**fields)


def _members(wilderness, site: MonsterSite) -> tuple[Monster, ...]:
    return monster_sites._members(wilderness, site)


def _living(wilderness, site: MonsterSite) -> tuple[Monster, ...]:
    return tuple(member for member in _members(wilderness, site) if _stored_hp(member) > 0)


class MonsterSiteLifecycleTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """The one site owner: population, clearing, recovery, and its contract."""

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        self.region = region_for_coordinates(*PROBE)
        self.rule = _local_row(ORDINARY, self.region)
        self.sites = {
            NEST_KEY: MonsterSite(
                NEST_KEY,
                "nest",
                self.region,
                PROBE,
                (ORDINARY, STRONGER),
                2,
                True,
            ),
            CAMP_KEY: MonsterSite(
                CAMP_KEY,
                "camp",
                self.region,
                PROBE,
                (STRONGER,),
                1,
                False,
                HOUR,
            ),
        }
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "ambient_placements",
                "monster_sites",
                extra={
                    "ambient_placements": {self.region: self.rule},
                    "monster_sites": self.sites,
                },
            )
        )
        monster_sites.register_monster_site_lifecycle()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.clock = get_world_clock()

    # -- helpers ------------------------------------------------------------

    def _settle(self, end_tick: int = 0):
        with self.captureOnCommitCallbacks(execute=True):
            return settle_monster_sites(0, end_tick)

    def _defeat(self, site: MonsterSite) -> tuple[int, ...]:
        defeated = []
        for member in _members(self.wilderness, site):
            member.traits.hp.current = 0
            defeated.append(member.pk)
        return tuple(defeated)

    # -- population ---------------------------------------------------------

    def test_the_first_settlement_populates_each_site_to_its_capacity(self):
        with (
            patch("world.maps.monster_sites.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            events = settle_monster_sites(0, 0)
        self.assertEqual(events, [])
        for key, site in self.sites.items():
            with self.subTest(site=key):
                members = _members(self.wilderness, site)
                self.assertEqual(len(members), site.capacity)
                for member in members:
                    self.assertEqual(member.db.site_key, key)
                    self.assertIn(member.variant_key, site.variant_keys)
                    self.assertGreater(member.traits.hp.current, 0)
                    self.assertEqual(
                        self.wilderness.db.itemcoordinates[member], PROBE
                    )
                    self.assertIs(member.location, self.room)
                state = site_state(key, wilderness=self.wilderness)
                self.assertEqual(state.state, SITE_STATE_POPULATED)
                self.assertIsNone(state.cleared_at_tick)
        # The scoped registry also carries the kit's own synthetic sites; the
        # assertions below pin this module's authored rows.
        site_calls = [
            call for call in info.call_args_list if call.kwargs["context"]["site"] in self.sites
        ]
        self.assertEqual(len(site_calls), len(self.sites))
        for call in site_calls:
            self.assertEqual(call.args[0], "monster_site_populated")
            context = call.kwargs["context"]
            self.assertEqual(
                set(context),
                {"site", "region", "coordinate", "species", "variant", "tick", "created"},
            )
            self.assertEqual(context["region"], self.region)
            self.assertEqual(context["coordinate"], PROBE)

    def test_capacity_is_a_ceiling_and_never_reshuffles(self):
        self._settle()
        # A living individual beyond the authored capacity is neither deleted
        # (no reshuffle to make room) nor joined by a replacement (the ceiling
        # forbids additions).
        surplus = construct_species_individual(
            variant_species_key(STRONGER), STRONGER
        )
        surplus.db.site_key = NEST_KEY
        self.wilderness.db.itemcoordinates[surplus] = PROBE
        surplus.location = self.room
        before = sorted(member.pk for member in _members(self.wilderness, self.sites[NEST_KEY]))
        self._settle()
        after = sorted(member.pk for member in _members(self.wilderness, self.sites[NEST_KEY]))
        self.assertEqual(after, before)
        self.assertEqual(len(after), 3)

    # -- one-shot -----------------------------------------------------------

    def test_a_one_shot_site_stays_cleared_across_advances_and_re_entry(self):
        self._settle()
        defeated = self._defeat(self.sites[NEST_KEY])

        self.clock.advance(60, AdvanceSource.SKIP, [])
        state = site_state(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_CLEARED)
        self.assertEqual(state.cleared_at_tick, 60)

        # A full game day later, on re-entry, and on the startup sync path the
        # one-shot site creates nothing: the defeated rows stay dead in place.
        self.clock.advance(86400, AdvanceSource.SKIP, [])
        self.wilderness.mapprovider.at_prepare_room(PROBE, self.char1, self.room)
        sync_wilderness()
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )
        self.assertEqual(
            sorted(member.pk for member in _members(self.wilderness, self.sites[NEST_KEY])),
            sorted(defeated),
        )

    def test_a_quest_acceptance_cannot_reach_the_site_owner(self):
        from world.quests.definitions import QuestStage
        from world.quests.tests._fixtures import accept, defeat, quest, register

        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self._settle()
        defeated = self._defeat(self.sites[NEST_KEY])
        # The clock settlement is what declares the site clear; no player
        # action can stand in for it.
        self.clock.advance(60, AdvanceSource.SKIP, [])
        definition = register(
            quest(
                "t_probe_hunt",
                stages=(QuestStage(0, defeat(_WITNESS_TIER, quantity=1)),),
            )
        )
        with patch("world.maps.monster_sites._populate") as populate:
            accept(self.char1, definition.key)
            self.wilderness.mapprovider.at_prepare_room(PROBE, self.char1, self.room)
        self.assertFalse(populate.called)
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )
        self.assertEqual(
            sorted(member.pk for member in _members(self.wilderness, self.sites[NEST_KEY])),
            sorted(defeated),
        )

    # -- recovery -----------------------------------------------------------

    def test_a_recoverable_site_recovers_at_its_condition_with_fresh_identities(self):
        self._settle()
        defeated = self._defeat(self.sites[CAMP_KEY])

        self.clock.advance(60, AdvanceSource.SKIP, [])
        self.assertEqual(
            site_state(CAMP_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )
        self.clock.advance(1800, AdvanceSource.SKIP, [])
        self.assertEqual(
            site_state(CAMP_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )
        self.assertEqual(_living(self.wilderness, self.sites[CAMP_KEY]), ())

        tick = self.clock.tick + 1800
        with (
            patch("world.maps.monster_sites.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            events = self.clock.advance(1800, AdvanceSource.SKIP, [])

        recovered = _living(self.wilderness, self.sites[CAMP_KEY])
        self.assertEqual(len(recovered), self.sites[CAMP_KEY].capacity)
        self.assertTrue({member.pk for member in recovered}.isdisjoint(defeated))
        for member in recovered:
            self.assertEqual(member.db.site_key, CAMP_KEY)
            self.assertEqual(
                self.wilderness.db.itemcoordinates[member], PROBE
            )
        state = site_state(CAMP_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        self.assertIsNone(state.cleared_at_tick)

        self.assertEqual(
            [event.kind for event in events], ["monster_site_recovered"]
        )
        self.assertEqual(
            events[0].payload["variants"], list(self.sites[CAMP_KEY].variant_keys)
        )
        recovered_calls = [
            call
            for call in info.call_args_list
            if call.args[0] == "monster_site_recovered"
        ]
        self.assertEqual(len(recovered_calls), 1)
        context = recovered_calls[0].kwargs["context"]
        self.assertEqual(context["site"], CAMP_KEY)
        self.assertEqual(context["variant"], self.sites[CAMP_KEY].variant_keys)
        self.assertEqual(context["tick"], tick)
        self.assertEqual(context["cleared_at_tick"], 60)

    def test_rejected_recovery_attempts_emit_one_warn_event(self):
        self._settle()
        cases = []
        # A one-shot site never recovers, however far the clock runs.
        cases.append((NEST_KEY, 10 * HOUR, "one_shot"))
        # A recoverable site that is not cleared has no recovery to make.
        cases.append((CAMP_KEY, 0, "not_cleared"))
        for site_key, tick, reason in cases:
            with self.subTest(site=site_key, reason=reason):
                with (
                    patch("world.maps.monster_sites.log_warn") as warn,
                    self.captureOnCommitCallbacks(execute=True),
                ):
                    self.assertFalse(
                        settle_site_recovery(
                            site_key, tick, wilderness=self.wilderness
                        )
                    )
                warn.assert_called_once()
                self.assertEqual(
                    warn.call_args.args[0], "monster_site_recovery_rejected"
                )
                self.assertEqual(warn.call_args.kwargs["context"]["reason"], reason)

        # A due site whose footprint still holds a living member refuses to add
        # individuals past its authored capacity.
        self._defeat(self.sites[CAMP_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        revived = construct_species_individual(
            variant_species_key(STRONGER), STRONGER
        )
        revived.db.site_key = CAMP_KEY
        self.wilderness.db.itemcoordinates[revived] = PROBE
        with (
            patch("world.maps.monster_sites.log_warn") as warn,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertFalse(
                settle_site_recovery(
                    CAMP_KEY, 10 * HOUR, wilderness=self.wilderness
                )
            )
        warn.assert_called_once()
        self.assertEqual(
            warn.call_args.kwargs["context"]["reason"], "capacity_reached"
        )

    # -- ownership domains --------------------------------------------------

    def test_the_two_owners_never_cross_domains(self):
        self._settle()
        marker = _population_key(*PROBE)
        ambient = [
            member
            for member in self.wilderness.get_objs_at_coordinates(PROBE)
            if isinstance(member, Monster) and member.db.population_key == marker
        ]
        self.assertTrue(ambient)
        site_members = _members(self.wilderness, self.sites[NEST_KEY])
        site_before = {
            member.pk: (member.traits.hp.current, member.db.site_key)
            for member in site_members
        }

        # Ambient reconciliation at the site's own coordinate leaves the site's
        # individuals exactly as they were.
        ensure_population(self.wilderness, PROBE)
        self.assertEqual(
            {
                member.pk: (member.traits.hp.current, member.db.site_key)
                for member in _members(self.wilderness, self.sites[NEST_KEY])
            },
            site_before,
        )

        # ... and site settlement leaves the ambient individuals untouched.
        ambient_before = sorted(
            (
                member.pk,
                member.traits.hp.current,
                member.variant_key,
            )
            for member in ambient
        )
        self._defeat(self.sites[NEST_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        ambient_after = sorted(
            (
                member.pk,
                member.traits.hp.current,
                member.variant_key,
            )
            for member in self.wilderness.get_objs_at_coordinates(PROBE)
            if isinstance(member, Monster) and member.db.population_key == marker
        )
        self.assertEqual(ambient_after, ambient_before)

    def test_foreign_and_other_owner_monsters_are_never_touched(self):
        from evennia.utils.create import create_object

        self._settle()
        probes = []
        foreign = create_object(Monster, key="t_foreign_site_witness")
        foreign.threat_tier = _WITNESS_TIER
        foreign.apply_monster_tier("floor")
        foreign.db.population_key = None
        foreign.traits.hp.current = 7
        self.wilderness.db.itemcoordinates[foreign] = PROBE
        probes.append(foreign)
        other_site = create_object(Monster, key="t_other_site_witness")
        other_site.threat_tier = _WITNESS_TIER
        other_site.apply_monster_tier("floor")
        other_site.db.site_key = "t_somewhere_else"
        other_site.traits.hp.current = 5
        self.wilderness.db.itemcoordinates[other_site] = PROBE
        probes.append(other_site)
        elsewhere = create_object(Monster, key="t_other_coordinate_witness")
        elsewhere.threat_tier = _WITNESS_TIER
        elsewhere.apply_monster_tier("floor")
        elsewhere.db.population_key = _population_key(PROBE[0] + 1, PROBE[1])
        elsewhere.traits.hp.current = 3
        self.wilderness.db.itemcoordinates[elsewhere] = PROBE
        probes.append(elsewhere)

        self._defeat(self.sites[NEST_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        ensure_population(self.wilderness, PROBE)

        for probe in probes:
            with self.subTest(monster=probe.key):
                self.assertTrue(ObjectDB.objects.filter(pk=probe.pk).exists())
                self.assertEqual(
                    self.wilderness.db.itemcoordinates[probe], PROBE
                )

    # -- advance-surface contract ------------------------------------------

    @covers_requirement(
        "world-clock::every-registered-boundary-stage-source-declares-the-durable-surfaces-it-may-write"
    )
    def test_the_contract_is_a_pure_read_covering_the_state_and_bookkeeping(self):
        self._settle()
        state_before = dict(self.wilderness.db.monster_sites)
        coordinates_before = dict(self.wilderness.db.itemcoordinates)
        members = _members(self.wilderness, self.sites[NEST_KEY])
        markers_before = {member.pk: member.db.site_key for member in members}

        snapshot = snapshot_monster_site_surfaces(0, 0)

        self.assertIn(id(self.wilderness), snapshot)
        self.assertEqual(set(snapshot[id(self.wilderness)].attributes), {
            ("monster_sites", None),
            ("itemcoordinates", None),
        })
        for member in members:
            self.assertIn(id(member), snapshot)
            self.assertEqual(
                set(snapshot[id(member)].attributes), {("site_key", None)}
            )
        self.assertEqual(dict(self.wilderness.db.monster_sites), state_before)
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), coordinates_before)
        self.assertEqual(
            {member.pk: member.db.site_key for member in members}, markers_before
        )

    @covers_requirement(
        "world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities"
    )
    def test_a_failed_advance_restores_site_state_and_leaves_no_cached_individual(self):
        created: list[Monster] = []
        real_construct = construct_species_individual

        def flaky(species_key, variant_key, **kwargs):
            individual = real_construct(species_key, variant_key, **kwargs)
            created.append(individual)
            if len(created) >= 2:
                raise RuntimeError("injected site settlement failure")
            return individual

        states_before = self.wilderness.db.monster_sites
        tick_before = self.clock.tick
        with patch("world.maps.monster_sites.construct_species_individual", side_effect=flaky):
            with self.assertRaises(RuntimeError):
                self.clock.advance(60, AdvanceSource.SKIP, [])

        self.assertTrue(created)
        self.assertEqual(self.wilderness.db.monster_sites, states_before)
        self.assertEqual(self.clock.tick, tick_before)
        for individual in created:
            self.assertFalse(
                ObjectDB.objects.filter(pk=individual.pk).exists(),
                "a rolled-back individual must leave no durable row",
            )
            self.assertNotIn(
                individual.pk,
                ObjectDB.__instance_cache__,
                "a rolled-back instance must not be served for a recycled pk",
            )
        # Every individual still discoverable at an authored site's coordinate
        # is a real row: no ghost member survives its rolled-back row.
        for site in self.sites.values():
            for member in _members(self.wilderness, site):
                self.assertTrue(ObjectDB.objects.filter(pk=member.pk).exists())


class MonsterSiteStageWithoutWorldTests(EvenniaTest):
    """The stage is silent while no wilderness script exists."""

    def test_settlement_and_contract_are_absent_tolerant(self):
        monster_sites.register_monster_site_lifecycle()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)
        self.assertFalse(search_script(WILDERNESS_NAME))
        with (
            patch("world.maps.monster_sites.log_info") as info,
            patch("world.maps.monster_sites.log_warn") as warn,
            self.captureOnCommitCallbacks(execute=True),
        ):
            events = get_world_clock().advance(60, AdvanceSource.SKIP, [])
            self.assertEqual(settle_monster_sites(0, 1000), [])
            self.assertEqual(snapshot_monster_site_surfaces(0, 1000), {})
        info.assert_not_called()
        warn.assert_not_called()
        self.assertEqual(
            [event.kind for event in events if event.kind == "monster_site_recovered"],
            [],
        )


class SiteRowVocabularyTests(EvenniaTest):
    """The authored vocabulary the owner reads is the registry's own."""

    def test_the_owner_reads_the_registry_instead_of_a_local_copy(self):
        site = MonsterSite(
            "t_vocabulary_site",
            "boss_site",
            region_for_coordinates(*PROBE),
            PROBE,
            (ORDINARY,),
            1,
            False,
            HOUR,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={"monster_sites": {site.key: site}},
            )
        )
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        with self.captureOnCommitCallbacks(execute=True):
            settle_monster_sites(0, 0)
        members = _members(wilderness, site)
        self.assertEqual(len(members), site.capacity)
        self.assertEqual(RECOVERY_CONDITION_FIELDS, ("recover_after_ticks",))
        state = site_state(site.key, wilderness=wilderness)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        self.assertIsNone(state.cleared_at_tick)
        # The authored row drove the population: the owner holds no second copy
        # of a site's capacity or lifecycle.
        self.assertEqual(members[0].variant_key, site.variant_keys[0])
