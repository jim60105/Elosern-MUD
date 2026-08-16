"""Elemental spell-catalog tests and their pinned catalog constants."""

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
    TargetSpec,
)


FIRE_SPELL_CATALOG = (
    ("fire_ball", "火球術", TargetSpec.SINGLE, 14, ("damage:fire:magic",)),
    ("fire_arrow", "火焰箭", TargetSpec.SINGLE, 10, ("damage:fire:magic",)),
    ("firestorm", "火焰風暴", TargetSpec.AREA, 30, ("damage:fire:magic",)),
    (
        "scorching_wave",
        "灼熱波動",
        TargetSpec.SINGLE,
        24,
        ("damage:fire:magic", "buff_apply:fire_scorch"),
    ),
    ("lava_burst", "熔岩術", TargetSpec.AREA, 52, ("damage:fire:magic",)),
    ("infernal_wrap", "業火纏繞", TargetSpec.SINGLE, 42, ("damage:fire:magic",)),
    ("dragon_flame", "龍炎術", TargetSpec.AREA, 95, ("damage:fire:magic",)),
    ("hellfire", "煉獄業火", TargetSpec.SINGLE, 78, ("damage:fire:magic",)),
    (
        "phoenix_eternal_flame",
        "不滅鳳凰焰",
        TargetSpec.AREA,
        150,
        ("damage:fire:magic", "self_heal"),
    ),
    ("world_ending_blaze", "焚世終焰", TargetSpec.SINGLE, 130, ("damage:fire:magic",)),
)


WATER_SPELL_CATALOG = (
    ("water_bolt", "水箭術", TargetSpec.SINGLE, 12, ("damage:water:magic",)),
    ("minor_heal", "治癒滴露", TargetSpec.SINGLE, 11, ("heal:single",)),
    ("healing_spring", "治癒之泉", TargetSpec.AREA, 28, ("heal:area",)),
    ("water_shield", "水盾術", TargetSpec.SINGLE, 22, ("buff_apply:water_shield",)),
    (
        "abyssal_whirlpool",
        "深海漩渦",
        TargetSpec.AREA,
        50,
        ("damage:water:magic", "buff_apply:water_bind"),
    ),
    ("wellspring_of_life", "生命湧泉", TargetSpec.SINGLE, 40, ("heal:single",)),
    ("tsunami", "海嘯術", TargetSpec.AREA, 95, ("damage:water:magic",)),
    ("tidal_revival", "復生之潮", TargetSpec.SINGLE, 78, ("heal:single",)),
    ("sea_of_life", "生命之海", TargetSpec.AREA, 160, ("heal:area",)),
    ("abyssal_tide", "深淵巨潮", TargetSpec.AREA, 145, ("damage:water:magic",)),
)


EARTH_SPELL_CATALOG = (
    ("stone_shard", "石礫術", TargetSpec.SINGLE, 12, ("damage:earth:magic",)),
    (
        "hardened_skin",
        "硬化肌膚",
        TargetSpec.SELF,
        10,
        ("self_buff_apply:earth_hardened_skin",),
    ),
    ("stone_armor", "岩甲術", TargetSpec.SINGLE, 24, ("buff_apply:earth_stone_armor",)),
    ("dust_veil", "沙塵術", TargetSpec.AREA, 22, ("buff_apply:earth_dust_veil",)),
    ("earth_bind", "地縛術", TargetSpec.AREA, 42, ("buff_apply:earth_root",)),
    ("rockslide", "岩壁崩落", TargetSpec.AREA, 48, ("damage:earth:magic",)),
    ("earthquake", "地震術", TargetSpec.AREA, 90, ("damage:earth:magic",)),
    ("earthen_ward", "大地庇護", TargetSpec.AREA, 75, ("buff_apply:earth_ward",)),
    ("mountain_collapse", "山嶽崩落", TargetSpec.AREA, 150, ("damage:earth:magic",)),
    ("earths_judgment", "大地審判", TargetSpec.SINGLE, 130, ("damage:earth:magic",)),
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
        "靜電護體",
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
        "永夜冰原",
        TargetSpec.AREA,
        158,
        ("damage:ice:magic", "buff_apply:ice_freeze"),
    ),
)


LIGHT_SPELL_CATALOG = (
    ("heal", "治癒術", TargetSpec.SINGLE, 12, ("heal:single",)),
    ("light_arrow", "光箭術", TargetSpec.SINGLE, 14, ("damage:light:magic",)),
    ("purify", "淨化術", TargetSpec.SINGLE, 22, ("cleanse:status",)),
    ("mass_heal", "群體治癒", TargetSpec.AREA, 30, ("heal:area",)),
    ("advanced_heal", "高級治癒", TargetSpec.SINGLE, 46, ("heal:single",)),
    ("holy_shield", "聖盾術", TargetSpec.SINGLE, 40, ("buff_apply:light_holy_shield",)),
    ("holy_radiance", "神聖光輝", TargetSpec.AREA, 90, ("damage:light:magic",)),
    ("revival_light", "復甦之光", TargetSpec.SINGLE, 82, ("heal:single",)),
    (
        "goddess_blessing",
        "女神降福",
        TargetSpec.AREA,
        145,
        ("heal:area", "buff_apply:light_blessing"),
    ),
    (
        "heavens_judgment_light",
        "天啟聖裁",
        TargetSpec.SINGLE,
        135,
        ("damage:light:magic",),
    ),
)


DARK_SPELL_CATALOG = (
    ("shadow_bolt", "暗影箭", TargetSpec.SINGLE, 14, ("damage:dark:magic",)),
    ("weaken", "衰弱術", TargetSpec.SINGLE, 11, ("buff_apply:dark_atk_down",)),
    ("curse", "詛咒術", TargetSpec.SINGLE, 26, ("buff_apply:dark_curse",)),
    ("dark_burst", "闇裂術", TargetSpec.AREA, 29, ("damage:dark:magic",)),
    (
        "dark_corrosion_domain",
        "闇蝕領域",
        TargetSpec.AREA,
        47,
        ("damage:dark:magic", "buff_apply:dark_corrosion"),
    ),
    (
        "shadow_torment",
        "暗影凌遲",
        TargetSpec.SINGLE,
        41,
        ("damage:dark:magic", "buff_apply:dark_corrosion"),
    ),
    ("abyss_devour", "深淵吞噬", TargetSpec.SINGLE, 85, ("damage:dark:magic",)),
    ("dark_dominion", "黑暗支配", TargetSpec.AREA, 72, ("buff_apply:fear",)),
    ("void_annihilation", "終焉黑洞", TargetSpec.AREA, 155, ("damage:dark:magic",)),
    (
        "netherworld_judgment",
        "冥府審判",
        TargetSpec.SINGLE,
        135,
        ("damage:dark:magic",),
    ),
)


_CATALOG_EFFECTS = {
    row[0]: row[4]
    for rows in (
        FIRE_SPELL_CATALOG,
        WATER_SPELL_CATALOG,
        EARTH_SPELL_CATALOG,
        WIND_SPELL_CATALOG,
        LIGHTNING_SPELL_CATALOG,
        ICE_SPELL_CATALOG,
        LIGHT_SPELL_CATALOG,
        DARK_SPELL_CATALOG,
    )
    for row in rows
}


class FireSpellCatalogTests(unittest.TestCase):
    def test_elemental_spells_builder_rejects_unknown_element(self):
        from world.skills.registry import _elemental_spells

        with self.assertRaises(ValueError):
            _elemental_spells(
                "bogus",
                ("x", "X", "說明", TargetSpec.SINGLE, 10, ("damage:fire:magic",)),
            )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-火-element-spell-set")
    def test_all_ten_fire_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in FIRE_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["fire"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-火-element-spell-set")
    def test_every_fire_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in FIRE_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="fire", school="magic"),
                        )
                    elif effect_id.startswith("buff_apply:"):
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key="fire_scorch"),
                        )
                    else:
                        self.assertEqual(parsed, SelfHealEffect())
                    self.assertIn(parsed, skill.parsed_effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-火-element-spell-set")
    def test_fire_ball_was_recosted_in_place_not_duplicated(self):
        self.assertEqual(
            [skill.key for skill in SKILL_REGISTRY.values()].count("fire_ball"),
            1,
        )
        skill = SKILL_REGISTRY["fire_ball"]
        self.assertEqual(skill.cost, {"mp": 14})
        self.assertEqual(skill.label, "火球術")
        self.assertIs(skill.target_spec, TargetSpec.SINGLE)
        self.assertIs(skill.element, ELEMENT_REGISTRY["fire"])
        self.assertEqual(skill.effects, ["damage:fire:magic"])

class WaterSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_all_ten_water_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in WATER_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["water"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_water_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["water"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in WATER_SPELL_CATALOG},
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_every_water_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in WATER_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="water", school="magic"),
                        )
                    elif effect_id.startswith("buff_apply:"):
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key=effect_id.partition(":")[2]),
                        )
                    else:
                        self.assertEqual(
                            parsed,
                            HealEffect(shape=effect_id.partition(":")[2]),
                        )
                    self.assertIn(parsed, skill.parsed_effects)

class EarthSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_all_ten_earth_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in EARTH_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["earth"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)
                if key == "hardened_skin":
                    self.assertIs(
                        skill.faction_constraint,
                        FactionConstraint.SELF_ONLY,
                    )
                else:
                    self.assertIs(skill.faction_constraint, FactionConstraint.ANY)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_earth_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["earth"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in EARTH_SPELL_CATALOG},
        )

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

class LightSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-光-element-spell-set")
    def test_all_ten_light_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in LIGHT_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["light"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-光-element-spell-set")
    def test_every_light_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in LIGHT_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="light", school="magic"),
                        )
                    elif effect_id.startswith("heal:"):
                        self.assertEqual(
                            parsed,
                            HealEffect(shape=effect_id.partition(":")[2]),
                        )
                    elif effect_id.startswith("cleanse:"):
                        self.assertEqual(parsed, CleanseEffect(scope="status"))
                    else:
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key=effect_id.partition(":")[2]),
                        )
                    self.assertIn(parsed, skill.parsed_effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-光-element-spell-set")
    def test_light_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["light"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in LIGHT_SPELL_CATALOG} | {"light_sword_style"},
        )

class DarkSpellCatalogTests(unittest.TestCase):
    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_all_ten_dark_spells_declare_the_exact_catalog_fields(self):
        for key, label, target_spec, mp, effects in DARK_SPELL_CATALOG:
            with self.subTest(spell=key):
                skill = SKILL_REGISTRY[key]
                self.assertEqual(skill.label, label)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.element, ELEMENT_REGISTRY["dark"])
                self.assertIs(skill.target_spec, target_spec)
                self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
                self.assertEqual(skill.cost, {"mp": mp})
                self.assertEqual(tuple(skill.effects), effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_every_dark_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in DARK_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="dark", school="magic"),
                        )
                    else:
                        self.assertEqual(
                            parsed,
                            BuffApplyEffect(buff_key=effect_id.partition(":")[2]),
                        )
                    self.assertIn(parsed, skill.parsed_effects)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_dark_active_spell_keys_are_exactly_the_catalog_set(self):
        self.assertEqual(
            {
                key
                for key, skill in SKILL_REGISTRY.items()
                if skill.element is ELEMENT_REGISTRY["dark"]
                and skill.kind is SkillKind.ACTIVE
            },
            {row[0] for row in DARK_SPELL_CATALOG}
            | {"shadow_slash", "dual_blade_mastery"},
        )
