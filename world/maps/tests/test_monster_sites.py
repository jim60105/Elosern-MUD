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
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
    composition_variant_keys,
    variant_species_key,
)
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps import monster_sites
from world.maps import regional_population
from world.tests.geography_fixture import sync_test_wilderness
from world.maps.geography import current as current_geography
from world.maps.population_geometry import (
    INHABITED_SETTLEMENT_KINDS,
    eligible_birth_cells,
)
from world.maps.monster_sites import (
    SITE_STAGE_KIND,
    SITE_STATE_CLEARED,
    SITE_STATE_POPULATED,
    SITE_READ_CLEARED,
    SITE_READ_STATE_UNREADABLE,
    SITE_READ_UNKNOWN_SITE,
    SITE_READ_UNPOPULATED,
    SITE_READ_WORLD_UNAVAILABLE,
    settle_monster_sites,
    settle_site_recovery,
    site_living_members,
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
    is_valid_wilderness_cell,
    region_for_coordinates,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.maps.regional_population import (
    BLOCKED_LOCAL_SATISFIED,
    MalformedPopulationState,
    PopulationSeedUninitialized,
    commit_population_wave,
    initialize_zone,
    initialize_population_seed,
    plan_population_wave,
    population_counts,
    sample_composition_counts,
)
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
PROBE = (500, 700)
NEST_KEY = "t_probe_nest"
CAMP_KEY = "t_probe_camp"
GROUP_KEY = "t_probe_group"
STRAY_KEY = "t_probe_stray"
HOUR = 3600
SEED = 11

PAIR = "t_probe_pair"
GROUP = "t_probe_group_composition"
SOLO = "t_probe_solo"
FLOCK = "t_probe_flock"

#: One solitary composition, one same-variant group, one mixed pair and one
#: variable-range group, all built from the kit's synthetic variants. The
#: variable range is what makes a wrong occurrence input observable: a fixed
#: group would look deterministic even if the sampler ignored its seed.
COMPOSITIONS = {
    PAIR: EncounterComposition(
        PAIR,
        (
            CompositionMember(ORDINARY, 1, 1),
            CompositionMember(STRONGER, 1, 1),
        ),
    ),
    GROUP: EncounterComposition(
        GROUP,
        (
            CompositionMember(ORDINARY, 2, 2),
            CompositionMember(STRONGER, 1, 1),
        ),
    ),
    SOLO: EncounterComposition(SOLO, (CompositionMember(STRONGER, 1, 1),)),
    FLOCK: EncounterComposition(FLOCK, (CompositionMember(ORDINARY, 1, 2),)),
}


def _declared_map_id():
    """One live registry map id; these tests never need grid gate provisioning."""

    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    entry = next(iter(WILDERNESS_ENTRY_REGISTRY.values()))
    return entry.gates[0].destination.map_id


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


def _cell_zone(cell: tuple[int, int], region: str) -> EcologyZone:
    """One synthetic ecology zone covering exactly ``cell``."""
    x, y = cell
    return EcologyZone(
        "t_probe_zone",
        region,
        ((x, x, y, y),),
        (WeightedComposition(SOLO, 1),),
        1,
        1,
        3,
        3600,
        600,
        3,
    )


def _eligible_birth_cells(zone: EcologyZone) -> tuple[tuple[int, int], ...]:
    """The ordinary birth cells of ``zone`` in the published test world."""
    return eligible_birth_cells(
        zone,
        geography=current_geography(),
        entries=WILDERNESS_ENTRY_REGISTRY,
        policies={},
    )


def _inhabited_settlement_cells():
    """Every published cell of an inhabited settlement (footprint or anchor)."""
    geography = current_geography()
    for anchor_key, anchor in geography.anchors.items():
        if anchor.kind not in INHABITED_SETTLEMENT_KINDS:
            continue
        entry = WILDERNESS_ENTRY_REGISTRY.get(anchor_key)
        if entry is not None and entry.footprint_cells:
            yield from sorted(entry.footprint_cells)
            continue
        published = geography.anchor_geography.get(anchor_key)
        if published is not None and published.cell is not None:
            yield published.cell


def _buffer_cell_inside_a_settlement_ring() -> tuple[int, int]:
    """A valid wild cell that ordinary birth geometry excludes.

    The cell is one Chebyshev step outside a published inhabited settlement, so
    it is lawful explicit-placement ground while the generic settlement buffer
    keeps it out of automatic birth geometry.
    """
    for settlement_cell in _inhabited_settlement_cells():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                cell = (settlement_cell[0] + dx, settlement_cell[1] + dy)
                if not is_valid_wilderness_cell(cell):
                    continue
                region = region_for_coordinates(*cell)
                if _eligible_birth_cells(_cell_zone(cell, region)):
                    continue
                return cell
    raise AssertionError("no excluded-but-valid wilderness cell was published")


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
                PAIR,
                2,
                True,
            ),
            CAMP_KEY: MonsterSite(
                CAMP_KEY,
                "camp",
                self.region,
                PROBE,
                PAIR,
                2,
                False,
                HOUR,
            ),
            GROUP_KEY: MonsterSite(
                GROUP_KEY,
                "encounter",
                self.region,
                PROBE,
                GROUP,
                3,
                True,
            ),
            STRAY_KEY: MonsterSite(
                STRAY_KEY,
                "stray",
                self.region,
                PROBE,
                SOLO,
                1,
                True,
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
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": self.sites,
                },
            )
        )
        from world.maps.population_lifecycle import register_regional_population

        register_regional_population()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        # The site owner derives each site's occurrence from the one explicit
        # world seed; a world without it refuses instead of guessing.
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.clock = get_world_clock()

    # -- helpers ------------------------------------------------------------

    def _settle(self, end_tick: int = 0):
        with self.captureOnCommitCallbacks(execute=True):
            return settle_monster_sites(0, end_tick)

    def _defeat(self, site: MonsterSite) -> tuple[int, ...]:
        """Defeat every member and record each committed loss occurrence."""
        from world.maps import regional_population
        from world.rules.clock import read_world_clock

        clock = read_world_clock()
        tick = 0 if clock is None else clock.tick
        defeated = []
        for member in _members(self.wilderness, site):
            before = regional_population.presence_of(self.wilderness, member)
            member.traits.hp.current = 0
            defeated.append(member.pk)
            regional_population.record_population_transition(
                self.wilderness,
                regional_population.PopulationTransition(
                    source_id=f"test-defeat:{member.pk}",
                    individual_id=int(member.pk),
                    occurred_tick=tick,
                    before=before,
                    after=regional_population.presence_of(
                        self.wilderness, member, alive=False
                    ),
                ),
            )
        return tuple(defeated)

    # -- population ---------------------------------------------------------

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::placement-decisions-are-boundary-observable-through-the-facade")
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

    # -- complete compositions and manual exceptions -----------------------

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
            "t_probe_flock_site", "encounter", self.region, PROBE, FLOCK, 3, True
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
            "t_probe_ring_site", "encounter", region, cell, SOLO, 1, True
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
        ensure_population(self.wilderness, cell)
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

    # -- one-shot -----------------------------------------------------------

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

        # A full game day later, on re-entry, and on the startup sync path the
        # one-shot site creates nothing: the defeated rows stay dead in place.
        self.clock.advance(86400, AdvanceSource.SKIP, [])
        self.wilderness.mapprovider.at_prepare_room(PROBE, self.char1, self.room)
        sync_test_wilderness((_declared_map_id(),))
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
        sync_test_wilderness((_declared_map_id(),))
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
            "t_probe_herd", "camp", self.region, PROBE, FLOCK, 3, False, HOUR
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

    # -- ownership domains --------------------------------------------------

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
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

    # -- the quest layer's binding source ----------------------------------

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
        ambient.db.population_key = _population_key(*PROBE)
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


class MonsterSiteStageWithoutWorldTests(EvenniaTest):
    """The stage is silent while no wilderness script exists."""

    def test_settlement_and_contract_are_absent_tolerant(self):
        from world.maps.population_lifecycle import register_regional_population

        register_regional_population()
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

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_the_read_refuses_when_no_world_is_provisioned(self):
        # Refusing is the read's answer, not an exception, and it provisions
        # nothing: no wilderness script may appear because a quest asked.
        self.assertFalse(search_script(WILDERNESS_NAME))

        read = site_living_members("t_absent_site")

        self.assertFalse(read.available)
        self.assertEqual(read.reason, SITE_READ_WORLD_UNAVAILABLE)
        self.assertEqual(read.members, ())
        self.assertIsNone(read.site)
        self.assertIsNone(read.state)
        self.assertFalse(search_script(WILDERNESS_NAME))


class MonsterSiteWithoutWorldSeedTests(EvenniaTest):
    """A world that never initialized its seed refuses before any site write."""

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_first_population_refuses_without_an_explicit_world_seed(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
        )

        site = MonsterSite(
            "t_seedless_site", "nest", "t_bramble_wold", (5, 5), SOLO, 1, True
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

        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))

        with self.assertRaises(PopulationSeedUninitialized):
            with self.captureOnCommitCallbacks(execute=True):
                settle_monster_sites(0, 0)

        self.assertIsNone(site_state(site.key, wilderness=wilderness))
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )


class SiteRowVocabularyTests(EvenniaTest):
    """The authored vocabulary the owner reads is the registry's own."""

    def test_the_owner_reads_the_registry_instead_of_a_local_copy(self):
        site = MonsterSite(
            "t_vocabulary_site",
            "boss_site",
            region_for_coordinates(*PROBE),
            PROBE,
            SOLO,
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
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {site.key: site},
                },
            )
        )
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(wilderness, seed=SEED, tick=0)
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
        self.assertEqual(
            members[0].variant_key,
            composition_variant_keys(COMPOSITIONS[SOLO])[0],
        )
