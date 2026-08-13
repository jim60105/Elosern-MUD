"""Contract tests for the skill registry."""

from tools.spec_traceability import covers_requirement

from dataclasses import fields
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.elements import ELEMENT_REGISTRY, Element
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.skills.effects import (
    BuffApplyEffect,
    DamageEffect,
    DivineMysteryEffect,
    ElementMasteryEffect,
    HealEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SexualMasteryEffect,
    parse_effect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)


class SkillRegistryTests(unittest.TestCase):
    def test_registry_uses_the_exact_forward_declared_contract(self):
        self.assertTrue(SKILL_REGISTRY)
        self.assertEqual(
            [field.name for field in fields(SkillDef)],
            [
                "key",
                "label",
                "description",
                "kind",
                "target_spec",
                "cost",
                "usable_out_of_combat",
                "element",
                "effects",
                "faction_constraint",
                "requires_divine_arts",
                "parsed_effects",
            ],
        )
        for key, skill in SKILL_REGISTRY.items():
            self.assertEqual(skill.key, key)
            self.assertIsInstance(skill.kind, SkillKind)
            self.assertIsInstance(skill.target_spec, TargetSpec)
            self.assertTrue(
                all(type(value) is int and value >= 0 for value in skill.cost.values())
            )
            if skill.element is not None:
                self.assertIsInstance(skill.element, Element)
                self.assertIn(skill.element, ELEMENT_REGISTRY.values())
            self.assertIsInstance(skill.faction_constraint, FactionConstraint)

    @covers_requirement(
        "skill-registry::skills-declare-only-self-only-or-free-target-scope"
    )
    def test_every_definition_has_bounded_player_facing_metadata(self):
        for skill in SKILL_REGISTRY.values():
            self.assertTrue(skill.label.strip())
            self.assertTrue(skill.description.strip())
            self.assertLessEqual(
                sum(1 for _ in skill.label),
                128,
                f"skill {skill.key!r} label exceeds 128 code points",
            )
            self.assertLessEqual(
                sum(1 for _ in skill.description),
                512,
                f"skill {skill.key!r} description exceeds 512 code points",
            )
            self.assertFalse("\n" in skill.label or "\n" in skill.description)

    @covers_requirement("skill-registry::skills-declare-only-self-only-or-free-target-scope")
    def test_no_skill_is_enemy_or_ally_restricted(self):
        for key, skill in SKILL_REGISTRY.items():
            self.assertIn(
                skill.faction_constraint,
                (FactionConstraint.ANY, FactionConstraint.SELF_ONLY),
                f"skill {key!r} must not declare an ENEMY/ALLY-only constraint",
            )
        for key in ("basic_attack", "fire_ball", "wind_blade", "shadow_slash"):
            self.assertIs(
                SKILL_REGISTRY[key].faction_constraint,
                FactionConstraint.ANY,
                key,
            )

    def test_self_only_constraint_is_available_for_self_effects(self):
        # The enum keeps SELF_ONLY for self-only effects; the shipped flee
        # innate skill is the only self-only consumer today.
        self.assertIn(FactionConstraint.SELF_ONLY, FactionConstraint)
        from world.rules.disengage import FLEE_SKILL_KEY

        self.assertIs(
            SKILL_REGISTRY[FLEE_SKILL_KEY].faction_constraint,
            FactionConstraint.SELF_ONLY,
        )

    def test_constructing_without_metadata_fails_closed(self):
        with self.assertRaises(TypeError):
            SkillDef(
                key="no_metadata",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )

    def test_metadata_bounds_reject_empty_and_oversized_values(self):
        from world.skills.registry import _validate_metadata

        for bad_label, bad_description in (
            ("", "說明"),
            ("   ", "說明"),
            ("標籤", ""),
            ("標籤", "   "),
            ("標" * 129, "說明"),
            ("標籤", "說" * 513),
        ):
            with self.subTest(label=bad_label, description=bad_description):
                with self.assertRaises(ValueError):
                    _validate_metadata(bad_label, bad_description)


    @covers_requirement("skill-registry::skillkind-and-targetspec-are-forward-declared-for-change-8-to-import")
    def test_enums_have_only_the_forward_declared_members(self):
        self.assertEqual(set(SkillKind.__members__), {"ACTIVE", "PASSIVE"})
        self.assertEqual(
            set(TargetSpec.__members__),
            {"NONE", "SELF", "SINGLE", "AREA"},
        )
        self.assertFalse(
            {
                name
                for name, value in SkillKind.__dict__.items()
                if callable(value) and not name.startswith("_")
            }
        )
        self.assertFalse(
            {
                name
                for name, value in TargetSpec.__dict__.items()
                if callable(value) and not name.startswith("_")
            }
        )

    @covers_requirement("skill-registry::all-eight-elements-have-a-mastery-skill")
    def test_all_eight_elements_have_a_mastery_skill(self):
        for element_key in (
            "fire",
            "water",
            "wind",
            "earth",
            "lightning",
            "ice",
            "light",
            "dark",
        ):
            with self.subTest(element=element_key):
                skill = SKILL_REGISTRY[f"{element_key}_mastery"]
                self.assertIs(skill.kind, SkillKind.PASSIVE)
                self.assertIs(skill.target_spec, TargetSpec.NONE)
                self.assertIs(skill.element, ELEMENT_REGISTRY[element_key])
                self.assertEqual(skill.effects, ["element_mastery_rank:主宰"])

    @covers_requirement("skill-registry::the-seed-registry-spans-every-skill-category-inventoried-from-the-sample-cards")
    def test_seed_set_spans_every_required_category(self):
        for key in (
            "body_enhancement",
            "body_enhancement_extreme",
            "body_enhancement_basic",
            "fire_mastery",
            "dark_mastery",
            "wind_mastery",
            "light_mastery",
            "fire_ball",
            "wind_blade",
            "dual_wield_style",
            "status_disguise",
            "dominion_art",
            "elf_longevity",
        ):
            self.assertIn(key, SKILL_REGISTRY)

        multipliers = {
            effect.rsplit(":", 1)[-1]
            for skill in SKILL_REGISTRY.values()
            for effect in skill.effects
            if effect.startswith("stat_multiply:")
        }
        self.assertTrue({"1.2", "100", "1000"} <= multipliers)

        for element_key in ("fire", "dark", "wind", "light"):
            skill = SKILL_REGISTRY[f"{element_key}_mastery"]
            self.assertIs(skill.kind, SkillKind.PASSIVE)
            self.assertIs(skill.element, ELEMENT_REGISTRY[element_key])

        conferral = [
            skill
            for skill in SKILL_REGISTRY.values()
            if "confer_skill_partial" in skill.effects
        ]
        disguises = [
            skill
            for skill in SKILL_REGISTRY.values()
            if "set_disguise" in skill.effects
        ]
        self.assertEqual(len(conferral), 1)
        self.assertEqual(len(disguises), 1)
        self.assertTrue(all(skill.kind is SkillKind.ACTIVE for skill in conferral + disguises))

        boons = [
            skill
            for key, skill in SKILL_REGISTRY.items()
            if key.startswith("reincarnation_boon_")
        ]
        self.assertGreaterEqual(len(boons), 3)
        self.assertEqual(len({tuple(skill.effects) for skill in boons}), len(boons))

    @covers_requirement("skill-registry::skills-declare-only-self-only-or-free-target-scope")
    def test_definition_collections_are_deeply_immutable(self):
        fire_ball = SKILL_REGISTRY["fire_ball"]
        with self.assertRaises(TypeError):
            fire_ball.cost["mp"] = 0
        with self.assertRaises(TypeError):
            fire_ball.effects.append("damage:unbounded")

    def test_direct_construction_observes_immutability_and_metadata_bounds(self):
        skill = SkillDef(
            key="direct",
            label="直接定義",
            description="直接建構的定義也受同一不變條件保護。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SELF,
            cost={"mp": 5},
            usable_out_of_combat=False,
            element=None,
            effects=["set_disguise"],
        )
        with self.assertRaises(TypeError):
            skill.cost["mp"] = 0
        with self.assertRaises(TypeError):
            skill.effects.append("unbounded")
        with self.assertRaises(ValueError):
            SkillDef(
                key="direct_bad",
                label="   ",
                description="說明",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )
        with self.assertRaises(ValueError):
            SkillDef(
                key="direct_long",
                label="標籤",
                description="說" * 513,
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )
        # Every registered definition, including the dynamically registered
        # production `flee`, stays immutable at runtime.
        for registered in SKILL_REGISTRY.values():
            with self.assertRaises(TypeError):
                registered.effects.append("unbounded")
            with self.assertRaises(TypeError):
                registered.cost["mp"] = 0

    @covers_requirement("skill-effect-model::skilldef---post-init---rejects-unparseable-effects-at-construction")
    def test_construction_rejects_unrecognized_effect_prefix(self):
        with self.assertRaises(ValueError):
            SkillDef(
                key="unknown_effect",
                label="未知效果",
                description="帶有無法辨識效果前綴的定義必須在建構時失敗。",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=["not_a_real_prefix:x"],
            )

    @covers_requirement("heal-effect-handler::heal-effect-prefix-restores-hp-capped-at-max")
    def test_construction_rejects_a_heal_shape_mismatching_the_target_spec(self):
        for target_spec, effects in (
            (TargetSpec.AREA, ["heal:single"]),
            (TargetSpec.SINGLE, ["heal:area"]),
            (TargetSpec.NONE, ["heal:single"]),
        ):
            with self.subTest(target_spec=target_spec, effects=effects):
                with self.assertRaises(ValueError):
                    SkillDef(
                        key="shape_mismatch",
                        label="形狀不符",
                        description="治療效果的形狀必須與目標規格一致。",
                        kind=SkillKind.ACTIVE,
                        target_spec=target_spec,
                        cost={"mp": 5},
                        usable_out_of_combat=True,
                        element=None,
                        effects=effects,
                    )
        for target_spec, effects in (
            (TargetSpec.SINGLE, ["heal:single"]),
            (TargetSpec.SELF, ["heal:single"]),
            (TargetSpec.AREA, ["heal:area"]),
            (TargetSpec.NONE, ["self_heal"]),
            (TargetSpec.SINGLE, ["damage:fire:magic", "self_heal"]),
        ):
            with self.subTest(target_spec=target_spec, effects=effects):
                SkillDef(
                    key="shape_match",
                    label="形狀相符",
                    description="治療效果的形狀與目標規格一致的定義可以建構。",
                    kind=SkillKind.ACTIVE,
                    target_spec=target_spec,
                    cost={"mp": 5},
                    usable_out_of_combat=True,
                    element=None,
                    effects=effects,
                )

    @covers_requirement("skill-effect-model::skilldef---post-init---rejects-unparseable-effects-at-construction")
    def test_every_registry_entry_parses_at_construction(self):
        for key, skill in SKILL_REGISTRY.items():
            if skill.effects:
                self.assertTrue(
                    skill.parsed_effects,
                    f"skill {key!r} declares effects but parsed none",
                )
            else:
                self.assertEqual(skill.parsed_effects, ())

    @covers_requirement("skill-registry::body-enhancement-family-is-passive-not-active")
    def test_body_enhancement_family_is_passive_not_active(self):
        for key in (
            "body_enhancement",
            "body_enhancement_extreme",
            "body_enhancement_basic",
        ):
            self.assertIs(
                SKILL_REGISTRY[key].kind,
                SkillKind.PASSIVE,
                key,
            )

    @covers_requirement("skill-registry::flight-and-flash-step-are-passive")
    def test_flight_and_flash_step_are_passive(self):
        for key in ("flight", "flash_step"):
            self.assertIs(
                SKILL_REGISTRY[key].kind,
                SkillKind.PASSIVE,
                key,
            )

    @covers_requirement("skill-registry::reincarnation-boon-yuna-s-effect-string-is-well-formed")
    def test_reincarnation_boon_yuna_parses_as_sexual_mastery_effect(self):
        parsed = SKILL_REGISTRY["reincarnation_boon_yuna"].parsed_effects
        self.assertEqual(len(parsed), 1)
        self.assertIsInstance(parsed[0], SexualMasteryEffect)
        self.assertFalse(
            any(isinstance(effect, ElementMasteryEffect) for effect in parsed)
        )


class SkillContentCompletionTests(unittest.TestCase):
    @covers_requirement("skill-registry::guardian-instinct-and-blade-art-mastery-display-text-reflects-character-sheet-flavor")
    def test_guardian_instinct_display_text_matches_character_sheet(self):
        skill = SKILL_REGISTRY["guardian_instinct"]
        self.assertEqual(skill.label, "護主本能")
        self.assertIn("守護主人", skill.description)
        self.assertIs(skill.kind, SkillKind.PASSIVE)
        self.assertEqual(skill.effects, ["passive_buff:guardian_instinct"])

    @covers_requirement("skill-registry::guardian-instinct-and-blade-art-mastery-display-text-reflects-character-sheet-flavor")
    def test_blade_art_mastery_description_covers_both_arts(self):
        skill = SKILL_REGISTRY["blade_art_mastery"]
        self.assertEqual(skill.label, "劍術精通")
        self.assertIn("劍術", skill.description)
        self.assertIn("刀術", skill.description)
        self.assertIs(skill.kind, SkillKind.PASSIVE)
        self.assertEqual(skill.effects, ["passive_buff:blade_arts"])

    @covers_requirement("skill-registry::dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style")
    def test_dual_blade_mastery_is_a_higher_tier_sibling(self):
        skill = SKILL_REGISTRY["dual_blade_mastery"]
        self.assertEqual(skill.label, "雙刀流·宗師級")
        self.assertIs(skill.kind, SkillKind.ACTIVE)
        self.assertIs(skill.target_spec, TargetSpec.SINGLE)
        self.assertEqual(skill.cost, {"sp": 30})
        self.assertIs(skill.element, ELEMENT_REGISTRY["dark"])
        self.assertIs(skill.faction_constraint, FactionConstraint.ANY)
        self.assertEqual(skill.effects, ["damage:dark:physical"])

        style = SKILL_REGISTRY["dual_wield_style"]
        self.assertEqual(style.label, "雙持劍術")
        self.assertEqual(style.cost, {"sp": 8})
        self.assertEqual(style.effects, ["weapon_style:dual_wield"])


class DualBladeMasteryCastTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="dual blade actor")
        self.target = create_object(PlayerCharacter, key="dual blade target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.db.skills = {"active": ["dual_blade_mastery"], "passive": []}
        self.target.db.skills = {"active": [], "passive": []}
        battlefield = Battlefield(
            {
                "party": frozenset({"dual blade actor"}),
                "foes": frozenset({"dual blade target"}),
            },
            {"dual blade actor": self.actor, "dual blade target": self.target},
        )
        self.request = ActionRequest(
            self.actor,
            "dual_blade_mastery",
            [self.target],
            BattlefieldActionContext(battlefield),
        )

    @covers_requirement("skill-registry::dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style")
    def test_cast_resolves_via_damage_handler_without_dual_wield_style(self):
        self.assertNotIn("dual_wield_style", self.actor.skills.owned_keys())
        before = self.target.traits.hp.value
        sp_before = self.actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertLess(self.target.traits.hp.value, before)
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries[:2]],
            ["roll", "damage"],
        )
        self.assertEqual(self.actor.traits.sp.value, sp_before - 30)

    @covers_requirement("skill-registry::dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style")
    def test_dual_wield_style_ownership_has_no_bearing_on_cost(self):
        self.actor.db.skills = {
            "active": ["dual_blade_mastery", "dual_wield_style"],
            "passive": [],
        }
        self.assertIn("dual_wield_style", self.actor.skills.owned_keys())
        sp_before = self.actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.sp.value, sp_before - 30)


class LightSwordStyleCastTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="light sword actor")
        self.target = create_object(PlayerCharacter, key="light sword target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.db.skills = {"active": ["light_sword_style"], "passive": []}
        self.target.db.skills = {"active": [], "passive": []}
        battlefield = Battlefield(
            {
                "party": frozenset({"light sword actor"}),
                "foes": frozenset({"light sword target"}),
            },
            {"light sword actor": self.actor, "light sword target": self.target},
        )
        self.request = ActionRequest(
            self.actor,
            "light_sword_style",
            [self.target],
            BattlefieldActionContext(battlefield),
        )

    @covers_requirement("skill-registry::light-sword-style-deals-damage-via-the-standard-damage-convention")
    def test_light_sword_style_declares_the_damage_convention(self):
        skill = SKILL_REGISTRY["light_sword_style"]
        self.assertEqual(skill.effects, ["damage:light:physical"])
        self.assertIs(skill.element, ELEMENT_REGISTRY["light"])

    @covers_requirement("skill-registry::light-sword-style-deals-damage-via-the-standard-damage-convention")
    def test_cast_resolves_and_deals_light_elemental_physical_damage(self):
        before = self.target.traits.hp.value
        sp_before = self.actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertLess(self.target.traits.hp.value, before)
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries[:2]],
            ["roll", "damage"],
        )
        self.assertEqual(self.actor.traits.sp.value, sp_before - 6)


class DivineMysteryRegistryTests(unittest.TestCase):
    @covers_requirement("skill-registry::divine-sexual-mastery-and-divine-sexual-arts-exist-as-distinct-skills", "divine-mystery::unmechanized-divine-mysteries-are-explicitly-declared-not-silently-missing")
    def test_divine_mystery_family_ships_mechanized_and_flavor_entries(self):
        mastery = SKILL_REGISTRY["divine_sexual_mastery"]
        self.assertIs(mastery.kind, SkillKind.PASSIVE)
        self.assertEqual(mastery.effects, ["sexual_magic_mastery"])

        arts = SKILL_REGISTRY["divine_sexual_arts"]
        self.assertIs(arts.kind, SkillKind.ACTIVE)
        self.assertIs(arts.target_spec, TargetSpec.SINGLE)
        self.assertTrue(arts.usable_out_of_combat)
        self.assertEqual(arts.cost, {})
        self.assertEqual(arts.effects, ["sexual_event:stimulus_applied"])

        disguised = SKILL_REGISTRY["status_disguise"]
        self.assertIn("神之秘法", disguised.label)
        self.assertEqual(disguised.effects, ["set_disguise"])
        self.assertFalse(disguised.requires_divine_arts)

        for key, name in (
            ("divine_time_dilation", "時間加速"),
            ("divine_space_distortion", "空間扭曲"),
            ("divine_matter_transmutation", "物質轉換"),
            ("divine_life_extension", "生命延續"),
        ):
            with self.subTest(skill=key):
                skill = SKILL_REGISTRY[key]
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertIs(skill.target_spec, TargetSpec.NONE)
                self.assertTrue(skill.usable_out_of_combat)
                self.assertEqual(skill.effects, [f"divine_mystery:{name}"])
                self.assertEqual(
                    skill.parsed_effects,
                    (DivineMysteryEffect(name=name, mechanized=False),),
                )

        for key in (
            "divine_sexual_mastery",
            "divine_sexual_arts",
            "divine_time_dilation",
            "divine_space_distortion",
            "divine_matter_transmutation",
            "divine_life_extension",
        ):
            with self.subTest(gated=key):
                self.assertTrue(
                    SKILL_REGISTRY[key].requires_divine_arts,
                    key,
                )
        self.assertFalse(
            SKILL_REGISTRY["reincarnation_boon_yuna"].requires_divine_arts
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


class EarthHardenedSkinCastTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="hardened skin actor")
        self.other = create_object(PlayerCharacter, key="hardened skin other")
        for entity in (self.actor, self.other):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.db.skills = {"active": ["hardened_skin"], "passive": []}
        self.other.db.skills = {"active": [], "passive": []}
        battlefield = Battlefield(
            {
                "party": frozenset({"hardened skin actor"}),
                "foes": frozenset({"hardened skin other"}),
            },
            {"hardened skin actor": self.actor, "hardened skin other": self.other},
        )
        self.context = BattlefieldActionContext(battlefield)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_self_cast_applies_the_buff_to_the_caster(self):
        request = ActionRequest(
            self.actor,
            "hardened_skin",
            [],
            self.context,
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertIn("earth_hardened_skin", self.actor.buffs.all)
        self.assertNotIn("earth_hardened_skin", self.other.buffs.all)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_cast_at_an_explicit_other_target_is_rejected(self):
        request = ActionRequest(
            self.actor,
            "hardened_skin",
            [self.other],
            self.context,
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.TARGET_SPEC_MISMATCH)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_every_earth_spell_effect_round_trips_through_typed_dispatch(self):
        for key, _label, _target_spec, _mp, effects in EARTH_SPELL_CATALOG:
            skill = SKILL_REGISTRY[key]
            for effect_id in effects:
                with self.subTest(spell=key, effect=effect_id):
                    parsed = parse_effect(effect_id)
                    if effect_id.startswith("damage:"):
                        self.assertEqual(
                            parsed,
                            DamageEffect(element="earth", school="magic"),
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
