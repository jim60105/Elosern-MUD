"""Data-contract test: published regional species-hunt content contract

The shipped catalog's regional species hunts are approved content
(``monster-regional-species-hunts``), so this module guards the properties that
keep each of them lawful and provisionable instead of re-asserting the authored
numbers for their own sake:

- every published hunt names a region whose authored ambient placement rule
  exists, declares the complete regional selector, holds at least one ordinary
  countable variant that is eligible in that rule, and asks for no more than the
  rule's authored per-coordinate legal supply ``min(quantity, capacity)``;
- a placement-covered region carries exactly one hunt per species its rule
  places, and a region with no ambient rule carries none at all;
- every hunt carries its own authored rank, rating rationale, background flavor
  (each inside the rendered-detail budget) and a reward inside its rank's copper
  band, registered as an ordinary commission of a registered guild branch;
- prose asserts no effect of the six approved special abilities, none of which
  has executable mechanics (a blocklist of their approved names, plus the
  byte-verbatim transcription from the change's approved content table);
- a hunt's authored rank is never below the danger grade its strongest
  countable variant carries, except for the approved divergences the table
  pins: a grade never supplies a rank.

This is content, not mechanism: the runtime already refuses an illegal hunt at
acceptance with its named reason, and that guarantee keeps its single owner.
"""

import unittest
from pathlib import Path
from typing import Mapping

from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.monster_placement import AMBIENT_PLACEMENT_REGISTRY
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.quests.catalog import QUEST_CATALOG, register_catalog
from world.quests.definitions import (
    MAX_DEFINITION_PROSE_LENGTH,
    MAX_DEFINITION_PROSE_TOTAL,
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    ordinary_countable_variant_keys,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.guild_config import load_guild_catalog

REPO_ROOT = Path(__file__).resolve().parents[3]
BESTIARY = REPO_ROOT / "docs" / "lore" / "bestiary.md"

#: The six approved special abilities of the first bestiary batch, verbatim from
#: the approved bestiary's own ability list (docs/lore/bestiary.md, 使用邊界).
#: None of them has executable mechanics — they are declared external
#: prerequisites — so no published hunt may assert one. A rationale describes the
#: arrangement, numbers, and terrain instead; where a bestiary sentence describes
#: an effect symptom, the published prose states the local conflict.
#:
#: The guard below is a blocklist of these six exact approved names, not a
#: semantic no-ability-claim check: a paraphrase of an ability effect that names
#: none of them passes it. The bestiary's own 能力邊界 sections are the
#: prose-review anchor for a paraphrase, and the shipped prose is additionally
#: transcribed verbatim from the change's approved content table.
APPROVED_ABILITY_CLAIMS = (
    "氣流震穀",
    "追隨燈光的發光斑紋",
    "壓實土埂",
    "接觸吸取魔力",
    "聚集霧氣",
    "敲岩脈動",
)

#: The two mid hunts and the rank they keep although their strongest countable
#: variant is graded above it (design D-R3: the rank is authored for the
#: arrangement, never inherited from an individual danger grade).
MID_HUNTS = {
    "northwest_highland_forest_fog_mane_lynx": "D",
    "western_hills_valleys_rock_echo_goat": "D",
}

#: Every published hunt whose strongest countable variant carries a danger grade
#: above the hunt's own rank: hunt key -> (authored rank, strongest grade). The
#: shipped content itself demonstrates the independence — the two mid hunts stay
#: ``D`` while their strongest countable variant is graded ``C`` — so a content
#: change that let a rank follow a grade has to state it here first.
AUTHORED_GRADE_DIVERGENCES = {
    "eastern_plains_sway_whistle_sparrow": ("F", "E"),
    "eastern_plains_ridge_burrow_hare": ("F", "E"),
    "northwest_highland_forest_fog_mane_lynx": ("D", "C"),
    "western_hills_valleys_rock_echo_goat": ("D", "C"),
}

#: The region with no authored ambient placement. Its only species presence is
#: the authored boss site published by the bound clear-out change, so a regional
#: hunt there could never be satisfied by construction.
UNPLACED_REGION_KEY = "southeast_coast"


def _regional_hunts() -> dict[str, QuestDefinition]:
    """The shipped regional species hunts, keyed by definition key.

    A published regional hunt is a shipped catalog definition whose stage-zero
    objective declares the regional selector. The selector families are mutually
    exclusive, so a bound clear-out — which declares ``requires_bound_targets``
    instead — can never be read as a regional hunt.

    No cardinality is pinned here by design: a later change appends bound
    clear-outs to the same catalog, which this filter excludes, so the seven-key
    offer expectation in
    ``world/rules/tests/test_guild_config/test_catalog_loading.py`` is what keeps
    this set from silently shrinking, and the per-region coverage assertions
    below keep it from silently growing.
    """
    hunts: dict[str, QuestDefinition] = {}
    for definition in QUEST_CATALOG:
        if definition.stages[0].objective.region_key is not None:
            hunts[definition.key] = definition
    return hunts


def _region_key(definition: QuestDefinition) -> str:
    return definition.stages[0].objective.region_key


def _hunt_regions() -> set[str]:
    return {_region_key(definition) for definition in _regional_hunts().values()}


def _strongest_countable_grade(definition: QuestDefinition) -> str:
    """The highest-ranked danger grade among the hunt's countable variants."""
    objective = definition.stages[0].objective
    return max(
        (
            MONSTER_VARIANT_REGISTRY[variant_key].danger_grade
            for variant_key in objective.countable_variant_keys
        ),
        key=lambda grade: GUILD_RANK_REGISTRY[grade].order,
    )


def _next_rank_key(rank_key: str) -> str | None:
    """The key of the rank one step above ``rank_key``, or ``None`` for the top."""
    order = GUILD_RANK_REGISTRY[rank_key].order
    following = [
        row for row in GUILD_RANK_REGISTRY.values() if row.order == order + 1
    ]
    return following[0].key if following else None


class _ShippedCatalogTestCase(RegistryIsolationMixin, unittest.TestCase):
    """Register the shipped catalog around every contract test.

    ``register_catalog()`` is idempotent, so calling it here makes each test
    independent of whether an earlier test in the same worker process already
    registered the catalog, and the isolation mixin puts the process-global
    registries back afterwards.
    """

    def setUp(self):
        super().setUp()
        register_catalog()


class ShippedHuntRegistrationTests(_ShippedCatalogTestCase):
    def test_the_shipped_catalog_registers_and_stays_registered(self):
        register_catalog()
        for definition in QUEST_CATALOG:
            with self.subTest(definition=definition.key):
                self.assertEqual(
                    QUEST_DEFINITION_REGISTRY[definition.key], definition
                )


class RegionalHuntProvisionabilityTests(_ShippedCatalogTestCase):
    def test_every_published_hunt_names_a_region_with_an_authored_ambient_rule(self):
        hunts = _regional_hunts()
        self.assertTrue(hunts)
        for key, definition in hunts.items():
            with self.subTest(hunt=key):
                self.assertIsNotNone(
                    AMBIENT_PLACEMENT_REGISTRY.get(_region_key(definition))
                )

    def test_every_published_hunt_declares_the_complete_selector(self):
        # A partial selector would not register, but the content contract states
        # the property rather than inferring it from the validator: a definition
        # carrying only a region key is not a regional hunt.
        for key, definition in _regional_hunts().items():
            objective = definition.stages[0].objective
            with self.subTest(hunt=key):
                self.assertTrue(objective.species_key)
                self.assertTrue(objective.countable_variant_keys)

    def test_at_least_one_ordinary_countable_variant_is_eligible_in_the_rule(self):
        # This is what makes the acceptance-time guarantee expressible: the
        # provisioning owner can only create a variant the rule places.
        for key, definition in _regional_hunts().items():
            objective = definition.stages[0].objective
            rule = AMBIENT_PLACEMENT_REGISTRY[_region_key(definition)]
            ordinary = ordinary_countable_variant_keys(objective)
            with self.subTest(hunt=key):
                self.assertTrue(ordinary)
                self.assertTrue(set(ordinary) & set(rule.variant_keys))

    def test_the_quantity_is_at_or_below_the_regions_authored_supply(self):
        for key, definition in _regional_hunts().items():
            objective = definition.stages[0].objective
            rule = AMBIENT_PLACEMENT_REGISTRY[_region_key(definition)]
            with self.subTest(hunt=key):
                self.assertLessEqual(
                    objective.quantity, min(rule.quantity, rule.capacity)
                )

    def test_the_uncovered_region_carries_no_hunt(self):
        # A region with no authored placement could never satisfy a hunt, so the
        # board must not offer one there.
        self.assertNotIn(UNPLACED_REGION_KEY, AMBIENT_PLACEMENT_REGISTRY)
        self.assertIn(UNPLACED_REGION_KEY, WILDERNESS_REGION_REGISTRY)
        self.assertNotIn(UNPLACED_REGION_KEY, _hunt_regions())

    def test_one_hunt_per_placed_species_in_every_covered_region(self):
        hunts = _regional_hunts()
        for region_key, rule in AMBIENT_PLACEMENT_REGISTRY.items():
            placed_species = {
                MONSTER_VARIANT_REGISTRY[variant_key].species_key
                for variant_key in rule.variant_keys
            }
            self.assertTrue(placed_species)
            for species_key in sorted(placed_species):
                with self.subTest(region=region_key, species=species_key):
                    matching = [
                        key
                        for key, definition in hunts.items()
                        if _region_key(definition) == region_key
                        and definition.stages[0].objective.species_key == species_key
                    ]
                    self.assertEqual(
                        len(matching),
                        1,
                        f"{region_key}/{species_key} hunts: {sorted(matching)}",
                    )
                    objective = hunts[matching[0]].stages[0].objective
                    placed_variants = {
                        variant_key
                        for variant_key in rule.variant_keys
                        if MONSTER_VARIANT_REGISTRY[variant_key].species_key
                        == species_key
                    }
                    # Equality both ways: a hunt may not count a variant its
                    # region does not place, and it must count every variant its
                    # region places for the species it is commissioned against
                    # the ambient owner selects from.
                    self.assertEqual(
                        placed_variants, set(objective.countable_variant_keys)
                    )


class HuntAuthoredContentTests(_ShippedCatalogTestCase):
    def test_the_introductory_reward_row_stays_the_first_offer(self):
        # The joins in world/rules/tests/test_guild_config/ read
        # ``catalog.quest_offers[0]``; the appended hunt rows must sit after it.
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(catalog.quest_offers[0].definition_key, "introductory_hunt")

    def test_every_hunt_carries_rank_rationale_flavor_and_a_banded_reward(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        for key, definition in _regional_hunts().items():
            with self.subTest(hunt=key):
                rank = GUILD_RANK_REGISTRY.get(definition.rank)
                self.assertIsNotNone(rank)
                rationale = definition.rating_rationale_zh
                flavor = definition.background_flavor_zh
                self.assertTrue(rationale and rationale.strip())
                self.assertTrue(flavor and flavor.strip())
                self.assertNotEqual(rationale, flavor)
                self.assertLessEqual(len(rationale), MAX_DEFINITION_PROSE_LENGTH)
                self.assertLessEqual(len(flavor), MAX_DEFINITION_PROSE_LENGTH)
                self.assertLessEqual(
                    len(rationale) + len(flavor), MAX_DEFINITION_PROSE_TOTAL
                )
                # No deadline: a hunt nobody asked to be time-limited adds a
                # failure mode the approved content deliberately avoids.
                self.assertIsNone(definition.deadline_hours)
                offer = catalog.offer_by_definition.get(key)
                self.assertIsNotNone(offer, f"{key} has no registered guild offer")
                self.assertIn(offer.issuer_branch_key, GUILD_BRANCH_REGISTRY)
                self.assertGreaterEqual(offer.reward.copper, rank.reward_min_copper)
                self.assertLessEqual(offer.reward.copper, rank.reward_max_copper)
                # The approved reward join stays copper + merit: monster loot is
                # the monster side's business, not a commission's.
                self.assertEqual(offer.reward.items, ())

    def test_reward_merit_fits_inside_its_rank_threshold_band(self):
        # The authored-merit bound of the approved content: a hunt's merit stays
        # inside the span from its own rank's examination threshold to the next
        # rank's, so no member standing at their own rank's entry can be carried
        # across the next threshold by one hunt's merit alone. This is the
        # band-span reading of that decision, not a guarantee for a member
        # already standing just below a threshold.
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        thresholds: Mapping[str, int] = catalog.merit_thresholds
        for key, definition in _regional_hunts().items():
            next_rank_key = _next_rank_key(definition.rank)
            if next_rank_key is None:
                continue
            with self.subTest(hunt=key):
                # F is the entry rank and legitimately carries no threshold row
                # (the rulebook requires E-through-S); every other rank must
                # have one, so a vanished row is a loud KeyError instead of a
                # silently widened band.
                own_floor = (
                    0 if definition.rank == "F" else thresholds[definition.rank]
                )
                band_span = thresholds[next_rank_key] - own_floor
                offer = catalog.offer_by_definition[key]
                self.assertGreater(offer.reward.merit, 0)
                self.assertLess(offer.reward.merit, band_span)


class HuntRankIndependenceTests(_ShippedCatalogTestCase):
    def test_hunt_rank_is_never_below_its_strongest_countable_grade(self):
        # The authored rank is not derived from a danger grade, so a hunt whose
        # strongest countable variant is graded above it has to be one of the
        # approved divergences instead of a newly copied rank. Equality with the
        # strongest grade is lawful and shipped twice (both E hunts carry an
        # E-graded stronger partner), so this pins the above-grade cases rather
        # than forbidding every coincidence.
        divergences = {}
        for key, definition in _regional_hunts().items():
            strongest = _strongest_countable_grade(definition)
            if (
                GUILD_RANK_REGISTRY[strongest].order
                > GUILD_RANK_REGISTRY[definition.rank].order
            ):
                divergences[key] = (definition.rank, strongest)
        self.assertEqual(divergences, AUTHORED_GRADE_DIVERGENCES)

    def test_the_two_mid_hunts_keep_their_authored_mid_rank(self):
        hunts = _regional_hunts()
        for key, rank in MID_HUNTS.items():
            definition = hunts[key]
            with self.subTest(hunt=key):
                self.assertEqual(definition.rank, rank)
                self.assertGreater(
                    GUILD_RANK_REGISTRY[_strongest_countable_grade(definition)].order,
                    GUILD_RANK_REGISTRY[rank].order,
                )


class HuntProseBoundaryTests(_ShippedCatalogTestCase):
    def test_the_ability_vocabulary_is_the_approved_bestiarys_own(self):
        # Non-vacuity: the guard below compares against real approved ability
        # names, so a reworded or dropped bestiary entry fails here rather than
        # silently weakening the prose contract.
        bestiary = BESTIARY.read_text(encoding="utf-8")
        for claim in APPROVED_ABILITY_CLAIMS:
            with self.subTest(claim=claim):
                self.assertIn(claim, bestiary)

    def test_no_published_hunt_prose_asserts_an_unimplemented_ability(self):
        for key, definition in _regional_hunts().items():
            published = (definition.display_name, definition.rating_rationale_zh,
                         definition.background_flavor_zh)
            for claim in APPROVED_ABILITY_CLAIMS:
                with self.subTest(hunt=key, claim=claim):
                    for text in published:
                        self.assertNotIn(claim, text or "")


if __name__ == "__main__":
    unittest.main()
