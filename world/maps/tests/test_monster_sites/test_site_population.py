"""Monster site journeys (population)."""

from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.objects.models import ObjectDB
from typeclasses.monsters import Monster
from world.lore.monster_placement import EcologyZone, MonsterSite, WeightedComposition, composition_variant_keys, variant_species_key
from world.maps import monster_activity as activity_owner
from world.maps import monster_sites
from world.maps import regional_population
from world.maps.monster_sites import SITE_STATE_CLEARED, SITE_STATE_POPULATED, SITE_READ_STATE_UNREADABLE, settle_site_recovery, site_living_members, site_state
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.wilderness_population import _stored_hp
from world.maps.wilderness_provider import is_valid_wilderness_cell, region_for_coordinates
from world.maps.regional_population import BLOCKED_LOCAL_SATISFIED, MalformedPopulationState, commit_population_wave, initialize_zone, plan_population_wave, population_counts, read_population_timeline, register_explicit_individual, sample_composition_counts
from world.rules.clock import AdvanceSource
from world.rules.monster_individual import construct_species_individual
from world.tests.synthetic_data import synthetic_registries


from ._support import COHESIVE_KEY, COMPOSITIONS, FLOCK, GROUP, GROUP_ACTIVITY, GROUP_KEY, HOUR, LABEL, LABELLED_KEY, MIXED_KEY, NEST_KEY, ORDINARY, OVERRIDE_KEY, PROBE, SEED, SOLITARY_ACTIVITY, SOLO, STATIONARY_ACTIVITY, STRAY_KEY, STRONGER, UNLABELLED_KEY, _MonsterSiteFixture, _WITNESS_TIER, _buffer_cell_inside_a_settlement_ring, _cell_zone, _eligible_birth_cells, _living, _members

class MonsterSitePopulationTests(_MonsterSiteFixture):
    """One journey per site lifecycle rule."""

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::placement-decisions-are-boundary-observable-through-the-facade")
    def test_the_first_settlement_populates_each_site_to_its_capacity(self):
        with (
            patch("world.maps.monster_sites.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            events = settle_population_lifecycle(0, 0)
        self.assertEqual(events, [])
        for key, site in self.sites.items():
            with self.subTest(site=key):
                members = _members(self.wilderness, site)
                self.assertEqual(len(members), site.capacity)
                self.assertEqual(
                    {member.variant_key for member in members},
                    set(
                        composition_variant_keys(
                            COMPOSITIONS[site.composition_key]
                        )
                    ),
                )
                for member in members:
                    self.assertEqual(member.db.site_key, key)
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

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_an_unchanged_site_pass_keeps_its_identities_and_resources(self):
        self._settle()
        nest = self.sites[NEST_KEY]
        before = {
            member.pk: (member.variant_key, _stored_hp(member))
            for member in _members(self.wilderness, nest)
        }
        state_before = site_state(NEST_KEY, wilderness=self.wilderness)

        # A repeat settlement is a no-op: the site already holds its complete
        # composition, so nothing is constructed, deleted, or re-rolled.
        self._settle()

        after = {
            member.pk: (member.variant_key, _stored_hp(member))
            for member in _members(self.wilderness, nest)
        }
        self.assertEqual(after, before)
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness), state_before
        )

    def test_a_foreign_marked_individual_is_never_adopted_or_replaced(self):
        self._settle()
        nest = self.sites[NEST_KEY]
        # A row that carries the site marker but is not one of the site's
        # saved member identities (an author-side fixture, a foreign writer):
        # the site neither adopts it into its composition nor deletes it.
        surplus = construct_species_individual(
            variant_species_key(STRONGER), STRONGER
        )
        surplus.db.site_key = NEST_KEY
        self.wilderness.db.itemcoordinates[surplus] = PROBE
        surplus.location = self.room
        before = sorted(member.pk for member in _members(self.wilderness, nest))

        self._settle()

        after = sorted(member.pk for member in _members(self.wilderness, nest))
        self.assertEqual(after, before)
        self.assertNotIn(surplus.pk, after)
        self.assertTrue(ObjectDB.objects.filter(pk=surplus.pk).exists())
        self.assertEqual(
            self.wilderness.db.itemcoordinates[surplus], PROBE
        )

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_a_mixed_composition_places_each_row_with_its_own_identity_and_resources(
        self,
    ):
        self._settle()
        group = self.sites[GROUP_KEY]

        members = _members(self.wilderness, group)

        self.assertEqual(len(members), 3)
        self.assertEqual(
            sorted(member.variant_key for member in members),
            sorted((ORDINARY, ORDINARY, STRONGER)),
        )
        self.assertEqual(len({member.pk for member in members}), 3)
        # Every individual stores its own resources: changing one member's
        # stored HP leaves every other member's stored value untouched.
        for member in members:
            self.assertGreater(_stored_hp(member), 0)
        before = {member.pk: _stored_hp(member) for member in members}
        first, second = members[0], members[1]
        first.traits.hp.current = 1
        self.assertEqual(_stored_hp(first), 1)
        self.assertEqual(
            {
                member.pk: _stored_hp(member)
                for member in members
                if member.pk != first.pk
            },
            {
                member.pk: value
                for member.pk, value in before.items()
                if member.pk != first.pk
            },
        )
        self.assertEqual(_stored_hp(second), before[second.pk])
        state = site_state(GROUP_KEY, wilderness=self.wilderness)
        self.assertEqual(state.member_ids, tuple(member.pk for member in members))
        self.assertEqual(state.generation_sequence, 0)
        self.assertIsInstance(state.seed, int)
        self.assertTrue(state.readable)

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_a_solitary_stray_places_exactly_one_individual(self):
        self._settle()

        members = _members(self.wilderness, self.sites[STRAY_KEY])

        self.assertEqual(self.sites[STRAY_KEY].kind, "stray")
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].variant_key, STRONGER)
        self.assertEqual(members[0].db.site_key, STRAY_KEY)

    @covers_requirement(
        "monster-field-activity::placements-form-movement-groups-from-their-binding-policy"
    )
    def test_a_cohesive_site_binding_forms_one_group_owned_by_the_site(self):
        cohesive = MonsterSite(
            COHESIVE_KEY,
            "encounter",
            self.region,
            PROBE,
            GROUP,
            GROUP_ACTIVITY,
            3,
            True,
        )
        self.enterContext(
            synthetic_registries(
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {**self.sites, cohesive.key: cohesive},
                },
            )
        )
        self._settle()

        groups = activity_owner.read_monster_activity(self.wilderness).groups
        group = groups[f"site:{COHESIVE_KEY}:0#0"]
        self.assertEqual(group.home_owner, ("site", COHESIVE_KEY))
        self.assertEqual(group.activity_key, GROUP_ACTIVITY)
        self.assertEqual(
            set(group.member_ids),
            {member.pk for member in _members(self.wilderness, cohesive)},
        )
        self.assertEqual(len(group.member_ids), 3)
        self.assertEqual(
            [key for key in groups if key.startswith(f"site:{COHESIVE_KEY}:")],
            [f"site:{COHESIVE_KEY}:0#0"],
        )

    @covers_requirement(
        "monster-field-activity::placements-form-movement-groups-from-their-binding-policy"
    )
    def test_a_stationary_site_binding_forms_one_group_per_member(self):
        self._settle()

        site = self.sites[GROUP_KEY]
        groups = activity_owner.read_monster_activity(self.wilderness).groups
        ids = [f"site:{GROUP_KEY}:0#{ordinal}" for ordinal in range(3)]
        self.assertEqual(
            [key for key in groups if key.startswith(f"site:{GROUP_KEY}:")], ids
        )
        for group_id in ids:
            with self.subTest(group=group_id):
                group = groups[group_id]
                self.assertEqual(len(group.member_ids), 1)
                self.assertEqual(group.home_owner, ("site", GROUP_KEY))
                self.assertEqual(group.activity_key, STATIONARY_ACTIVITY)
        self.assertEqual(
            {groups[group_id].member_ids[0] for group_id in ids},
            {member.pk for member in _members(self.wilderness, site)},
        )

    @covers_requirement(
        "monster-site-placement::composition-rows-resolve-one-effective-activity-binding"
    )
    def test_a_row_bound_site_forms_one_group_per_row_binding(self):
        self._settle()

        site = self.sites[MIXED_KEY]
        groups = activity_owner.read_monster_activity(self.wilderness).groups
        ids = [f"site:{MIXED_KEY}:0#{ordinal}" for ordinal in range(2)]
        self.assertEqual(
            [key for key in groups if key.startswith(f"site:{MIXED_KEY}:")], ids
        )
        cohesive, solitary = (groups[group_id] for group_id in ids)
        # The cohesive row keeps its pair together; the solitary row stays
        # independent. Both groups belong to the one site.
        self.assertEqual(cohesive.activity_key, GROUP_ACTIVITY)
        self.assertEqual(len(cohesive.member_ids), 2)
        self.assertEqual(solitary.activity_key, SOLITARY_ACTIVITY)
        self.assertEqual(len(solitary.member_ids), 1)
        for group in (cohesive, solitary):
            self.assertEqual(group.home_owner, ("site", MIXED_KEY))
        self.assertEqual(
            set(cohesive.member_ids) | set(solitary.member_ids),
            {member.pk for member in _members(self.wilderness, site)},
        )
        # Each group carries its own binding's decision interval, so the two
        # rows decide independently instead of sharing the site's schedule.
        self.assertEqual(
            cohesive.next_decision_tick,
            activity_owner.activity_decision_interval(GROUP_ACTIVITY),
        )
        self.assertEqual(
            solitary.next_decision_tick,
            activity_owner.activity_decision_interval(SOLITARY_ACTIVITY),
        )
        self.assertNotEqual(
            cohesive.next_decision_tick, solitary.next_decision_tick
        )
        # A due decision of the solitary group leaves its cohesive sibling
        # exactly where it was: the two rows decide from their own saved state.
        decision = activity_owner.plan_group_decision(
            self.wilderness, ids[1], tick=solitary.next_decision_tick
        )
        if decision.edge is not None:
            activity_owner.commit_group_decision(self.wilderness, decision)
        after = activity_owner.read_monster_activity(self.wilderness).groups
        self.assertEqual(after[ids[0]].position, cohesive.position)
        self.assertEqual(after[ids[0]].member_ids, cohesive.member_ids)
        self.assertEqual(after[ids[0]].sequence, cohesive.sequence)
        self.assertIsNone(after[ids[0]].journey_id)

    @covers_requirement(
        "monster-site-placement::composition-rows-resolve-one-effective-activity-binding"
    )
    def test_a_stationary_site_override_suppresses_every_row_binding(self):
        self._settle()

        groups = activity_owner.read_monster_activity(self.wilderness).groups
        ids = [f"site:{OVERRIDE_KEY}:0#{ordinal}" for ordinal in range(3)]
        self.assertEqual(
            [key for key in groups if key.startswith(f"site:{OVERRIDE_KEY}:")],
            ids,
        )
        for group_id in ids:
            with self.subTest(group=group_id):
                group = groups[group_id]
                self.assertEqual(len(group.member_ids), 1)
                self.assertEqual(group.home_owner, ("site", OVERRIDE_KEY))
                self.assertEqual(group.activity_key, STATIONARY_ACTIVITY)
        # Every group is stationary in its own binding, so even a due decision
        # neither departs nor lets a row binding move a member.
        for group_id in ids:
            due = groups[group_id].next_decision_tick
            decision = activity_owner.plan_group_decision(
                self.wilderness, group_id, tick=due
            )
            with self.subTest(decision=group_id):
                self.assertIsNone(decision.edge)
                self.assertEqual(decision.reason, activity_owner.STAY_STATIONARY)
                self.assertIsNone(
                    activity_owner.read_monster_activity(self.wilderness)
                    .groups[group_id]
                    .journey_id
                )

    @covers_requirement(
        "monster-site-placement::a-designated-site-individual-carries-an-authored-individual-name"
    )
    def test_a_labelled_site_names_its_individual_without_changing_identity(self):
        self._settle()

        labelled = self.sites[LABELLED_KEY]
        unlabelled = self.sites[UNLABELLED_KEY]
        labelled_members = _members(self.wilderness, labelled)
        unlabelled_members = _members(self.wilderness, unlabelled)
        self.assertEqual(len(labelled_members), 1)
        self.assertEqual(len(unlabelled_members), 1)
        named, plain = labelled_members[0], unlabelled_members[0]

        self.assertEqual(named.individual_name, LABEL)
        self.assertEqual(named.key, LABEL)
        self.assertIsNone(plain.individual_name)
        self.assertNotEqual(plain.key, LABEL)
        self.assertEqual(named.species_key, plain.species_key)
        self.assertEqual(named.variant_key, plain.variant_key)
        self.assertEqual(named.db.site_key, LABELLED_KEY)
        self.assertEqual(plain.db.site_key, UNLABELLED_KEY)

        groups = activity_owner.read_monster_activity(self.wilderness).groups
        named_group = groups[f"site:{LABELLED_KEY}:0#0"]
        plain_group = groups[f"site:{UNLABELLED_KEY}:0#0"]
        self.assertEqual(named_group.home_owner, ("site", LABELLED_KEY))
        self.assertEqual(plain_group.home_owner, ("site", UNLABELLED_KEY))
        self.assertEqual(named_group.member_ids, (named.pk,))
        self.assertEqual(plain_group.member_ids, (plain.pk,))
        self.assertEqual(named_group.activity_key, plain_group.activity_key)

    @covers_requirement(
        "monster-site-placement::a-designated-site-individual-carries-an-authored-individual-name"
    )
    def test_a_recovered_labelled_individual_keeps_the_label_and_a_new_identity(self):
        ward = MonsterSite(
            "t_probe_labelled_camp",
            "camp",
            self.region,
            PROBE,
            SOLO,
            None,
            1,
            False,
            HOUR,
            individual_name_zh=LABEL,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {ward.key: ward},
                },
            )
        )
        self._settle()
        first = _members(self.wilderness, ward)
        self.assertEqual(len(first), 1)
        first_pk = first[0].pk
        self.assertEqual(first[0].key, LABEL)
        first[0].traits.hp.current = 0
        self.clock.advance(60, AdvanceSource.SKIP, [])
        self.assertEqual(
            site_state(ward.key, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )

        self.assertTrue(
            settle_site_recovery(ward.key, 60 + HOUR, wilderness=self.wilderness)
        )

        recovered = _members(self.wilderness, ward)
        self.assertEqual(len(recovered), 1)
        # A recovery is a new persistent identity that keeps the authored
        # display label; identity stays keyed by species, variant and site.
        self.assertNotEqual(recovered[0].pk, first_pk)
        self.assertEqual(recovered[0].key, LABEL)
        self.assertEqual(recovered[0].individual_name, LABEL)
        self.assertEqual(recovered[0].db.site_key, ward.key)
        group = activity_owner.read_monster_activity(self.wilderness).groups[
            f"site:{ward.key}:1#0"
        ]
        self.assertEqual(group.home_owner, ("site", ward.key))
        self.assertEqual(group.member_ids, (recovered[0].pk,))

    @covers_requirement(
        "monster-field-activity::placements-form-movement-groups-from-their-binding-policy"
    )
    def test_a_failed_second_unit_restores_the_site_and_every_member(self):
        states_before = self.wilderness.db.monster_sites
        coordinates_before = dict(self.wilderness.db.itemcoordinates)
        activity_before = dict(self.wilderness.db.monster_activity)
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))
        room = (self.wilderness.db.rooms or {})[PROBE]
        contents_before = {obj.pk for obj in room.contents}

        real_register = monster_sites.register_explicit_group

        def flaky(wilderness, individuals, coordinates, **kwargs):
            if (
                kwargs["operation_id"] == f"site:{GROUP_KEY}:0"
                and kwargs["ordinal"] == 1
            ):
                raise RuntimeError("injected second unit failure")
            return real_register(wilderness, individuals, coordinates, **kwargs)

        with patch.object(
            monster_sites, "register_explicit_group", side_effect=flaky
        ):
            with self.assertRaises(RuntimeError):
                self.clock.advance(60, AdvanceSource.SKIP, [])

        self.assertEqual(self.wilderness.db.monster_sites, states_before)
        self.assertEqual(dict(self.wilderness.db.itemcoordinates), coordinates_before)
        self.assertEqual(dict(self.wilderness.db.monster_activity), activity_before)
        self.assertEqual({obj.pk for obj in room.contents}, contents_before)
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )
        for site in self.sites.values():
            self.assertEqual(_members(self.wilderness, site), ())

        # A retry populates every site, each stationary member with its own
        # group and no partial survivor of the rolled-back pass.
        self._settle()
        for key, site in self.sites.items():
            with self.subTest(site=key):
                self.assertEqual(len(_members(self.wilderness, site)), site.capacity)
        groups = activity_owner.read_monster_activity(self.wilderness).groups
        self.assertEqual(
            len([key for key in groups if key.startswith(f"site:{GROUP_KEY}:")]), 3
        )

    @covers_requirement("regional-population::shared-population-seed-and-explicit-registrations-are-owner-supplied")
    def test_single_registration_keeps_its_explicit_identity_and_presence_evidence(self):
        self._settle()
        individual = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        register_explicit_individual(
            self.wilderness,
            individual,
            PROBE,
            tick=0,
            owner_kind="explicit",
            owner_key="gm:1",
            activity_key=STATIONARY_ACTIVITY,
        )

        operation_id = f"explicit:{PROBE[0]}:{PROBE[1]}:{individual.pk}"
        group = activity_owner.read_monster_activity(self.wilderness).groups[
            f"{operation_id}#0"
        ]
        self.assertEqual(group.home_owner, ("explicit", "gm:1"))
        self.assertEqual(group.member_ids, (individual.pk,))
        transitions = [
            entry
            for entry in read_population_timeline(self.wilderness).transitions
            if entry.individual_id == individual.pk
        ]
        self.assertEqual([entry.source_id for entry in transitions], [operation_id])

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_the_saved_occurrence_reproduces_its_group_and_ignores_the_retry_tick(
        self,
    ):
        # A variable-range composition makes a wrong occurrence input visible.
        selections = {
            sample_composition_counts(
                FLOCK, seed=seed, stream_key=GROUP_KEY, sequence=0, budget=2
            )
            for seed in range(12)
        }
        self.assertGreater(len(selections), 1, "the sampler must read its seed")
        self.assertEqual(
            sample_composition_counts(
                FLOCK, seed=5, stream_key=GROUP_KEY, sequence=0, budget=2
            ),
            sample_composition_counts(
                FLOCK, seed=5, stream_key=GROUP_KEY, sequence=0, budget=2
            ),
        )

        # The real owner replays its occurrence after the record and rows are
        # lost (an interrupted attempt leaves exactly that state). A variable
        # range makes a tick-dependent or seed-ignoring sample observable.
        flock = MonsterSite(
            "t_probe_flock_site",
            "encounter",
            self.region,
            PROBE,
            FLOCK,
            STATIONARY_ACTIVITY,
            3,
            True,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {flock.key: flock},
                },
            )
        )
        self._settle()
        first_state = site_state(flock.key, wilderness=self.wilderness)
        first = sorted(
            member.variant_key for member in _members(self.wilderness, flock)
        )
        self.assertIn(len(first), (1, 2, 3))
        for member in list(_members(self.wilderness, flock)):
            self.wilderness.db.itemcoordinates.pop(member, None)
            member.delete()
        # The lost attempt loses its movement groups with its record: the
        # owning transaction would have rolled both back together.
        for group_id in [
            group_id
            for group_id in activity_owner.read_monster_activity(
                self.wilderness
            ).groups
            if group_id.startswith(f"site:{flock.key}:")
        ]:
            activity_owner.release_group(self.wilderness, group_id)
        states = {
            key: dict(value)
            for key, value in self.wilderness.db.monster_sites.items()
        }
        states.pop(flock.key, None)
        self.wilderness.db.monster_sites = states

        self._settle(end_tick=10 * HOUR)

        second_state = site_state(flock.key, wilderness=self.wilderness)
        second = sorted(
            member.variant_key for member in _members(self.wilderness, flock)
        )
        self.assertEqual(second, first)
        self.assertEqual(second_state.seed, first_state.seed)
        self.assertEqual(second_state.generation_sequence, 0)

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_a_living_absent_member_prevents_false_clearing(self):
        self._settle()
        nest = self.sites[NEST_KEY]
        members = _members(self.wilderness, nest)
        absent = members[0]
        for other in members[1:]:
            other.traits.hp.current = 0
        # Temporarily unlocated and unregistered but still alive and owned.
        self.wilderness.db.itemcoordinates.pop(absent, None)
        absent.location = None

        self.clock.advance(60, AdvanceSource.SKIP, [])

        state = site_state(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        self.assertIn(absent.pk, state.member_ids)
        self.assertEqual(
            [member.pk for member in _living(self.wilderness, nest)], [absent.pk]
        )
        self.assertEqual(
            sorted(member.pk for member in _members(self.wilderness, nest)),
            sorted(member.pk for member in members),
        )

        absent.traits.hp.current = 0
        self.clock.advance(60, AdvanceSource.SKIP, [])
        self.assertEqual(
            site_state(NEST_KEY, wilderness=self.wilderness).state,
            SITE_STATE_CLEARED,
        )

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_a_one_shot_site_is_never_refilled_by_a_regional_deficit_wave(self):
        nest = self.sites[NEST_KEY]
        zone = EcologyZone(
            "t_probe_zone",
            self.region,
            ((PROBE[0] - 2, PROBE[0] + 2, PROBE[1] - 2, PROBE[1] + 2),),
            (WeightedComposition(SOLO, 1),),
            4,
            12,
            3,
            3600,
            600,
            3,
        )
        self.assertTrue(
            _eligible_birth_cells(zone), "the probe must stay an eligible cell"
        )
        with (
            patch.object(monster_sites, "MONSTER_SITE_REGISTRY", {NEST_KEY: nest}),
            patch.object(
                regional_population,
                "ECOLOGY_ZONE_REGISTRY",
                {zone.key: zone},
            ),
        ):
            # Entering the probe already reconciled its ambient population, so
            # clear it first: the wave below must start from a real deficit.
            for living in list(Monster.objects.all()):
                if _stored_hp(living) > 0:
                    living.traits.hp.current = 0
            ambient = initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)
            self.assertTrue(
                ambient,
                (
                    plan_population_wave(self.wilderness, zone.key, tick=0).blocked_reason,
                    population_counts(self.wilderness, zone.key).local_ids,
                ),
            )
            self._settle()
            self.assertEqual(len(_members(self.wilderness, nest)), nest.capacity)
            defeated = self._defeat(nest)
            self.clock.advance(60, AdvanceSource.SKIP, [])
            self.assertEqual(
                site_state(NEST_KEY, wilderness=self.wilderness).state,
                SITE_STATE_CLEARED,
            )
            # Create a genuine local deficit, then run one ordinary wave.
            for pk in ambient:
                member = Monster.objects.get(pk=pk)
                member.traits.hp.current = 0
            wave = plan_population_wave(self.wilderness, zone.key, tick=120)
            self.assertFalse(wave.is_blocked, wave.blocked_reason)
            created = commit_population_wave(self.wilderness, wave)
            self.assertTrue(created)

        state = site_state(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(state.state, SITE_STATE_CLEARED)
        self.assertEqual(state.member_ids, defeated)
        self.assertEqual(_living(self.wilderness, nest), ())
        for pk in created:
            self.assertNotEqual(Monster.objects.get(pk=pk).db.site_key, NEST_KEY)

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_an_explicit_site_inside_a_settlement_ring_survives_maintenance(self):
        cell = _buffer_cell_inside_a_settlement_ring()
        region = region_for_coordinates(*cell)
        self.assertTrue(is_valid_wilderness_cell(cell))
        self.assertEqual(
            _eligible_birth_cells(_cell_zone(cell, region)),
            (),
            "the settlement ring must exclude ordinary births at this cell",
        )
        # The control is the same real geometry admitting an unrestrained cell:
        # the empty result above is the exclusion, not unusable test geometry.
        self.assertTrue(_eligible_birth_cells(_cell_zone(PROBE, self.region)))

        site = MonsterSite(
            "t_probe_ring_site",
            "encounter",
            region,
            cell,
            SOLO,
            STATIONARY_ACTIVITY,
            1,
            True,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {site.key: site},
                },
            )
        )
        self._settle()
        members = _members(self.wilderness, site)
        self.assertEqual(len(members), 1)
        self.assertEqual(self.wilderness.db.itemcoordinates[members[0]], cell)

        # Ordinary maintenance never removes or moves the explicit placement,
        # although automatic birth geometry can reach none of those cells.
        from evennia.utils.create import create_object

        ordinary = create_object(Monster, key="t_ordinary_witness")
        ordinary.threat_tier = _WITNESS_TIER
        ordinary.apply_monster_tier("floor")
        ordinary.traits.hp.current = 5
        self.wilderness.db.itemcoordinates[ordinary] = cell
        self._settle(end_tick=HOUR)

        self.assertEqual(
            [member.pk for member in _members(self.wilderness, site)],
            [members[0].pk],
        )
        self.assertEqual(self.wilderness.db.itemcoordinates[members[0]], cell)
        self.assertEqual(
            site_state(site.key, wilderness=self.wilderness).state,
            SITE_STATE_POPULATED,
        )

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_manual_excess_counts_against_ordinary_ceilings_without_culling(self):
        zone = EcologyZone(
            "t_probe_zone",
            self.region,
            ((PROBE[0] - 2, PROBE[0] + 2, PROBE[1] - 2, PROBE[1] + 2),),
            (WeightedComposition(SOLO, 1),),
            4,
            12,
            3,
            3600,
            600,
            3,
        )
        with patch.object(
            regional_population, "ECOLOGY_ZONE_REGISTRY", {zone.key: zone}
        ):
            initialize_zone(self.wilderness, zone.key, seed=SEED, tick=0)
            self._settle()
            counts = population_counts(self.wilderness, zone.key)
            site_ids = {
                member.pk
                for site in self.sites.values()
                for member in _members(self.wilderness, site)
            }
            self.assertLessEqual(site_ids, set(counts.local_ids))
            self.assertLessEqual(site_ids, set(counts.cell_ids[PROBE]))
            plan = plan_population_wave(self.wilderness, zone.key, tick=60)
            self.assertTrue(plan.is_blocked)
            self.assertEqual(
                plan.blocked_reason, BLOCKED_LOCAL_SATISFIED
            )

        for key, site in self.sites.items():
            with self.subTest(site=key):
                self.assertEqual(
                    len(_members(self.wilderness, site)), site.capacity
                )
                self.assertEqual(
                    site_state(key, wilderness=self.wilderness).state,
                    SITE_STATE_POPULATED,
                )

    def test_an_unreadable_record_answers_a_named_verdict_and_refuses_work(self):
        self._settle()
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))
        base = {
            key: dict(value)
            for key, value in self.wilderness.db.monster_sites.items()
        }
        nest_member = base[NEST_KEY]["member_ids"][0]
        corruptions = {
            "non-sequence identities": lambda record: record.update(
                member_ids="not-a-list"
            ),
            # Every lawful composition has positive membership, so an empty
            # identity list is corrupt, never an empty site.
            "empty identities": lambda record: record.update(member_ids=[]),
            "duplicate identities": lambda record: record.update(
                member_ids=[nest_member, nest_member]
            ),
            "unknown lifecycle state": lambda record: record.update(state="sleeping"),
            "populated record with a clearing tick": lambda record: record.update(
                cleared_at_tick=5
            ),
        }
        for name, corrupt in corruptions.items():
            with self.subTest(corruption=name):
                states = {key: dict(value) for key, value in base.items()}
                corrupt(states[NEST_KEY])
                self.wilderness.db.monster_sites = states

                read = site_living_members(NEST_KEY, wilderness=self.wilderness)

                self.assertFalse(read.available)
                self.assertEqual(read.reason, SITE_READ_STATE_UNREADABLE)
                self.assertEqual(read.members, ())
                with self.assertRaises(MalformedPopulationState):
                    self._settle()
                self.assertEqual(
                    sorted(Monster.objects.values_list("pk", flat=True)),
                    monsters_before,
                )
                # The corrupt value is exactly what remains: nothing
                # reinterpreted it.
                self.assertEqual(
                    {
                        key: dict(value)
                        for key, value in self.wilderness.db.monster_sites.items()
                    },
                    states,
                )

        # A corrupt state-map container is answered by the same verdict.
        self.wilderness.db.monster_sites = "not-a-map"
        read = site_living_members(NEST_KEY, wilderness=self.wilderness)
        self.assertEqual(read.reason, SITE_READ_STATE_UNREADABLE)
        with self.assertRaises(MalformedPopulationState):
            self._settle()
        self.wilderness.db.monster_sites = base
