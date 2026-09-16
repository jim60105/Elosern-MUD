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


WIND_SPELL_CATALOG = (
    ("wind_blade", "風刃術", TargetSpec.AREA, 14, ("damage:wind:magic",)),
    ("gale_step", "疾風術", TargetSpec.SELF, 10, ("self_buff_apply:wind_haste",)),
    ("flight", "飛行術", TargetSpec.SELF, 22, ("movement:flight",)),
    ("tornado_blade", "龍捲風刃", TargetSpec.SINGLE, 26, ("damage:wind:magic",)),
    ("storm_domain", "暴風領域", TargetSpec.AREA, 50, ("damage:wind:magic",)),
    ("gale_dance_strike", "疾風刃舞", TargetSpec.SINGLE, 40, ("damage:wind:magic",)),
    ("heavens_wrath_storm", "天譴風暴", TargetSpec.AREA, 90, ("damage:wind:magic",)),
    ("haste_domain", "神速領域", TargetSpec.AREA, 70, ("buff_apply:wind_haste_domain",)),
    ("vacuum_severance", "真空斬滅", TargetSpec.SINGLE, 130, ("damage:wind:magic",)),
    ("sky_tempest", "蒼穹暴風", TargetSpec.AREA, 150, ("damage:wind:magic",)),
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
        WIND_SPELL_CATALOG,
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


class WindSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_all_ten_wind_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in WIND_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.element, ELEMENT_REGISTRY["wind"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)
                if key == "flight":
                    self.assertIs(skill.kind, SkillKind.PASSIVE)
                    self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
                elif key == "gale_step":
                    self.assertIs(skill.kind, SkillKind.ACTIVE)
                    self.assertIs(skill.faction_constraint, FactionConstraint.SELF_ONLY)
                else:
                    self.assertIs(skill.kind, SkillKind.ACTIVE)
                    self.assertIs(skill.faction_constraint, FactionConstraint.ANY)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_every_wind_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in WIND_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="wind", school="magic"),
                        )
                    elif effect_id.startswith("self_buff_apply:"):
                        self.assertEqual(
                            parsed,
                            SelfBuffApplyEffect(
                                buff_key=effect_id.partition(":")[2]
                            ),
                        )
                    elif effect_id.startswith("buff_apply:"):
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key=effect_id.partition(":")[2]),
                        )
                    else:
                        self.assertEqual(parsed, MovementEffect(mode="flight"))
                    self.assertIn(parsed, skill.parsed_effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_wind_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["wind"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in WIND_SPELL_CATALOG} - {"flight"},
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_wind_blade_and_flight_was_recosted_in_place_not_duplicated(self):
        keys = [skill.key for skill in SKILL_REGISTRY.values()]
        self.assertEqual(keys.count("wind_blade"), 1)
        self.assertEqual(keys.count("flight"), 1)
        wind_blade = SKILL_REGISTRY["wind_blade"]
        self.assertEqual(wind_blade.cost, {"mp": 14})
        self.assertEqual(wind_blade.label, "風刃術")
        self.assertIs(wind_blade.target_spec, TargetSpec.AREA)
        self.assertIs(wind_blade.element, ELEMENT_REGISTRY["wind"])
        self.assertEqual(wind_blade.effects, ["damage:wind:magic"])
        flight = SKILL_REGISTRY["flight"]
        self.assertEqual(flight.cost, {"mp": 22})
        self.assertIs(flight.kind, SkillKind.PASSIVE)
        self.assertEqual(flight.effects, ["movement:flight"])

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

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-first-round-linear-tree")
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

    @covers_requirement("skill-lineage::the-fire-lineage-ships-as-the-first-round-linear-tree")
    def test_mastery_passives_stay_out_of_the_graph(self):
        for element_key in ELEMENT_REGISTRY:
            mastery_key = f"{element_key}_mastery"
            with self.subTest(mastery_key=mastery_key):
                self.assertEqual(prerequisite_consumers(mastery_key), ())
                self.assertEqual(declared_prerequisites(mastery_key), ())
