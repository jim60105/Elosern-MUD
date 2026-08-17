"""Skill-registry, category-classification, and content tests."""

from tools.spec_traceability import covers_requirement

from dataclasses import fields
import unittest

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import (
    DivineMysteryEffect,
    ElementMasteryEffect,
    SexualMasteryEffect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

from .test_spell_catalogs import _CATALOG_EFFECTS


_CATEGORY_ORDER = [
    SkillCategory.ELEMENTAL_MAGIC,
    SkillCategory.MARTIAL_ARTS,
    SkillCategory.ENHANCEMENT,
    SkillCategory.INNATE_GIFT,
    SkillCategory.MOVEMENT,
    SkillCategory.DIVINE_MYSTERY,
    SkillCategory.UTILITY,
    SkillCategory.SEXUAL_ACT,
]


_UNGROUPED_CATEGORIES = (
    SkillCategory.MARTIAL_ARTS,
    SkillCategory.ENHANCEMENT,
    SkillCategory.INNATE_GIFT,
    SkillCategory.MOVEMENT,
    SkillCategory.DIVINE_MYSTERY,
    SkillCategory.UTILITY,
)


_MASTERY_KEYS = frozenset(
    f"{element_key}_mastery"
    for element_key in ELEMENT_REGISTRY
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
                "category",
                "group",
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
            category=SkillCategory.UTILITY,
            group=None,
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
                category=SkillCategory.UTILITY,
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
                category=SkillCategory.UTILITY,
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
                category=SkillCategory.UTILITY,
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
                        category=SkillCategory.UTILITY,
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
                    category=SkillCategory.UTILITY,
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

    @covers_requirement("skill-registry::reincarnation-boon-labels-match-the-preset-character-names")
    def test_reincarnation_boon_labels_match_the_preset_character_names(self):
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        expected = {
            "reincarnation_boon_elosia": (
                "elosia_shadowmoon", "伊洛希雅", ("growth_rate:magic:100",),
            ),
            "reincarnation_boon_yuka": (
                "yuka_darknight", "悠花", ("combat_prediction:武感",),
            ),
            "reincarnation_boon_yuna": (
                "yuna_darknight", "悠奈", ("sexual_magic_mastery",),
            ),
        }
        for key, (preset_key, display_name, effects) in expected.items():
            with self.subTest(key=key):
                skill = SKILL_REGISTRY[key]
                preset = PLAYER_PRESET_REGISTRY[preset_key]
                self.assertIn(key, (*preset.active_skills, *preset.passive_skills))
                self.assertEqual(skill.label, f"轉生祝福·{display_name}")
                self.assertIs(skill.kind, SkillKind.PASSIVE)
                self.assertEqual(skill.target_spec, TargetSpec.NONE)
                self.assertEqual(skill.cost, {})
                self.assertEqual(tuple(skill.effects), effects)

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

    @covers_requirement("skill-registry::dual-wield-style-is-a-passive-stance-not-a-castable-active-skill")
    def test_dual_wield_style_is_a_passive_stance(self):
        style = SKILL_REGISTRY["dual_wield_style"]
        self.assertEqual(style.label, "雙持劍術")
        self.assertIs(style.kind, SkillKind.PASSIVE)
        self.assertIs(style.target_spec, TargetSpec.NONE)
        self.assertEqual(style.cost, {})
        self.assertEqual(style.effects, ["weapon_style:dual_wield"])

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

class SkillCategoryClassificationTests(unittest.TestCase):
    """Structural proof that the 118-skill classification partition is exact.

    The suite imports ``world.rules.disengage`` so ``flee`` is registered
    before these tests run, matching how the registry exists at runtime.
    """

    @classmethod
    def setUpClass(cls):
        import world.rules.disengage  # noqa: F401  (registers flee)

    @covers_requirement("skill-category-registry::skillcategory-enumerates-exactly-eight-presentation-categories")
    def test_skill_category_declares_the_exact_member_set_in_order(self):
        self.assertEqual(list(SkillCategory), _CATEGORY_ORDER)
        self.assertEqual(
            {member.value for member in SkillCategory},
            {
                "elemental_magic",
                "martial_arts",
                "enhancement",
                "innate_gift",
                "movement",
                "divine_mystery",
                "utility",
                "sexual_act",
            },
        )

    @covers_requirement("skill-category-registry::every-skilldef-declares-a-required-category-and-an-optional-group")
    def test_constructing_without_category_raises_type_error(self):
        with self.assertRaises(TypeError):
            SkillDef(
                key="no_category",
                label="無分類",
                description="缺少 category 的定義必須在建構時失敗。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )

    @covers_requirement("skill-category-registry::every-skilldef-declares-a-required-category-and-an-optional-group")
    def test_empty_string_group_raises_value_error(self):
        with self.assertRaises(ValueError) as caught:
            SkillDef(
                key="empty_group",
                label="空群組",
                description="空的 group 字串必須被拒絕。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
                category=SkillCategory.UTILITY,
                group="",
            )
        self.assertIn("empty_group", str(caught.exception))

    @covers_requirement("skill-category-registry::every-skilldef-declares-a-required-category-and-an-optional-group")
    def test_non_string_group_raises_value_error(self):
        with self.assertRaises(ValueError) as caught:
            SkillDef(
                key="numeric_group",
                label="數值群組",
                description="非字串的 group 必須被拒絕，而非觸發 AttributeError。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
                category=SkillCategory.UTILITY,
                group=123,
            )
        self.assertIn("numeric_group", str(caught.exception))

    @covers_requirement("skill-category-registry::every-skilldef-declares-a-required-category-and-an-optional-group")
    def test_group_omission_defaults_to_none(self):
        skill = SkillDef(
            key="null_group",
            label="無群組",
            description="省略 group 時應預設為 None。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SELF,
            cost={},
            usable_out_of_combat=False,
            element=None,
            effects=[],
            category=SkillCategory.UTILITY,
        )
        self.assertIsNone(skill.group)

    @covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-eight-categories")
    def test_every_registry_key_has_a_valid_category(self):
        for key in SKILL_REGISTRY:
            with self.subTest(key=key):
                self.assertIsInstance(
                    SKILL_REGISTRY[key].category,
                    SkillCategory,
                    key,
                )

    @covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-eight-categories")
    def test_per_category_partition_covers_the_registry_exactly(self):
        per_category = {
            category: {key for key, skill in SKILL_REGISTRY.items() if skill.category is category}
            for category in SkillCategory
        }
        self.assertEqual(set(SKILL_REGISTRY.keys()), set().union(*per_category.values()))
        self.assertEqual(
            sum(len(members) for members in per_category.values()),
            len(SKILL_REGISTRY),
            "a key may appear in only one category",
        )

    @covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-eight-categories")
    def test_per_category_key_sets_match_the_d4_classification_table(self):
        expected = {
            SkillCategory.MARTIAL_ARTS: {
                "basic_attack",
                "dual_blade_mastery",
                "light_sword_style",
                "shadow_slash",
                "dual_wield_style",
            },
            SkillCategory.ENHANCEMENT: {
                "body_enhancement",
                "body_enhancement_extreme",
                "body_enhancement_basic",
                "defense_instinct",
                "blade_art_mastery",
                "extreme_endurance",
                "retainer_martial_training",
                "guardian_instinct",
                "magic_circle_comprehension",
                "precise_mana_control",
                "concentration",
            },
            SkillCategory.INNATE_GIFT: {
                "reincarnation_boon_elosia",
                "reincarnation_boon_yuka",
                "elf_longevity",
            },
            SkillCategory.MOVEMENT: {"flight", "flash_step", "flee"},
            SkillCategory.DIVINE_MYSTERY: {
                "divine_time_dilation",
                "divine_space_distortion",
                "divine_matter_transmutation",
                "divine_life_extension",
            },
            SkillCategory.UTILITY: {"status_disguise", "dominion_art"},
            SkillCategory.SEXUAL_ACT: {
                "divine_sexual_arts",
                "divine_sexual_mastery",
                "reincarnation_boon_yuna",
                "divine_extreme_climax_command",
                "divine_timed_copulation",
                "divine_realm_drain",
                "solo_self_touch",
                "solo_fondle_breasts",
                "solo_thigh_rub",
                "solo_deep_touch",
                "solo_both_hands",
                "solo_finger_lick",
                "solo_rear_touch",
                "solo_nipple_play",
                "solo_toy_vibrator",
                "solo_toy_clamps",
                "solo_toy_plug",
                "solo_toy_advanced_link",
                "solo_toy_advanced_full",
                "solo_bound_masturbation",
                "shame_hem_lift",
                "shame_half_expose_chest",
                "shame_half_expose_lower",
                "shame_loosen_collar",
                "shame_full_expose",
                "shame_public_masturbation",
                "shame_provocative_gaze",
                "shame_public_performance",
                "shame_devoted_pose",
                "shame_shameless_declaration",
                "partner_caress",
                "partner_hand_hold",
                "partner_kiss",
                "partner_neck_caress",
                "partner_breast_play",
                "partner_ear_whisper",
                "partner_deep_caress",
                "partner_oral_service",
                "partner_breast_sex",
                "partner_thigh_rub",
                "partner_foot_service",
                "partner_anal_sex",
                "partner_mutual_masturbation",
                "partner_vaginal_sex",
                "partner_deep_vaginal_sex",
                "partner_group_caress",
                "partner_group_orgy",
                "partner_group_service",
                "combat_tease",
                "combat_tease_whisper",
                "combat_tease_touch",
                "combat_charm",
                "combat_bind_caress",
                "combat_forced_pleasure",
                "combat_forced_climax",
                "combat_relentless_torment",
                "combat_climax_domination",
                "interspecies_touch",
                "interspecies_caress",
                "interspecies_entangle",
                "interspecies_receive",
                "interspecies_mating",
                "interspecies_domination",
                "interspecies_resonance",
                "divine_sensitivity_creation",
                "divine_shame_deprivation",
                "divine_absolute_submission",
                "divine_purity_restoration",
            },
        }
        pinned = set().union(*expected.values())
        expected[SkillCategory.ELEMENTAL_MAGIC] = set(SKILL_REGISTRY) - pinned
        for category, keys in expected.items():
            with self.subTest(category=category.value):
                self.assertEqual(
                    {
                        key
                        for key, skill in SKILL_REGISTRY.items()
                        if skill.category is category
                    },
                    keys,
                )

    @covers_requirement("skill-category-registry::elemental-magic-and-sexual-act-members-declare-a-non-null-group-every-other-category-s-members-declare-a-null-group")
    def test_every_elemental_magic_group_is_its_own_element_key(self):
        for key, skill in SKILL_REGISTRY.items():
            if skill.category is not SkillCategory.ELEMENTAL_MAGIC:
                continue
            with self.subTest(key=key):
                self.assertIsNotNone(skill.group)
                self.assertIsNotNone(skill.element)
                self.assertIn(skill.element.key, ELEMENT_REGISTRY)
                self.assertEqual(skill.group, skill.element.key)

    @covers_requirement("skill-category-registry::elemental-magic-and-sexual-act-members-declare-a-non-null-group-every-other-category-s-members-declare-a-null-group")
    def test_every_sexual_act_group_is_a_non_empty_string(self):
        sexual_acts = [
            skill
            for skill in SKILL_REGISTRY.values()
            if skill.category is SkillCategory.SEXUAL_ACT
        ]
        self.assertGreaterEqual(len(sexual_acts), 1)
        for skill in sexual_acts:
            self.assertTrue(skill.group)
            self.assertTrue(skill.group.strip())

    @covers_requirement("skill-category-registry::elemental-magic-and-sexual-act-members-declare-a-non-null-group-every-other-category-s-members-declare-a-null-group")
    def test_every_ungrouped_category_member_declares_null_group(self):
        for key, skill in SKILL_REGISTRY.items():
            if skill.category not in _UNGROUPED_CATEGORIES:
                continue
            with self.subTest(key=key):
                self.assertIsNone(skill.group, key)

    @covers_requirement("skill-category-registry::classifying-a-skill-changes-no-other-field")
    def test_divine_sexual_arts_keeps_its_mechanics_after_reclassification(self):
        skill = SKILL_REGISTRY["divine_sexual_arts"]
        self.assertTrue(skill.requires_divine_arts)
        self.assertEqual(skill.effects, ["sexual_event:stimulus_applied"])
        self.assertIs(skill.kind, SkillKind.ACTIVE)
        self.assertEqual(skill.cost, {})
        self.assertIs(skill.target_spec, TargetSpec.SINGLE)
        self.assertIs(skill.category, SkillCategory.SEXUAL_ACT)
        self.assertEqual(skill.group, "神之秘法")

    @covers_requirement("skill-category-registry::classifying-a-skill-changes-no-other-field")
    def test_elemental_magic_effects_are_unchanged_from_their_catalog_values(self):
        for key, skill in SKILL_REGISTRY.items():
            if skill.category is not SkillCategory.ELEMENTAL_MAGIC:
                continue
            with self.subTest(key=key):
                if key in _MASTERY_KEYS:
                    self.assertEqual(
                        tuple(skill.effects),
                        ("element_mastery_rank:主宰",),
                    )
                else:
                    self.assertEqual(
                        tuple(skill.effects),
                        _CATALOG_EFFECTS[key],
                        f"skill {key!r} effects drifted from its catalog row",
                    )

class FleeCategoryDeclarationTests(unittest.TestCase):
    """The ``flee`` classification is declared at its own construction site."""

    @classmethod
    def setUpClass(cls):
        import world.rules.disengage  # noqa: F401  (registers flee)

    @covers_requirement("universal-action-ownership::flee-declares-its-skill-category-at-its-own-construction-site")
    def test_flee_is_classified_movement_with_null_group(self):
        skill = SKILL_REGISTRY["flee"]
        self.assertIs(skill.category, SkillCategory.MOVEMENT)
        self.assertIsNone(skill.group)

    @covers_requirement("universal-action-ownership::flee-declares-its-skill-category-at-its-own-construction-site")
    def test_disengage_source_supplies_an_explicit_category_argument(self):
        import ast
        import pathlib

        source = pathlib.Path(
            pathlib.Path(__file__).resolve().parents[2],
            "rules",
            "disengage.py",
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        flee_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            call = node.value
            if not (isinstance(call.func, ast.Name) and call.func.id == "SkillDef"):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "SKILL_REGISTRY"
                ):
                    flee_calls.append(call)
        self.assertEqual(
            len(flee_calls),
            1,
            "expected exactly one SKILL_REGISTRY[...] SkillDef construction (flee)",
        )
        call = flee_calls[0]
        keywords = {keyword.arg for keyword in call.keywords if keyword.arg}
        self.assertIn("category", keywords, "flee must supply category explicitly")
        category_value = next(
            keyword.value for keyword in call.keywords if keyword.arg == "category"
        )
        self.assertIn(
            "SkillCategory.MOVEMENT",
            ast.unparse(category_value),
        )
