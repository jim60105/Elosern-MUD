"""Monster site journeys (clearing)."""

from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.objects.models import ObjectDB
from typeclasses.monsters import Monster
from world.lore.monster_placement import MonsterSite, composition_variant_keys, variant_species_key
from world.maps import monster_sites
from world.maps.monster_sites import SITE_STATE_CLEARED, SITE_STATE_POPULATED, SITE_READ_CLEARED, SITE_READ_UNKNOWN_SITE, SITE_READ_UNPOPULATED, settle_site_recovery, site_living_members, site_state, snapshot_monster_site_surfaces
from world.maps.regional_population import MalformedPopulationState
from world.rules.clock import AdvanceSource
from world.rules.monster_individual import construct_species_individual
from world.tests.synthetic_data import synthetic_registries


from ._support import CAMP_KEY, COMPOSITIONS, FLOCK, HOUR, NEST_KEY, PAIR, PROBE, STATIONARY_ACTIVITY, STRONGER, _MonsterSiteFixture, _WITNESS_TIER, _living, _members

class MonsterSiteClearingTests(_MonsterSiteFixture):
    """One journey per site lifecycle rule."""

    def test_an_incomplete_saved_record_refuses_instead_of_repopulating(self):
        self._settle()
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))
        states = {
            key: dict(value)
            for key, value in self.wilderness.db.monster_sites.items()
        }
        # A pre-identity save: lifecycle state only, no occurrence or members.
        states[NEST_KEY] = {
            "state": SITE_STATE_CLEARED,
            "cleared_at_tick": 0,
        }
        self.wilderness.db.monster_sites = states

        self.assertFalse(
            site_state(NEST_KEY, wilderness=self.wilderness).readable
        )
        with self.assertRaises(MalformedPopulationState):
            self._settle()
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )

    @covers_requirement("monster-site-placement::one-shot-sites-stay-cleared-and-recoverable-sites-recover-only-on-approved-conditions")
    def test_a_one_shot_site_stays_cleared_across_advances_and_re_entry(self):
        self._settle()
        defeated = self._defeat(self.sites[NEST_KEY])

        self.clock.advance(60, AdvanceSource.SKIP, [])
        state = site_state(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_CLEARED)
        # The clearing boundary is the committed loss occurrence, never the
        # interval end the advance happened to stop at.
        self.assertEqual(state.cleared_at_tick, 0)

        # Four in-game hours later -- four times the recoverable camp's own
        # one-hour window, so the same advance recovers what may recover --
        # and on re-entry the one-shot site creates nothing: the defeated rows
        # stay dead in place. The span is bounded by the authored recovery
        # windows rather than an arbitrary day: a skipped day settles 2,880
        # ambient movement boundaries and costs minutes of runner time without
        # observing one more site decision.
        self.clock.advance(4 * HOUR, AdvanceSource.SKIP, [])
        self.wilderness.mapprovider.at_prepare_room(PROBE, self.char1, self.room)
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

    def test_an_active_combat_session_defers_the_clearing_decision(self):
        from world.rules.combat_session import engage

        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self._settle()
        members = _members(self.wilderness, self.sites[NEST_KEY])
        engage(self.char1, members[0])
        for member in members:
            member.traits.hp.current = 0

        self.clock.advance(60, AdvanceSource.SKIP, [])
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness).state,
            SITE_STATE_POPULATED,
            "a committed session still owns this defeat",
        )

        self.char1.db.active_combat = None
        self.clock.advance(60, AdvanceSource.SKIP, [])
        state = site_state(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_CLEARED)
        self.assertEqual(state.cleared_at_tick, 60)

    @covers_requirement("monster-site-placement::one-shot-sites-stay-cleared-and-recoverable-sites-recover-only-on-approved-conditions")
    @covers_requirement("monster-site-placement::placement-decisions-are-boundary-observable-through-the-facade")
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
        # Re-entering the room before the condition matures recovers nothing.
        self.wilderness.mapprovider.at_prepare_room(PROBE, self.char1, self.room)
        self.assertEqual(_living(self.wilderness, self.sites[CAMP_KEY]), ())
        self.assertEqual(
            site_state(CAMP_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )

        tick = (
            site_state(CAMP_KEY, wilderness=self.wilderness).cleared_at_tick
            + self.sites[CAMP_KEY].recover_after_ticks
        )
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
        camp_variants = list(
            composition_variant_keys(COMPOSITIONS[PAIR])
        )
        self.assertEqual(events[0].payload["variants"], camp_variants)
        recovered_calls = [
            call
            for call in info.call_args_list
            if call.args[0] == "monster_site_recovered"
        ]
        self.assertEqual(len(recovered_calls), 1)
        context = recovered_calls[0].kwargs["context"]
        self.assertEqual(context["site"], CAMP_KEY)
        self.assertEqual(context["variant"], tuple(camp_variants))
        self.assertEqual(context["tick"], tick)
        self.assertEqual(context["cleared_at_tick"], 0)

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

        # A due site that still owns a living member refuses to add individuals
        # past its authored capacity. The member is a saved identity (a record
        # whose clearing decision drifted), not merely a marked bystander.
        self._defeat(self.sites[CAMP_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        revived = construct_species_individual(
            variant_species_key(STRONGER), STRONGER
        )
        revived.db.site_key = CAMP_KEY
        self.wilderness.db.itemcoordinates[revived] = PROBE
        states = {
            key: dict(value)
            for key, value in self.wilderness.db.monster_sites.items()
        }
        states[CAMP_KEY]["member_ids"] = [revived.pk]
        self.wilderness.db.monster_sites = states
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

    def test_a_direct_recovery_advances_the_sequence_with_fresh_identities(self):
        herd = MonsterSite(
            "t_probe_herd",
            "camp",
            self.region,
            PROBE,
            FLOCK,
            STATIONARY_ACTIVITY,
            3,
            False,
            HOUR,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {herd.key: herd},
                },
            )
        )
        self._settle()
        first = site_state(herd.key, wilderness=self.wilderness)
        first_ids = set(first.member_ids)
        for member in _members(self.wilderness, herd):
            member.traits.hp.current = 0
        self.clock.advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(herd.key, wilderness=self.wilderness)
        self.assertEqual(cleared.state, SITE_STATE_CLEARED)
        self.assertEqual(cleared.member_ids, tuple(sorted(first_ids)))

        recovered = settle_site_recovery(
            herd.key, 60 + HOUR, wilderness=self.wilderness
        )

        self.assertTrue(recovered)
        state = site_state(herd.key, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        self.assertEqual(state.seed, first.seed)
        self.assertEqual(state.generation_sequence, first.generation_sequence + 1)
        self.assertTrue(set(state.member_ids).isdisjoint(first_ids))
        self.assertEqual(
            {member.pk for member in _living(self.wilderness, herd)},
            set(state.member_ids),
        )

    def test_a_failed_direct_recovery_after_a_registration_restores_everything(self):
        self._settle()
        self._defeat(self.sites[CAMP_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(CAMP_KEY, wilderness=self.wilderness)
        coordinates_before = dict(self.wilderness.db.itemcoordinates)
        real_construct = construct_species_individual
        created: list[Monster] = []

        def flaky(species_key, variant_key, **kwargs):
            individual = real_construct(species_key, variant_key, **kwargs)
            created.append(individual)
            if len(created) == 2:
                raise RuntimeError("injected direct recovery failure")
            return individual

        with (
            patch(
                "world.maps.monster_sites.construct_species_individual",
                side_effect=flaky,
            ),
            patch("world.maps.monster_sites.log_info") as info,
        ):
            with self.assertRaises(RuntimeError):
                settle_site_recovery(
                    CAMP_KEY, 60 + HOUR, wilderness=self.wilderness
                )
        info.assert_not_called()
        self.assertTrue(created)
        self.assertEqual(
            site_state(CAMP_KEY, wilderness=self.wilderness), cleared
        )
        self.assertEqual(
            dict(self.wilderness.db.itemcoordinates), coordinates_before
        )
        for individual in created:
            self.assertFalse(ObjectDB.objects.filter(pk=individual.pk).exists())
            self.assertNotIn(individual.pk, ObjectDB.__instance_cache__)

        # The retry replays the same occurrence and completes the group.
        self.assertTrue(
            settle_site_recovery(
                CAMP_KEY, 60 + HOUR, wilderness=self.wilderness
            )
        )
        state = site_state(CAMP_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        self.assertEqual(state.generation_sequence, cleared.generation_sequence + 1)
        self.assertEqual(len(_living(self.wilderness, self.sites[CAMP_KEY])), 2)

    def test_a_failed_state_write_restores_the_cleared_record(self):
        self._settle()
        self._defeat(self.sites[CAMP_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(CAMP_KEY, wilderness=self.wilderness)
        coordinates_before = dict(self.wilderness.db.itemcoordinates)
        real_write = monster_sites._write_state
        writes: list[int] = []

        def fail_after_write(wilderness, states):
            real_write(wilderness, states)
            if not writes:
                writes.append(1)
                raise RuntimeError("injected state write failure")

        with patch(
            "world.maps.monster_sites._write_state", side_effect=fail_after_write
        ):
            with self.assertRaises(RuntimeError):
                settle_site_recovery(
                    CAMP_KEY, 60 + HOUR, wilderness=self.wilderness
                )

        self.assertEqual(
            site_state(CAMP_KEY, wilderness=self.wilderness), cleared
        )
        self.assertEqual(
            dict(self.wilderness.db.itemcoordinates), coordinates_before
        )

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    def test_site_settlement_never_touches_a_foreign_individual(self):
        from evennia.utils.create import create_object

        self._settle()
        foreign = create_object(Monster, key="t_foreign_owner_witness")
        foreign.threat_tier = _WITNESS_TIER
        foreign.apply_monster_tier("floor")
        foreign.db.home_ecology_zone = "t_other_owner"
        foreign.traits.hp.current = 3
        self.wilderness.db.itemcoordinates[foreign] = PROBE

        # Site settlement leaves the foreign individual untouched.
        self._defeat(self.sites[NEST_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])
        self.assertTrue(ObjectDB.objects.filter(pk=foreign.pk).exists())
        self.assertEqual(self.wilderness.db.itemcoordinates[foreign], PROBE)
        self.assertEqual(foreign.traits.hp.current, 3)
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )

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
        elsewhere.db.home_ecology_zone = "t_other_zone"
        elsewhere.traits.hp.current = 3
        self.wilderness.db.itemcoordinates[elsewhere] = PROBE
        probes.append(elsewhere)

        self._defeat(self.sites[NEST_KEY])
        self.clock.advance(60, AdvanceSource.SKIP, [])

        for probe in probes:
            with self.subTest(monster=probe.key):
                self.assertTrue(ObjectDB.objects.filter(pk=probe.pk).exists())
                self.assertEqual(
                    self.wilderness.db.itemcoordinates[probe], PROBE
                )

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_a_populated_site_whose_members_are_all_dead_answers_an_empty_set(self):
        # Until the world clock's own settlement declares the clearing, the
        # durable state still says populated: the read answers the truth about
        # what stands (nothing) with no reason, and it is the caller's own
        # quantity comparison that then refuses the clear-out as short.
        self._settle()
        nest = self.sites[NEST_KEY]
        self._defeat(nest)

        read = site_living_members(NEST_KEY, wilderness=self.wilderness)

        self.assertTrue(read.available)
        self.assertIsNone(read.reason)
        self.assertEqual(read.state, SITE_STATE_POPULATED)
        self.assertEqual(read.members, ())
        # The settlement is what turns it into the cleared verdict, not the read.
        self.clock.advance(60, AdvanceSource.SKIP, [])
        settled = site_living_members(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(settled.reason, SITE_READ_CLEARED)

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_the_read_returns_the_sites_living_members_and_only_those(self):
        from evennia.utils.create import create_object

        self._settle()
        nest = self.sites[NEST_KEY]
        ambient = create_object(Monster, key="t_read_ambient_witness")
        ambient.threat_tier = _WITNESS_TIER
        ambient.apply_monster_tier("floor")
        ambient.db.home_ecology_zone = "t_read_other_owner"
        self.wilderness.db.itemcoordinates[ambient] = PROBE
        foreign = create_object(Monster, key="t_read_foreign_site_witness")
        foreign.threat_tier = _WITNESS_TIER
        foreign.apply_monster_tier("floor")
        foreign.db.site_key = "t_read_elsewhere"
        self.wilderness.db.itemcoordinates[foreign] = PROBE
        members = _members(self.wilderness, nest)
        dead = members[0]
        dead.traits.hp.current = 0

        read = site_living_members(NEST_KEY, wilderness=self.wilderness)

        self.assertTrue(read.available)
        self.assertEqual(
            [member.pk for member in read.members],
            [member.pk for member in members if member.pk != dead.pk],
        )
        for member in read.members:
            with self.subTest(member=member.pk):
                self.assertEqual(member.db.site_key, NEST_KEY)
        for excluded in (ambient, foreign, dead):
            with self.subTest(excluded=excluded.key):
                self.assertNotIn(excluded.pk, {m.pk for m in read.members})

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_the_read_modifies_nothing_even_from_a_cold_trait_handler(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self._settle()
        nest = self.sites[NEST_KEY]
        members = _members(self.wilderness, nest)
        # Force every member's trait handler cold: a read that materializes a
        # Trait from here issues a stored-attribute UPDATE (Evennia's Trait
        # constructor calls ``_SaverDict.update``, which saves on every call),
        # which is what this capture would catch.
        for member in members:
            member.__dict__.pop("traits", None)
        state_before = dict(self.wilderness.db.monster_sites)
        coordinates_before = dict(self.wilderness.db.itemcoordinates)
        surfaces_before = {
            member.pk: (
                member.db.site_key,
                self.wilderness.db.itemcoordinates.get(member),
                dict(member.attributes.get("traits", category="traits") or {}),
            )
            for member in members
        }

        with CaptureQueriesContext(connection) as queries:
            first = site_living_members(NEST_KEY, wilderness=self.wilderness)
            second = site_living_members(NEST_KEY, wilderness=self.wilderness)

        self.assertEqual(first, second)
        self.assertEqual(first.members, second.members)
        self.assertEqual(dict(self.wilderness.db.monster_sites), state_before)
        self.assertEqual(
            dict(self.wilderness.db.itemcoordinates), coordinates_before
        )
        self.assertEqual(
            {
                member.pk: (
                    member.db.site_key,
                    self.wilderness.db.itemcoordinates.get(member),
                    dict(member.attributes.get("traits", category="traits") or {}),
                )
                for member in members
            },
            surfaces_before,
        )
        writes = [
            query["sql"]
            for query in queries
            if query["sql"].lstrip().upper().startswith(
                ("UPDATE", "INSERT", "DELETE")
            )
        ]
        self.assertEqual(writes, [])

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_a_cleared_site_offers_no_members_and_stays_cleared(self):
        self._settle()
        nest = self.sites[NEST_KEY]
        self._defeat(nest)
        self.clock.advance(60, AdvanceSource.SKIP, [])
        cleared = site_state(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(cleared.state, SITE_STATE_CLEARED)
        state_before = dict(self.wilderness.db.monster_sites)
        coordinates_before = dict(self.wilderness.db.itemcoordinates)

        read = site_living_members(NEST_KEY, wilderness=self.wilderness)

        self.assertFalse(read.available)
        self.assertEqual(read.reason, SITE_READ_CLEARED)
        self.assertEqual(read.members, ())
        self.assertEqual(read.state, SITE_STATE_CLEARED)
        self.assertEqual(read.cleared_at_tick, cleared.cleared_at_tick)
        self.assertEqual(dict(self.wilderness.db.monster_sites), state_before)
        self.assertEqual(
            dict(self.wilderness.db.itemcoordinates), coordinates_before
        )
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness), cleared
        )

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_a_never_populated_site_is_not_populated_by_the_read(self):
        # No settlement has run, so neither site holds a durable state yet.
        self.assertIsNone(site_state(NEST_KEY, wilderness=self.wilderness))
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))

        read = site_living_members(NEST_KEY, wilderness=self.wilderness)

        self.assertFalse(read.available)
        self.assertEqual(read.reason, SITE_READ_UNPOPULATED)
        self.assertEqual(read.members, ())
        self.assertIsNone(read.state)
        self.assertEqual(read.site.key, NEST_KEY)
        self.assertIsNone(site_state(NEST_KEY, wilderness=self.wilderness))
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_the_read_answers_an_unknown_site_without_creating_anything(self):
        self._settle()
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))
        states_before = dict(self.wilderness.db.monster_sites)

        read = site_living_members("t_absent_site", wilderness=self.wilderness)

        self.assertFalse(read.available)
        self.assertEqual(read.reason, SITE_READ_UNKNOWN_SITE)
        self.assertEqual(read.members, ())
        self.assertIsNone(read.site)
        self.assertIsNone(read.state)
        self.assertEqual(dict(self.wilderness.db.monster_sites), states_before)
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )

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
    def test_a_failure_after_the_state_write_restores_it_and_evicts_the_created_individuals(self):
        created: list[Monster] = []
        real_construct = construct_species_individual

        def recording(species_key, variant_key, **kwargs):
            individual = real_construct(species_key, variant_key, **kwargs)
            created.append(individual)
            return individual

        states_before = self.wilderness.db.monster_sites
        coordinates_before = dict(self.wilderness.db.itemcoordinates)

        def boom(tick):
            raise RuntimeError("injected tick persistence failure")

        with (
            patch(
                "world.maps.monster_sites.construct_species_individual",
                side_effect=recording,
            ),
            patch.object(self.clock, "_persist", side_effect=boom),
        ):
            with self.assertRaises(RuntimeError):
                self.clock.advance(60, AdvanceSource.SKIP, [])

        self.assertTrue(created)
        # The whole-value per-site state write happened before the failure, so
        # the declared contract is what puts it back.
        self.assertEqual(self.wilderness.db.monster_sites, states_before)
        self.assertEqual(
            dict(self.wilderness.db.itemcoordinates), coordinates_before
        )
        for individual in created:
            self.assertFalse(ObjectDB.objects.filter(pk=individual.pk).exists())
            self.assertNotIn(individual.pk, ObjectDB.__instance_cache__)
        # A retry still populates every site normally, with fresh rows.
        self._settle()
        for key, site in self.sites.items():
            with self.subTest(site=key):
                self.assertEqual(len(_members(self.wilderness, site)), site.capacity)
                self.assertEqual(
                    site_state(key, wilderness=self.wilderness).state,
                    SITE_STATE_POPULATED,
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
