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
    SkillPrerequisite,
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

    The edge table itself is the shipped content the requirement names, so it
    lives in this registered data-contract file.
    """

    @covers_requirement(
        "skill-lineage::the-lightning-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_lightning_tree_edges_are_as_designed(self):
        expected = {
            "lightning_flicker": (SkillPrerequisite("static_ward", 3),),
            "thunder_combo": (SkillPrerequisite("lightning_flicker", 3),),
            "thunder_gods_haste": (SkillPrerequisite("thunder_combo", 5),),
            "thunder_shatter_strike": (SkillPrerequisite("thunder_combo", 5),),
            "judgement_thunder": (SkillPrerequisite("thunder_gods_haste", 8),),
            "chain_lightning": (SkillPrerequisite("spark_shock", 3),),
            "paralyzing_bolt": (SkillPrerequisite("spark_shock", 3),),
            "lightning_strike": (SkillPrerequisite("chain_lightning", 3),),
            "thunder_prison": (SkillPrerequisite("paralyzing_bolt", 3),),
            "heavens_thunder": (SkillPrerequisite("lightning_strike", 5),),
            "divine_lightning_slaughter": (SkillPrerequisite("heavens_thunder", 8),),
            "thunder_apotheosis": (
                SkillPrerequisite("judgement_thunder", 10),
                SkillPrerequisite("divine_lightning_slaughter", 10),
            ),
        }
        for key, expected_prereqs in expected.items():
            with self.subTest(spell=key):
                self.assertEqual(
                    declared_prerequisites(key),
                    expected_prereqs,
                )
        self.assertEqual(declared_prerequisites("static_ward"), ())
        self.assertEqual(declared_prerequisites("spark_shock"), ())
        # Topological canopy: thunder_apotheosis is consumed by nothing.
        self.assertEqual(prerequisite_consumers("thunder_apotheosis"), ())
        # Both Lv.10 parents are consumed only by thunder_apotheosis at threshold 10.
        self.assertEqual(
            prerequisite_consumers("judgement_thunder"),
            (("thunder_apotheosis", 10),),
        )
        self.assertEqual(
            prerequisite_consumers("divine_lightning_slaughter"),
            (("thunder_apotheosis", 10),),
        )
        # Branch points: spark_shock feeds exactly two children at threshold 3.
        self.assertEqual(
            set(prerequisite_consumers("spark_shock")),
            {("chain_lightning", 3), ("paralyzing_bolt", 3)},
        )
        # thunder_combo feeds exactly two children at threshold 5.
        self.assertEqual(
            set(prerequisite_consumers("thunder_combo")),
            {("thunder_gods_haste", 5), ("thunder_shatter_strike", 5)},
        )
        # Terminal leaves have empty consumers.
        self.assertEqual(prerequisite_consumers("thunder_shatter_strike"), ())
        self.assertEqual(prerequisite_consumers("thunder_prison"), ())

    def test_lightning_passives_stay_out_of_the_graph(self):
        self.assertEqual(prerequisite_consumers("lightning_mastery"), ())
        self.assertEqual(declared_prerequisites("lightning_mastery"), ())


class IceLineageTreeCatalogTests(unittest.TestCase):
    """The shipped branching ice lineage tree with a two-parent canopy is catalog data.

    The edge table itself is the shipped content the requirement names, so it
    lives in this registered data-contract file.
    """

    @covers_requirement(
        "skill-lineage::the-ice-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_ice_tree_edges_are_as_designed(self):
        expected = {
            "ice_wall": (SkillPrerequisite("frost_breath", 3),),
            "frost_mire": (SkillPrerequisite("ice_wall", 3),),
            "permafrost_domain": (SkillPrerequisite("ice_wall", 3),),
            "absolute_tundra": (SkillPrerequisite("permafrost_domain", 8),),
            "eternal_ice_field": (SkillPrerequisite("absolute_tundra", 8),),
            "frost_arrow_rain": (SkillPrerequisite("ice_shard", 3),),
            "ice_prison": (SkillPrerequisite("frost_arrow_rain", 3),),
            "blizzard": (SkillPrerequisite("ice_prison", 5),),
            "crystal_shatter": (SkillPrerequisite("ice_prison", 5),),
            "absolute_zero": (SkillPrerequisite("blizzard", 8),),
            "eternal_frost_apotheosis": (
                SkillPrerequisite("eternal_ice_field", 10),
                SkillPrerequisite("absolute_zero", 10),
            ),
        }
        for key, expected_prereqs in expected.items():
            with self.subTest(spell=key):
                self.assertEqual(
                    declared_prerequisites(key),
                    expected_prereqs,
                )
        self.assertEqual(declared_prerequisites("frost_breath"), ())
        self.assertEqual(declared_prerequisites("ice_shard"), ())
        # Topological canopy: eternal_frost_apotheosis is consumed by nothing.
        self.assertEqual(prerequisite_consumers("eternal_frost_apotheosis"), ())
        # Both Lv.10 parents are consumed only by eternal_frost_apotheosis at threshold 10.
        self.assertEqual(
            prerequisite_consumers("eternal_ice_field"),
            (("eternal_frost_apotheosis", 10),),
        )
        self.assertEqual(
            prerequisite_consumers("absolute_zero"),
            (("eternal_frost_apotheosis", 10),),
        )
        # Branch points: ice_wall feeds exactly two children at threshold 3.
        self.assertEqual(
            set(prerequisite_consumers("ice_wall")),
            {("frost_mire", 3), ("permafrost_domain", 3)},
        )
        # ice_prison feeds exactly two children at threshold 5.
        self.assertEqual(
            set(prerequisite_consumers("ice_prison")),
            {("blizzard", 5), ("crystal_shatter", 5)},
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
    edge table itself is the shipped content the requirement names, so it
    lives in this registered data-contract file.
    """

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-authored-branching-tree-with-a-two-parent-canopy")
    def test_fire_tree_edges_are_as_designed(self):
        expected = {
            "fire_ball": (SkillPrerequisite("fire_arrow", 3),),
            "scorching_wave": (SkillPrerequisite("fire_ball", 3),),
            "firestorm": (SkillPrerequisite("scorching_wave", 3),),
            "flame_shroud": (SkillPrerequisite("scorching_wave", 3),),
            "scorching_armor": (SkillPrerequisite("scorching_wave", 3),),
            "lava_burst": (SkillPrerequisite("firestorm", 5),),
            "hellfire": (SkillPrerequisite("firestorm", 5),),
            "dragon_flame": (SkillPrerequisite("lava_burst", 8),),
            "final_blaze": (SkillPrerequisite("hellfire", 5),),
            "sacrificial_flame": (SkillPrerequisite("dragon_flame", 8),),
            "crimson_apotheosis": (
                SkillPrerequisite("sacrificial_flame", 10),
                SkillPrerequisite("final_blaze", 10),
            ),
        }
        for key, expected_prereqs in expected.items():
            with self.subTest(key=key):
                self.assertEqual(
                    declared_prerequisites(key),
                    expected_prereqs,
                )
        self.assertEqual(declared_prerequisites("fire_arrow"), ())
        # Topological canopy: crimson_apotheosis is the strict last node.
        self.assertEqual(prerequisite_consumers("crimson_apotheosis"), ())
        # sacrificial_flame is consumed only by crimson_apotheosis.
        self.assertEqual(
            prerequisite_consumers("sacrificial_flame"),
            (("crimson_apotheosis", 10),),
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

    The edge table itself is the shipped content the requirement names, so it
    lives in this registered data-contract file.
    """

    @covers_requirement(
        "skill-lineage::the-wind-lineage-ships-as-the-authored-two-root-branching-tree-with-a-two-parent-canopy"
    )
    def test_wind_tree_edges_are_as_designed(self):
        expected = {
            "gale_chain_step": (SkillPrerequisite("gale_step", 3),),
            "afterimage_step": (SkillPrerequisite("gale_chain_step", 3),),
            "haste_domain": (SkillPrerequisite("afterimage_step", 5),),
            "tornado_blade": (SkillPrerequisite("wind_blade", 3),),
            "storm_domain": (SkillPrerequisite("tornado_blade", 3),),
            "gale_dance_strike": (SkillPrerequisite("tornado_blade", 3),),
            "heavens_wrath_storm": (SkillPrerequisite("storm_domain", 5),),
            "sky_rending_slash": (SkillPrerequisite("gale_dance_strike", 8),),
            "sky_tempest": (SkillPrerequisite("heavens_wrath_storm", 8),),
            "vacuum_severance": (SkillPrerequisite("sky_rending_slash", 8),),
            "sky_apotheosis": (
                SkillPrerequisite("sky_tempest", 10),
                SkillPrerequisite("vacuum_severance", 10),
            ),
        }
        for key, expected_prereqs in expected.items():
            with self.subTest(key=key):
                self.assertEqual(
                    declared_prerequisites(key),
                    expected_prereqs,
                )
        self.assertEqual(declared_prerequisites("gale_step"), ())
        self.assertEqual(declared_prerequisites("wind_blade"), ())
        # Topological canopy: sky_apotheosis is consumed by nothing.
        self.assertEqual(prerequisite_consumers("sky_apotheosis"), ())
        # Both Lv.8 parents are consumed only by sky_apotheosis at threshold 10.
        self.assertEqual(
            prerequisite_consumers("sky_tempest"),
            (("sky_apotheosis", 10),),
        )
        self.assertEqual(
            prerequisite_consumers("vacuum_severance"),
            (("sky_apotheosis", 10),),
        )
        # Branch point: tornado_blade feeds exactly two children at threshold 3.
        self.assertEqual(
            set(prerequisite_consumers("tornado_blade")),
            {("storm_domain", 3), ("gale_dance_strike", 3)},
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
