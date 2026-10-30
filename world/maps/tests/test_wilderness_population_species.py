"""Behavior tests for the species-bearing ambient branch (monster-site-placement).

The ambient rows are file-local synthetic fixtures injected through the
synthetic test-data kit's ``extra=`` seam and the individuals' identities come
from the kit's synthetic species/variant catalogs, so no shipped placement,
species, or variant key is named. Every region key is read from the live
terrain model at runtime.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.lore.monster_placement import AmbientPlacementRule, variant_species_key
import world.maps.wilderness_population as wilderness_population_module
from world.maps.wilderness_population import (
    _coordinate_hash,
    _population_key,
    _stored_hp,
    ambient_observation_key,
    ambient_variant_for_slot,
    ensure_population,
    species_rule_for_coordinates,
    population_view,
    ambient_population_decision,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    is_valid_wilderness_cell,
    region_for_coordinates,
)
from world.maps import wilderness_provider
from world.rules.combat_session import engage
from world.rules.combat_session import clear_session
from world.rules.monster_individual import construct_species_individual
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import publish_shipped_geography
from world.tests.synthetic_data import (
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    synthetic_registries,
)

publish_shipped_geography()
CAPITAL_ENTRY_XY = wilderness_population_module.capital_entry_xy()

_VARIANTS = tuple(SYNTH_MONSTER_VARIANTS)
ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]
_WITNESS_TIER = next(iter(SYNTH_MONSTER_TIERS))

#: A walkable eastern-plain wild cell, outside every anchor footprint and far
#: from the contract-pinned hunting band.
PROBE = (2000, 1000)
BAND_RADIUS = 3


def _in_band(cell: tuple[int, int]) -> bool:
    return max(
        abs(cell[0] - CAPITAL_ENTRY_XY[0]), abs(cell[1] - CAPITAL_ENTRY_XY[1])
    ) <= BAND_RADIUS


def _region_cells(region: str):
    """Walkable cells of ``region`` over its authored search window, in order."""
    x_min, x_max, y_min, y_max = wilderness_provider.region_search_boxes()[region]
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            cell = (x, y)
            if is_valid_wilderness_cell(cell) and region_for_coordinates(x, y) == region:
                yield cell


def _first_cell(region: str, *, inside_band: bool) -> tuple[int, int]:
    """A walkable cell of ``region`` inside or outside the hunting band.

    Enumerated over the region's authored search window, so the fixture lookup
    stays a bounded local search rather than a frame sweep.
    """
    for cell in _region_cells(region):
        if _in_band(cell) is inside_band:
            return cell
    raise AssertionError(f"no walkable {region} cell with inside_band={inside_band}")


def _cell_outside_every_rule(rules) -> tuple[int, int]:
    """A walkable cell whose region carries no authored rule."""
    for region, (x_min, x_max, y_min, y_max) in wilderness_provider.region_search_boxes().items():
        if region in rules:
            continue
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                cell = (x, y)
                if not is_valid_wilderness_cell(cell) or _in_band(cell):
                    continue
                if region_for_coordinates(x, y) == region:
                    return cell
    raise AssertionError("every region carries an authored rule")


def _species_members(wilderness, coordinates: tuple[int, int]) -> tuple[Monster, ...]:
    marker = _population_key(*coordinates)
    return tuple(
        member
        for member in wilderness.get_objs_at_coordinates(coordinates)
        if isinstance(member, Monster)
        and member.db.population_key == marker
        and member.species_key is not None
    )


class AmbientSpeciesReconciliationTests(BattlefieldIsolation, EvenniaTest):
    """The species branch: selection, capacity, drift, and owner immunity."""

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        self.region = region_for_coordinates(*PROBE)
        self.band_region = region_for_coordinates(*CAPITAL_ENTRY_XY)
        self.rule = AmbientPlacementRule(
            self.region, (ORDINARY, STRONGER), 2, 3, 1
        )
        self.band_rule = AmbientPlacementRule(
            self.band_region, (ORDINARY,), 1, 1
        )
        self.rules = {self.region: self.rule, self.band_region: self.band_rule}
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "ambient_placements",
                extra={"ambient_placements": self.rules},
            )
        )
        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location

    def _expected_variants(self) -> list[str]:
        return sorted(
            ambient_variant_for_slot(self.rule, *PROBE, slot)
            for slot in range(min(self.rule.quantity, self.rule.capacity))
        )

    # -- population ---------------------------------------------------------

    def test_a_covered_coordinate_is_populated_from_the_authored_variants(self):
        members = _species_members(self.wilderness, PROBE)
        self.assertEqual(len(members), self.rule.quantity)
        self.assertEqual(
            sorted(member.variant_key for member in members), self._expected_variants()
        )
        marker = _population_key(*PROBE)
        for member in members:
            self.assertEqual(member.db.population_key, marker)
            self.assertEqual(
                member.species_key, variant_species_key(member.variant_key)
            )
            self.assertGreater(_stored_hp(member), 0)
            self.assertEqual(self.wilderness.db.itemcoordinates[member], PROBE)
            self.assertIs(member.location, self.room)
        # The one branch that covers this coordinate is the species branch: no
        # tier-example row (an identity-less marker row) exists here.
        identity_less = [
            member
            for member in self.wilderness.get_objs_at_coordinates(PROBE)
            if isinstance(member, Monster)
            and member.db.population_key == marker
            and member.species_key is None
        ]
        self.assertEqual(identity_less, [])

    def test_repeated_reconciliation_is_idempotent_and_never_exceeds_capacity(self):
        first = sorted(member.pk for member in _species_members(self.wilderness, PROBE))
        ensure_population(self.wilderness, PROBE)
        second = sorted(member.pk for member in _species_members(self.wilderness, PROBE))
        self.assertEqual(first, second)
        self.assertEqual(len(second), self.rule.quantity)
        self.assertLessEqual(len(second), self.rule.capacity)

    def test_a_dead_individual_is_replaced_by_a_fresh_one(self):
        members = _species_members(self.wilderness, PROBE)
        defeated = members[0]
        defeated_variant = defeated.variant_key
        defeated.traits.hp.current = 0

        ensure_population(self.wilderness, PROBE)

        remaining = _species_members(self.wilderness, PROBE)
        self.assertEqual(len(remaining), self.rule.quantity)
        self.assertNotIn(defeated.pk, [member.pk for member in remaining])
        self.assertIn(members[1].pk, [member.pk for member in remaining])
        replacement = next(
            member
            for member in remaining
            if member.variant_key == defeated_variant
        )
        self.assertNotEqual(replacement.pk, defeated.pk)

    def test_living_individuals_are_never_deleted_to_make_room(self):
        surplus = construct_species_individual(
            variant_species_key(ORDINARY), ORDINARY
        )
        surplus.db.population_key = _population_key(*PROBE)
        self.wilderness.db.itemcoordinates[surplus] = PROBE
        surplus.location = self.room
        before = sorted(
            member.pk for member in _species_members(self.wilderness, PROBE)
        )
        self.assertEqual(len(before), self.rule.quantity + 1)

        ensure_population(self.wilderness, PROBE)

        after = sorted(member.pk for member in _species_members(self.wilderness, PROBE))
        self.assertEqual(after, before)

    def test_a_living_drifted_individual_still_bounds_the_pass_by_quantity(self):
        # An authoring change can leave a living owned individual outside the
        # selected variant multiset. It is preserved, and the authored quantity
        # is still a ceiling: the pass adds nothing to exceed it, even though
        # the capacity alone would allow one more.
        narrow = AmbientPlacementRule(self.region, (ORDINARY,), 1, 2)
        self.enterContext(
            synthetic_registries(
                "ambient_placements",
                extra={"ambient_placements": {self.region: narrow}},
            )
        )
        # One living owned individual, whose variant the narrowed rule no
        # longer selects.
        members = _species_members(self.wilderness, PROBE)
        spare = members[1]
        self.wilderness.db.itemcoordinates.pop(spare, None)
        spare.delete()
        drifted = members[0]
        drifted.variant_key = STRONGER
        drifted.species_key = variant_species_key(STRONGER)
        before = sorted(
            member.pk for member in _species_members(self.wilderness, PROBE)
        )
        self.assertEqual(len(before), 1)

        ensure_population(self.wilderness, PROBE)

        after = sorted(member.pk for member in _species_members(self.wilderness, PROBE))
        self.assertEqual(after, before)

    # -- determinism --------------------------------------------------------

    @covers_requirement(
        "wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map"
    )
    def test_the_selection_is_a_pure_function_of_coordinates_and_rule(self):
        for slot in range(4):
            with self.subTest(slot=slot):
                expected = self.rule.variant_keys[
                    (_coordinate_hash(*PROBE) + self.rule.selection_salt + slot)
                    % len(self.rule.variant_keys)
                ]
                self.assertEqual(
                    ambient_variant_for_slot(self.rule, *PROBE, slot), expected
                )
                self.assertEqual(
                    ambient_variant_for_slot(self.rule, *PROBE, slot), expected
                )
        # The authored hash inputs are load-bearing: another coordinate and
        # another salt select from the same set without repeating the first
        # coordinate's answer in every slot.
        other = ambient_variant_for_slot(self.rule, PROBE[0] + 1, PROBE[1], 0)
        self.assertIn(other, self.rule.variant_keys)
        self.assertEqual(
            ambient_variant_for_slot(
                AmbientPlacementRule(self.region, (ORDINARY, STRONGER), 1, 1, 0),
                *PROBE,
                0,
            ),
            ORDINARY,
        )

    def test_each_coordinate_belongs_to_exactly_one_ambient_branch(self):
        # The species rules cover the probe's region ...
        self.assertIs(species_rule_for_coordinates(*PROBE), self.rule)
        # ... but never the contract-pinned hunting band, even though the
        # band's own region carries an authored rule.
        band_region_cell = _first_cell(self.band_region, inside_band=False)
        self.assertIs(
            species_rule_for_coordinates(*band_region_cell), self.band_rule
        )
        for dx in range(-BAND_RADIUS, BAND_RADIUS + 1):
            for dy in range(-BAND_RADIUS, BAND_RADIUS + 1):
                cell = (CAPITAL_ENTRY_XY[0] + dx, CAPITAL_ENTRY_XY[1] + dy)
                with self.subTest(cell=cell):
                    self.assertIsNone(species_rule_for_coordinates(*cell))
        # ... and a region with no authored rule keeps the tier-example branch.
        uncovered = _cell_outside_every_rule(self.rules)
        self.assertIsNone(species_rule_for_coordinates(*uncovered))
        self.assertNotEqual(
            region_for_coordinates(*uncovered), region_for_coordinates(*PROBE)
        )

    # -- ownership domains --------------------------------------------------

    def test_foreign_and_site_owned_monsters_are_untouched(self):
        foreign = create_object(Monster, key="t_foreign_ambient_witness")
        foreign.threat_tier = _WITNESS_TIER
        foreign.apply_monster_tier("floor")
        foreign.traits.hp.current = 7
        self.wilderness.db.itemcoordinates[foreign] = PROBE
        other_site = create_object(Monster, key="t_site_ambient_witness")
        other_site.threat_tier = _WITNESS_TIER
        other_site.apply_monster_tier("floor")
        other_site.db.site_key = "t_somewhere_else"
        other_site.traits.hp.current = 5
        self.wilderness.db.itemcoordinates[other_site] = PROBE
        elsewhere = create_object(Monster, key="t_other_cell_witness")
        elsewhere.threat_tier = _WITNESS_TIER
        elsewhere.apply_monster_tier("floor")
        elsewhere.db.population_key = _population_key(PROBE[0] + 1, PROBE[1])
        elsewhere.traits.hp.current = 3
        self.wilderness.db.itemcoordinates[elsewhere] = PROBE

        ensure_population(self.wilderness, PROBE)

        witnesses = (
            (foreign, 7, None),
            (other_site, 5, None),
            (elsewhere, 3, _population_key(PROBE[0] + 1, PROBE[1])),
        )
        for probe, hp, marker in witnesses:
            with self.subTest(monster=probe.key):
                self.assertEqual(self.wilderness.db.itemcoordinates[probe], PROBE)
                self.assertEqual(probe.traits.hp.current, hp)
                self.assertEqual(probe.db.population_key, marker)
                self.assertNotEqual(marker, _population_key(*PROBE))

    def test_an_active_combat_session_freezes_the_species_pass(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        victim = _species_members(self.wilderness, PROBE)[0]
        engage(self.char1, victim)
        victim.traits.hp.current = 0
        before = sorted(
            member.pk for member in _species_members(self.wilderness, PROBE)
        )

        ensure_population(self.wilderness, PROBE)

        self.assertEqual(
            sorted(member.pk for member in _species_members(self.wilderness, PROBE)),
            before,
        )
        # The defeated participant is still registered, not replaced: the pass
        # is skipped so session restoration settles it first.
        self.assertIn(victim.pk, before)
        self.assertTrue(
            Monster.objects.filter(pk=victim.pk).exists()
        )

    @covers_requirement(
        "wilderness-population-view::population-reads-share-materialization-decisions"
    )
    def test_species_view_agrees_with_materialization_and_session_protection(self):
        # Cell PROBE has 2 living species monsters placed in setUp
        members = _species_members(self.wilderness, PROBE)
        self.assertEqual(len(members), self.rule.quantity)
        # Each individual's observation identity is the slot it persists.
        keys = {
            member.pk: ambient_observation_key(
                WILDERNESS_NAME, PROBE[0], PROBE[1], "species", member.db.population_slot
            )
            for member in members
        }
        self.assertEqual(len(set(keys.values())), len(members))

        # View the populated cell; char1 is also at PROBE so filter monster facts
        facts = population_view(self.wilderness, [PROBE])
        monster_facts = [f for f in facts if f.kind == "monster"]
        self.assertEqual(len(monster_facts), self.rule.quantity)
        self.assertEqual(
            {f.observation_key: f.label for f in monster_facts},
            {keys[member.pk]: member.key for member in members},
        )

        # Now start an active combat session with the slot-0 individual
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        victim = next(member for member in members if member.db.population_slot == 0)
        survivor = next(member for member in members if member.pk != victim.pk)
        engage(self.char1, victim)
        victim.traits.hp.current = 0

        # Session is active and victim is defeated:
        # View must project living participant/monsters as protected without spawning prospective replacements
        decision = ambient_population_decision(self.wilderness, PROBE)
        self.assertTrue(decision.is_session_protected)
        self.assertEqual(decision.spawns_needed, ())

        facts_protected = population_view(self.wilderness, [PROBE])
        monster_facts_protected = [f for f in facts_protected if f.kind == "monster"]
        # Only the living survivor is projected, and under its own exact key:
        # it never inherits the defeated individual's slot while the pass is
        # frozen, and no prospective replacement appears.
        self.assertEqual(
            [(f.observation_key, f.label) for f in monster_facts_protected],
            [(keys[survivor.pk], survivor.key)],
        )

    @covers_requirement(
        "wilderness-population-view::observation-identities-survive-materialization",
        "wilderness-population-view::population-reads-share-materialization-decisions",
    )
    def test_a_survivor_keeps_its_identity_when_the_slot_before_it_dies(self):
        # One variant fills both slots, so matching survivors by variant alone
        # would move the survivor into the defeated individual's slot.
        narrow = AmbientPlacementRule(self.region, (ORDINARY,), 2, 3)
        self.enterContext(
            synthetic_registries(
                "ambient_placements",
                extra={"ambient_placements": {self.region: narrow}},
            )
        )
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        cell = next(candidate for candidate in _region_cells(self.region) if candidate != PROBE)
        enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME)

        by_slot = {
            member.db.population_slot: member
            for member in _species_members(self.wilderness, cell)
        }
        self.assertEqual(set(by_slot), {0, 1})
        self.assertEqual({member.variant_key for member in by_slot.values()}, {ORDINARY})
        keys = {
            slot: ambient_observation_key(
                WILDERNESS_NAME, cell[0], cell[1], "species", slot
            )
            for slot in by_slot
        }
        victim, survivor = by_slot[0], by_slot[1]

        self.char1.race = "human"
        self.char1.apply_race_baseline()
        engage(self.char1, victim)
        victim.traits.hp.current = 0

        decision = ambient_population_decision(self.wilderness, cell)
        self.assertTrue(decision.is_session_protected)
        self.assertEqual(decision.spawns_needed, ())
        # Pre-fix the survivor was reassigned to slot 0, adopting the dead
        # individual's observation identity.
        projected = [
            fact for fact in population_view(self.wilderness, [cell]) if fact.kind == "monster"
        ]
        self.assertEqual(
            [(fact.observation_key, fact.label) for fact in projected],
            [(keys[1], survivor.key)],
        )

        # Protection ends: reconciliation refills the vacant slot only.
        clear_session(self.char1)
        ensure_population(self.wilderness, cell)

        living = _species_members(self.wilderness, cell)
        self.assertEqual(len(living), 2)
        self.assertIn(survivor.pk, [member.pk for member in living])
        self.assertEqual(Monster.objects.get(pk=survivor.pk).db.population_slot, 1)
        replacement = next(member for member in living if member.pk != survivor.pk)
        self.assertEqual(replacement.db.population_slot, 0)
        resumed = {
            fact.observation_key: fact.label
            for fact in population_view(self.wilderness, [cell])
            if fact.kind == "monster"
        }
        self.assertEqual(resumed[keys[1]], survivor.key)
        self.assertEqual(resumed[keys[0]], replacement.key)
