"""Data-contract test: spell catalog content contract
Elemental spell-catalog tests and their pinned catalog constants."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.elements import ELEMENT_REGISTRY
from world.skills.effects import (
    BuffApplyEffect,
    CleanseEffect,
    DamageEffect,
    HealEffect,
    MovementEffect,
    RiteBlessingEffect,
    RiteShelterEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    parse_effect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillKind,
    TargetSpec,
    declared_prerequisites,
    prerequisite_consumers,
)


# Retained for callers importing _CATALOG_EFFECTS; elemental catalogs have migrated to behavior specs.
_CATALOG_EFFECTS: dict[str, tuple[str, ...]] = {}

class ElementalSpellsBuilderTests(unittest.TestCase):
    def test_elemental_spells_builder_rejects_unknown_element(self):
        from world.skills.registry import _elemental_spells

        with self.assertRaises(ValueError):
            _elemental_spells(
                "bogus",
                ("x", "X", "說明", TargetSpec.SINGLE, 10, ("damage:fire:magic",)),
            )


class ClosedVocabularyParseTests(unittest.TestCase):
    """Positive parses of the parser's closed production vocabularies.

    The accepted values of these branches ARE shipped grammar (no synthetic
    substitute exists), so their assertions live in this registered content
    contract rather than in the synthetic data-independent behavior tests.
    """

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_movement_flash_step_parses_as_the_closed_mode(self):
        self.assertEqual(
            parse_effect("movement:flash_step"),
            MovementEffect(mode="flash_step"),
        )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_self_heal_bare_prefix_parses_into_its_dataclass(self):
        self.assertEqual(parse_effect("self_heal"), SelfHealEffect())

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_blessing_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("rite_blessing:martial_blessing"),
            RiteBlessingEffect(buff_key="martial_blessing"),
        )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_blessing_malformed_payloads_raise(self):
        for effect in ("rite_blessing", "rite_blessing:", "rite_blessing:a:b"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_shelter_parses_into_its_dataclass(self):
        self.assertEqual(
            parse_effect("rite_shelter"),
            RiteShelterEffect(),
        )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_rite_shelter_rejects_payload(self):
        for effect in ("rite_shelter:", "rite_shelter:today", "rite_shelter:sanctuary"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)


class LightningLineageTreeCatalogTests(unittest.TestCase):
    """The shipped branching lightning lineage tree with a two-parent canopy is catalog data.

    The edge topology is the shipped content the requirement names, so it
    lives in this registered data-contract file; each edge threshold is
    authored tuning data, so only its positive-integer shape is asserted.
    """

    @covers_requirement(
        "skill-lineage::the-lightning-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_lightning_tree_edges_are_as_designed(self):
        expected_edges = {
            "lightning_flicker": ("static_ward",),
            "thunder_combo": ("lightning_flicker",),
            "thunder_gods_haste": ("thunder_combo",),
            "thunder_shatter_strike": ("thunder_combo",),
            "judgement_thunder": ("thunder_gods_haste",),
            "chain_lightning": ("spark_shock",),
            "paralyzing_bolt": ("spark_shock",),
            "lightning_strike": ("chain_lightning",),
            "thunder_prison": ("paralyzing_bolt",),
            "heavens_thunder": ("lightning_strike",),
            "divine_lightning_slaughter": ("heavens_thunder",),
            "thunder_apotheosis": (
                "judgement_thunder",
                "divine_lightning_slaughter",
            ),
        }
        for key, parent_keys in expected_edges.items():
            with self.subTest(spell=key):
                declared = declared_prerequisites(key)
                self.assertEqual(
                    tuple(prereq.skill_key for prereq in declared),
                    parent_keys,
                )
                for prereq in declared:
                    self.assertIs(type(prereq.min_proficiency), int)
                    self.assertGreaterEqual(prereq.min_proficiency, 1)
        for root in ("static_ward", "spark_shock"):
            self.assertEqual(declared_prerequisites(root), ())
        # Topological canopy: thunder_apotheosis is consumed by nothing.
        self.assertEqual(prerequisite_consumers("thunder_apotheosis"), ())
        # Both canopy parents are consumed only by the canopy edge.
        for parent in ("judgement_thunder", "divine_lightning_slaughter"):
            self.assertEqual(
                tuple(consumer for consumer, _ in prerequisite_consumers(parent)),
                ("thunder_apotheosis",),
            )
        # Branch points feed exactly their authored children.
        self.assertEqual(
            {consumer for consumer, _ in prerequisite_consumers("spark_shock")},
            {"chain_lightning", "paralyzing_bolt"},
        )
        self.assertEqual(
            {consumer for consumer, _ in prerequisite_consumers("thunder_combo")},
            {"thunder_gods_haste", "thunder_shatter_strike"},
        )
        # Terminal leaves have empty consumers.
        self.assertEqual(prerequisite_consumers("thunder_shatter_strike"), ())
        self.assertEqual(prerequisite_consumers("thunder_prison"), ())

    def test_lightning_passives_stay_out_of_the_graph(self):
        self.assertEqual(prerequisite_consumers("lightning_mastery"), ())
        self.assertEqual(declared_prerequisites("lightning_mastery"), ())


class IceLineageTreeCatalogTests(unittest.TestCase):
    """The shipped branching ice lineage tree with a two-parent canopy is catalog data.

    The edge topology is the shipped content the requirement names, so it
    lives in this registered data-contract file; each edge threshold is
    authored tuning data, so only its positive-integer shape is asserted.
    """

    @covers_requirement(
        "skill-lineage::the-ice-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_ice_tree_edges_are_as_designed(self):
        expected_edges = {
            "ice_wall": ("frost_breath",),
            "frost_mire": ("ice_wall",),
            "permafrost_domain": ("ice_wall",),
            "absolute_tundra": ("permafrost_domain",),
            "eternal_ice_field": ("absolute_tundra",),
            "frost_arrow_rain": ("ice_shard",),
            "ice_prison": ("frost_arrow_rain",),
            "blizzard": ("ice_prison",),
            "crystal_shatter": ("ice_prison",),
            "absolute_zero": ("blizzard",),
            "eternal_frost_apotheosis": ("eternal_ice_field", "absolute_zero"),
        }
        for key, parent_keys in expected_edges.items():
            with self.subTest(spell=key):
                declared = declared_prerequisites(key)
                self.assertEqual(
                    tuple(prereq.skill_key for prereq in declared),
                    parent_keys,
                )
                for prereq in declared:
                    self.assertIs(type(prereq.min_proficiency), int)
                    self.assertGreaterEqual(prereq.min_proficiency, 1)
        self.assertEqual(declared_prerequisites("frost_breath"), ())
        self.assertEqual(declared_prerequisites("ice_shard"), ())
        # Topological canopy: eternal_frost_apotheosis is consumed by nothing.
        self.assertEqual(prerequisite_consumers("eternal_frost_apotheosis"), ())
        # Both canopy parents are consumed only by the canopy edge.
        for parent in ("eternal_ice_field", "absolute_zero"):
            self.assertEqual(
                tuple(consumer for consumer, _ in prerequisite_consumers(parent)),
                ("eternal_frost_apotheosis",),
            )
        # Branch points feed exactly their two authored children.
        self.assertEqual(
            {consumer for consumer, _ in prerequisite_consumers("ice_wall")},
            {"frost_mire", "permafrost_domain"},
        )
        self.assertEqual(
            {consumer for consumer, _ in prerequisite_consumers("ice_prison")},
            {"blizzard", "crystal_shatter"},
        )
        # Terminal leaves have empty consumers.
        self.assertEqual(prerequisite_consumers("frost_mire"), ())
        self.assertEqual(prerequisite_consumers("crystal_shatter"), ())

    @covers_requirement(
        "skill-lineage::the-ice-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_mastery_passives_stay_out_of_the_graph(self):
        for element_key in ELEMENT_REGISTRY:
            mastery_key = f"{element_key}_mastery"
            with self.subTest(mastery_key=mastery_key):
                self.assertEqual(prerequisite_consumers(mastery_key), ())
                self.assertEqual(declared_prerequisites(mastery_key), ())

class FireLineageTreeCatalogTests(unittest.TestCase):
    """The shipped branching fire lineage tree with a two-parent canopy is catalog data.

    Relocated from the migrated (now synthetic) rules lineage suite: the
    edge topology is the shipped content the requirement names, so it lives in
    this registered data-contract file; each edge threshold is authored
    tuning data, so only its positive-integer shape is asserted.
    """

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-authored-branching-tree-with-a-two-parent-canopy")
    def test_fire_tree_edges_are_as_designed(self):
        expected_edges = {
            "fire_ball": ("fire_arrow",),
            "scorching_wave": ("fire_ball",),
            "firestorm": ("scorching_wave",),
            "flame_shroud": ("scorching_wave",),
            "scorching_armor": ("scorching_wave",),
            "lava_burst": ("firestorm",),
            "hellfire": ("firestorm",),
            "dragon_flame": ("lava_burst",),
            "final_blaze": ("hellfire",),
            "sacrificial_flame": ("dragon_flame",),
            "crimson_apotheosis": ("sacrificial_flame", "final_blaze"),
        }
        for key, parent_keys in expected_edges.items():
            with self.subTest(key=key):
                declared = declared_prerequisites(key)
                self.assertEqual(
                    tuple(prereq.skill_key for prereq in declared),
                    parent_keys,
                )
                for prereq in declared:
                    self.assertIs(type(prereq.min_proficiency), int)
                    self.assertGreaterEqual(prereq.min_proficiency, 1)
        self.assertEqual(declared_prerequisites("fire_arrow"), ())
        # Topological canopy: crimson_apotheosis is the strict last node.
        self.assertEqual(prerequisite_consumers("crimson_apotheosis"), ())
        # sacrificial_flame is consumed only by crimson_apotheosis.
        self.assertEqual(
            tuple(
                consumer
                for consumer, _ in prerequisite_consumers("sacrificial_flame")
            ),
            ("crimson_apotheosis",),
        )

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-authored-branching-tree-with-a-two-parent-canopy")
    def test_mastery_passives_stay_out_of_the_graph(self):
        for element_key in ELEMENT_REGISTRY:
            mastery_key = f"{element_key}_mastery"
            with self.subTest(mastery_key=mastery_key):
                self.assertEqual(prerequisite_consumers(mastery_key), ())
                self.assertEqual(declared_prerequisites(mastery_key), ())


class WindLineageTreeCatalogTests(unittest.TestCase):
    """The shipped branching wind lineage tree with a two-parent canopy is catalog data.

    The edge topology is the shipped content the requirement names, so it
    lives in this registered data-contract file; each edge threshold is
    authored tuning data, so only its positive-integer shape is asserted.
    """

    @covers_requirement(
        "skill-lineage::the-wind-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_wind_tree_edges_are_as_designed(self):
        expected_edges = {
            "gale_chain_step": ("gale_step",),
            "afterimage_step": ("gale_chain_step",),
            "haste_domain": ("afterimage_step",),
            "tornado_blade": ("wind_blade",),
            "storm_domain": ("tornado_blade",),
            "gale_dance_strike": ("tornado_blade",),
            "heavens_wrath_storm": ("storm_domain",),
            "sky_rending_slash": ("gale_dance_strike",),
            "sky_tempest": ("heavens_wrath_storm",),
            "vacuum_severance": ("sky_rending_slash",),
            "sky_apotheosis": ("sky_tempest", "vacuum_severance"),
        }
        for key, parent_keys in expected_edges.items():
            with self.subTest(key=key):
                declared = declared_prerequisites(key)
                self.assertEqual(
                    tuple(prereq.skill_key for prereq in declared),
                    parent_keys,
                )
                for prereq in declared:
                    self.assertIs(type(prereq.min_proficiency), int)
                    self.assertGreaterEqual(prereq.min_proficiency, 1)
        self.assertEqual(declared_prerequisites("gale_step"), ())
        self.assertEqual(declared_prerequisites("wind_blade"), ())
        # Topological canopy: sky_apotheosis is consumed by nothing.
        self.assertEqual(prerequisite_consumers("sky_apotheosis"), ())
        # Both canopy parents are consumed only by the canopy edge.
        for parent in ("sky_tempest", "vacuum_severance"):
            self.assertEqual(
                tuple(consumer for consumer, _ in prerequisite_consumers(parent)),
                ("sky_apotheosis",),
            )
        # Branch point: tornado_blade feeds exactly its two authored children.
        self.assertEqual(
            {consumer for consumer, _ in prerequisite_consumers("tornado_blade")},
            {"storm_domain", "gale_dance_strike"},
        )
        # Mobility leaf: haste_domain is consumed by nothing.
        self.assertEqual(prerequisite_consumers("haste_domain"), ())

    @covers_requirement(
        "skill-lineage::the-wind-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_wind_passives_stay_out_of_the_graph(self):
        for passive_key in ("wind_mastery", "flight"):
            with self.subTest(passive_key=passive_key):
                self.assertEqual(prerequisite_consumers(passive_key), ())
                self.assertEqual(declared_prerequisites(passive_key), ())
