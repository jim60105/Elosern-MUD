"""Data-contract test: skill registry content contract
Slice of ``test_skill_registry``: SkillCategoryClassificationTests, FleeCategoryDeclarationTests.
"""
from tools.spec_traceability import covers_requirement
import ast
from dataclasses import fields
import pathlib
import unittest
from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import (
    DamageEffect,
    HealEffect,
    RevealDisguiseEffect,
    SelfHealEffect,
    SexualMasteryEffect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    prerequisite_consumers,
    validate_prerequisite_graph,
)
from world.rules.progression import proficiency_cap
from ..test_spell_catalogs import _CATALOG_EFFECTS

from ._support import (
    _CATEGORY_ORDER,
    _UNGROUPED_CATEGORIES,
    _MASTERY_KEYS,
)

class SkillCategoryClassificationTests(unittest.TestCase):
    """Structural proof that the skill classification partition is exact.

    The suite imports ``world.rules.disengage`` so ``flee`` is registered
    before these tests run, matching how the registry exists at runtime.
    """

    @classmethod
    def setUpClass(cls):
        import world.rules.disengage  # noqa: F401  (registers flee)

    @covers_requirement("skill-category-registry::skillcategory-enumerates-exactly-six-presentation-categories")
    def test_skill_category_declares_the_exact_member_set_in_order(self):
        self.assertEqual(list(SkillCategory), _CATEGORY_ORDER)
        self.assertEqual(
            {member.value for member in SkillCategory},
            {
                "elemental_magic",
                "martial_arts",
                "enhancement",
                "divine_mystery",
                "utility",
                "sexual_act",
            },
        )
        self.assertNotIn("movement", {member.value for member in SkillCategory})
        self.assertNotIn("innate_gift", {member.value for member in SkillCategory})

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

    @covers_requirement("skill-registry::skills-declare-only-self-only-or-free-target-scope")
    def test_string_element_normalizes_to_the_registry_element(self):
        """Direct SkillDef(...) authors pass a string key; consumers read
        ``skill.element.key`` (practice XP, freeform ladder), so every
        constructor path must yield an Element, never a raw str."""
        skill = SkillDef(
            key="str_element",
            label="字串屬性",
            description="直接建構時以字串宣告的屬性必須正規化為 Element。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={"mp": 4},
            usable_out_of_combat=False,
            element="fire",
            effects=["damage:fire:magic"],
            category=SkillCategory.UTILITY,
        )
        self.assertIs(skill.element, ELEMENT_REGISTRY["fire"])
        self.assertEqual(skill.element.key, "fire")
        with self.assertRaises(ValueError) as caught:
            SkillDef(
                key="bad_element",
                label="未知屬性",
                description="未知屬性字串必須在建構時失敗。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={},
                usable_out_of_combat=False,
                element="not_an_element",
                effects=[],
                category=SkillCategory.UTILITY,
            )
        self.assertIn("bad_element", str(caught.exception))

    @covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-six-categories")
    def test_every_registry_key_has_a_valid_category(self):
        for key in SKILL_REGISTRY:
            with self.subTest(key=key):
                self.assertIsInstance(
                    SKILL_REGISTRY[key].category,
                    SkillCategory,
                    key,
                )

    @covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-six-categories")
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

    @covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-six-categories")
    def test_per_category_key_sets_match_the_d4_classification_table(self):
        expected = {
            SkillCategory.MARTIAL_ARTS: {
                "basic_attack",
                "light_sword_style",
                "dual_wield_style",
                "flee",
                "basic_swordplay",
                "flowing_strikes",
                "tendon_sever",
                "whirlwind_slash",
                "thousand_blade_art",
                "blade_storm",
                "blade_saint_arts",
                "thousand_army_slash",
                "true_sword_saint",
                "shadow_slash",
                "phantom_dance",
                "dual_blade_waltz",
                "shadow_veil_execution",
                "shadow_dance_finale",
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
                "pain_to_pleasure",
                "rapture_renewal",
                "priestly_grace",
                "saintess_vessel",
                "vow_of_service",
                "rite_heal_light",
                "rite_cleanse",
                "rite_calm",
                "rite_bless_water",
                "rite_sanctify_ground",
                "rite_absolution",
                "rite_lamb_mark",
                "rite_martyrdom_vow",
                "reincarnation_boon_elosia",
                "reincarnation_boon_yuka",
                "elf_longevity",
                "flight",
                "flash_step",
            },
            SkillCategory.DIVINE_MYSTERY: {
                "dominion_art",
                "dominion_recall",
                "shared_dominion",
                "sovereign_investiture",
                "mentors_covenant",
                "chorus_of_ages",
                "undying_tutelage",
                "status_disguise",
                "bestowed_veil",
                "true_name_sight",
                "crown_apotheosis",
            },
            SkillCategory.UTILITY: set(),
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
                "rite_anointing_touch",
                "rite_milk_blessing",
                "rite_holy_kiss",
                "rite_confession_bed",
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

    @covers_requirement("skill-category-registry::category-group-vocabulary-is-closed-per-category")
    def test_every_elemental_magic_group_is_its_own_element_key(self):
        for key, skill in SKILL_REGISTRY.items():
            if skill.category is not SkillCategory.ELEMENTAL_MAGIC:
                continue
            with self.subTest(key=key):
                self.assertIsNotNone(skill.group)
                self.assertIsNotNone(skill.element)
                self.assertIn(skill.element.key, ELEMENT_REGISTRY)
                self.assertEqual(skill.group, skill.element.key)

    @covers_requirement("skill-category-registry::category-group-vocabulary-is-closed-per-category")
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

    @covers_requirement("skill-category-registry::category-group-vocabulary-is-closed-per-category")
    def test_enhancement_display_tags_match_closed_vocabulary(self):
        innate_traits = {"elf_longevity", "reincarnation_boon_elosia", "reincarnation_boon_yuka"}
        movement_passives = {"flight", "flash_step"}
        enhancements = [
            skill for skill in SKILL_REGISTRY.values()
            if skill.category is SkillCategory.ENHANCEMENT
        ]
        self.assertGreaterEqual(len(enhancements), 5)
        for skill in enhancements:
            with self.subTest(key=skill.key):
                if skill.key in innate_traits:
                    self.assertEqual(skill.group, "天賦")
                elif skill.key in movement_passives:
                    self.assertEqual(skill.group, "身法")
                else:
                    self.assertIsNone(skill.group)

    @covers_requirement("skill-category-registry::category-group-vocabulary-is-closed-per-category")
    def test_every_ungrouped_category_member_declares_null_group(self):
        for key, skill in SKILL_REGISTRY.items():
            if skill.category not in _UNGROUPED_CATEGORIES:
                continue
            with self.subTest(key=key):
                self.assertIsNone(skill.group, key)

    @covers_requirement("skill-category-registry::classifying-a-skill-changes-no-other-field")
    def test_rehomed_acquired_passives_keep_their_mechanics(self):
        flight = SKILL_REGISTRY["flight"]
        self.assertIs(flight.kind, SkillKind.PASSIVE)
        self.assertEqual(flight.cost, {})
        self.assertEqual(flight.effects, ["movement:flight"])
        self.assertEqual(flight.element.key, "wind")
        self.assertIs(flight.category, SkillCategory.ENHANCEMENT)
        self.assertEqual(flight.group, "身法")

        yuka = SKILL_REGISTRY["reincarnation_boon_yuka"]
        self.assertIs(yuka.kind, SkillKind.PASSIVE)
        self.assertEqual(yuka.effects, ["combat_prediction:武感"])
        self.assertIs(yuka.category, SkillCategory.ENHANCEMENT)
        self.assertEqual(yuka.group, "天賦")

    @covers_requirement("skill-category-registry::classifying-a-skill-changes-no-other-field")
    def test_divine_sexual_arts_keeps_its_mechanics_after_reclassification(self):
        skill = SKILL_REGISTRY["divine_sexual_arts"]
        self.assertTrue(skill.requires_divine_arts)
        # The one authorised post-classification effects rewrite: the
        # integrate-divine-sexual-arts-catalog prefix migration of the same
        # declared event (sexual_event: -> sexual_event_target:). No other
        # field of the entry changed.
        self.assertEqual(skill.effects, ["sexual_event_target:stimulus_applied"])
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
                        ("passive_trait:element_mastery",),
                    )
                elif key in _CATALOG_EFFECTS:
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
    def test_flee_is_classified_martial_arts_with_null_group(self):
        skill = SKILL_REGISTRY["flee"]
        self.assertIs(skill.category, SkillCategory.MARTIAL_ARTS)
        self.assertIsNone(skill.group)

    @covers_requirement("universal-action-ownership::flee-declares-its-skill-category-at-its-own-construction-site")
    def test_disengage_source_supplies_an_explicit_category_argument(self):
        import ast
        import pathlib

        source = pathlib.Path(
            # Package split: one directory deeper than the flat module.
            pathlib.Path(__file__).resolve().parents[3],
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
            "SkillCategory.MARTIAL_ARTS",
            ast.unparse(category_value),
        )
