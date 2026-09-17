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


LIGHTNING_SPELL_CATALOG = (
    ("spark_shock", "電擊術", TargetSpec.SINGLE, 13, ("damage:lightning:magic",)),
    (
        "static_ward",
        "靜電護罩",
        TargetSpec.SELF,
        10,
        ("self_buff_apply:lightning_static_ward",),
    ),
    ("chain_lightning", "雷鎖術", TargetSpec.AREA, 27, ("damage:lightning:magic",)),
    (
        "paralyzing_bolt",
        "麻痺電擊",
        TargetSpec.SINGLE,
        24,
        ("damage:lightning:magic", "buff_apply:paralysis"),
    ),
    ("thunder_combo", "雷霆連擊", TargetSpec.SINGLE, 46, ("damage:lightning:magic",)),
    ("lightning_strike", "落雷術", TargetSpec.AREA, 50, ("damage:lightning:magic",)),
    ("heavens_thunder", "天雷降臨", TargetSpec.AREA, 92, ("damage:lightning:magic",)),
    (
        "thunder_gods_haste",
        "雷神之速",
        TargetSpec.SELF,
        68,
        ("self_buff_apply:lightning_extra_action",),
    ),
    ("judgement_thunder", "審判雷霆", TargetSpec.SINGLE, 135, ("damage:lightning:magic",)),
    (
        "divine_lightning_slaughter",
        "神雷滅殺",
        TargetSpec.AREA,
        155,
        ("damage:lightning:magic",),
    ),
)


ICE_SPELL_CATALOG = (
    ("ice_shard", "冰錐術", TargetSpec.SINGLE, 13, ("damage:ice:magic",)),
    ("frost_breath", "凍結之息", TargetSpec.SINGLE, 11, ("buff_apply:ice_slow",)),
    ("ice_wall", "冰牆術", TargetSpec.SINGLE, 25, ("buff_apply:ice_wall",)),
    ("frost_arrow_rain", "冷凍箭雨", TargetSpec.AREA, 28, ("damage:ice:magic",)),
    ("permafrost_domain", "永凍領域", TargetSpec.AREA, 48, ("buff_apply:ice_freeze",)),
    ("ice_prison", "冰封監牢", TargetSpec.SINGLE, 44, ("buff_apply:ice_prison",)),
    ("blizzard", "暴風雪", TargetSpec.AREA, 88, ("damage:ice:magic",)),
    (
        "absolute_tundra",
        "絕對凍土",
        TargetSpec.AREA,
        82,
        ("damage:ice:magic", "buff_apply:ice_freeze"),
    ),
    (
        "absolute_zero",
        "絕對零度",
        TargetSpec.SINGLE,
        140,
        ("damage:ice:magic", "buff_apply:ice_freeze"),
    ),
    (
        "eternal_ice_field",
        "長夜冰原",
        TargetSpec.AREA,
        158,
        ("damage:ice:magic", "buff_apply:ice_freeze"),
    ),
)


_CATALOG_EFFECTS = {
    row[0]: row[4]
    for rows in (
        LIGHTNING_SPELL_CATALOG,
        ICE_SPELL_CATALOG,
    )
    for row in rows
}


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


class LightningSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_all_ten_lightning_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in LIGHTNING_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["lightning"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)
                if key in ("static_ward", "thunder_gods_haste"):
                    self.assertIs(
                        skill.faction_constraint,
                        FactionConstraint.SELF_ONLY,
                    )
                else:
                    self.assertIs(skill.faction_constraint, FactionConstraint.ANY)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_every_lightning_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in LIGHTNING_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="lightning", school="magic"),
                        )
                    elif effect_id.startswith("self_buff_apply:"):
                        self.assertEqual(
                            parsed,
                            SelfBuffApplyEffect(
                                buff_key=effect_id.partition(":")[2]
                            ),
                        )
                    else:
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key=effect_id.partition(":")[2]),
                        )
                    self.assertIn(parsed, skill.parsed_effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_lightning_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["lightning"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in LIGHTNING_SPELL_CATALOG},
        )

class IceSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_all_ten_ice_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in ICE_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["ice"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_every_ice_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in ICE_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="ice", school="magic"),
                        )
                    else:
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key=effect_id.partition(":")[2]),
                        )
                    self.assertIn(parsed, skill.parsed_effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_ice_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["ice"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in ICE_SPELL_CATALOG},
        )


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
