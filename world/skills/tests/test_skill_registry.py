"""Data-contract test: skill registry content contract
Skill-registry, category-classification, and content tests."""

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

from .test_spell_catalogs import _CATALOG_EFFECTS


_CATEGORY_ORDER = [
    SkillCategory.ELEMENTAL_MAGIC,
    SkillCategory.MARTIAL_ARTS,
    SkillCategory.ENHANCEMENT,
    SkillCategory.DIVINE_MYSTERY,
    SkillCategory.UTILITY,
    SkillCategory.SEXUAL_ACT,
]


_UNGROUPED_CATEGORIES = (
    SkillCategory.MARTIAL_ARTS,
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
                "effect_policies",
                "parsed_effects",
                "prerequisites",
                "cast_conditions",
                "interaction",
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

    @covers_requirement(
        "affinity-friendly-fire::shipped-content-provides-reachable-friendly-fire-triggers"
    )
    def test_shipped_set_provides_any_faction_area_and_single_target_damage(self):
        # affinity-friendly-fire reachability contract: the penalty and
        # auto-leave flow must stay playable through ordinary player actions,
        # so the shipped registry must keep at least one ANY-faction active
        # AREA damage skill AND one ANY-faction active single-target damage
        # skill. Shape-based existence (never specific keys) so a content
        # rename cannot silently strand the friendly-fire contract.
        damaging = [
            skill
            for skill in SKILL_REGISTRY.values()
            if skill.kind is SkillKind.ACTIVE
            and skill.faction_constraint is FactionConstraint.ANY
            and any(effect.startswith("damage:") for effect in skill.effects)
        ]
        self.assertTrue(
            any(skill.target_spec is TargetSpec.AREA for skill in damaging),
            "shipped set lost its ANY-faction AREA damage path",
        )
        self.assertTrue(
            any(skill.target_spec is TargetSpec.SINGLE for skill in damaging),
            "shipped set lost its ANY-faction single-target damage path",
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

    @covers_requirement("sexual-act-seeds::a-single-target-sexual-act-cannot-be-self-cast")
    def test_every_skill_states_its_targeting_rule(self):
        # The shared resolver consumes the rules-side requirement_for(skill),
        # derived from the definition's declared fields: shape and faction
        # mirror them, and the self-target prohibition is carried by exactly
        # the sexual-act category (their SINGLE-target acts are two-participant
        # by construction). Non-SINGLE sexual acts legitimately carry
        # forbid_self without ever exercising it — the resolver reads the flag
        # only in its SINGLE arm.
        from world.rules.targeting import requirement_for

        import world.skills.sexual_acts  # noqa: F401  (import side effect registers the full catalog)

        single_sexual_count = 0
        for key, skill in SKILL_REGISTRY.items():
            requirement = requirement_for(skill)
            with self.subTest(key=key):
                self.assertIs(requirement.spec, skill.target_spec)
                self.assertIs(requirement.faction, skill.faction_constraint)
                self.assertIs(
                    requirement.forbid_self,
                    skill.category is SkillCategory.SEXUAL_ACT,
                )
                if (
                    skill.category is SkillCategory.SEXUAL_ACT
                    and skill.target_spec is TargetSpec.SINGLE
                ):
                    single_sexual_count += 1
                    self.assertTrue(requirement.forbid_self)
        # Non-vacuity: the three seed acts alone guarantee three SINGLE-target
        # sexual acts; an empty loop here would pass every assertion above.
        self.assertGreaterEqual(single_sexual_count, 3)

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
                self.assertEqual(skill.effects, ["passive_trait:element_mastery"])

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
        # The divine-mystery tree ships a conferral ladder and a veil line,
        # each rooted in an ACTIVE cast skill the sample cards own. The two
        # sample-card roots must stay inside those families.
        self.assertGreaterEqual(len(conferral), 1)
        self.assertGreaterEqual(len(disguises), 1)
        self.assertTrue(
            all(skill.kind is SkillKind.ACTIVE for skill in conferral + disguises)
        )
        self.assertIn(
            "dominion_art", {skill.key for skill in conferral}
        )
        self.assertIn(
            "status_disguise", {skill.key for skill in disguises}
        )

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
            # A PASSIVE skill has no cast action from which any resource could
            # be deducted, so neither movement waiver declares a spendable cost.
            self.assertEqual(SKILL_REGISTRY[key].cost, {})

    @covers_requirement("skill-registry::reincarnation-boon-yuna-s-effect-string-is-well-formed")
    def test_reincarnation_boon_yuna_parses_as_sexual_mastery_effect(self):
        parsed = SKILL_REGISTRY["reincarnation_boon_yuna"].parsed_effects
        self.assertEqual(len(parsed), 1)
        self.assertIsInstance(parsed[0], SexualMasteryEffect)

    @covers_requirement("skill-registry::reincarnation-boon-labels-match-the-preset-character-names")
    def test_reincarnation_boon_labels_match_the_preset_character_names(self):
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        expected = {
            "reincarnation_boon_elosia": (
                "elosia_shadowmoon", "伊洛希雅", ("growth_rate:practice:5:wind",),
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

    @covers_requirement("skill-registry::dual-wield-style-is-a-passive-stance-not-a-castable-active-skill")
    def test_dual_wield_style_is_a_passive_stance(self):
        style = SKILL_REGISTRY["dual_wield_style"]
        self.assertEqual(style.label, "雙持劍術")
        self.assertIs(style.kind, SkillKind.PASSIVE)
        self.assertIs(style.target_spec, TargetSpec.NONE)
        self.assertEqual(style.cost, {})
        self.assertEqual(style.effects, ["weapon_style:dual_wield"])

    @covers_requirement("skill-registry::light-sword-style-deals-damage-via-the-standard-damage-convention")
    def test_light_sword_style_declares_the_damage_convention(self):
        # The cast-side dispatch (a damage: effect resolving through the
        # standard damage handler) is behavior, covered generically by the
        # synthetic cast-resolution tests; this contract carries the exact
        # shipped declaration the requirement names.
        skill = SKILL_REGISTRY["light_sword_style"]
        self.assertEqual(skill.effects, ["damage:light:physical"])
        self.assertIs(skill.element, ELEMENT_REGISTRY["light"])


class DivineMysteryFamilyInvariantTests(unittest.TestCase):
    """Category-wide family invariants of the shipped divine-mystery tree.

    Property assertions over every current and future member of the
    ``DIVINE_MYSTERY`` category — never a per-row listing of keys and
    labels — establishing the family boundary the redesigned lore mandates
    (docs/lore/skill-trees/divine-mystery.md section 0.1): zero resource
    cost, mandatory divine-blood gating, and no damage or healing effect.
    """

    def _members(self):
        return [
            (key, skill)
            for key, skill in SKILL_REGISTRY.items()
            if skill.category is SkillCategory.DIVINE_MYSTERY
        ]

    @covers_requirement("divine-mystery::divine-mystery-skills-are-gated-by-raceprofile-can-use-divine-arts")
    def test_every_member_is_bloodline_gated(self):
        for key, skill in self._members():
            with self.subTest(skill=key):
                self.assertTrue(skill.requires_divine_arts, key)

    @covers_requirement(
        "divine-mystery::the-divine-mystery-family-takes-no-element-verb-and-costs-nothing",
    )
    def test_every_member_declares_an_empty_resource_cost(self):
        for key, skill in self._members():
            with self.subTest(skill=key):
                self.assertEqual(skill.cost, {}, key)

    @covers_requirement(
        "divine-mystery::the-divine-mystery-family-takes-no-element-verb-and-costs-nothing",
    )
    def test_no_member_declares_a_damage_or_healing_effect(self):
        # The family vocabulary is closed: conferral, revocation, veil and
        # reveal effects only — plus the retained inert flavor form (design
        # D6 keeps the prefix and its handler registered for a future node).
        # A damage/heal/self-heal verb is the observable violation; the
        # isinstance whitelist also refuses any other cast verb a future
        # node could smuggle in.
        from world.skills.effects import (
            ConferGrowthRateEffect,
            ConferralEffect,
            DisguiseEffect,
            DivineMysteryEffect,
            RevealDisguiseEffect,
            RevokeGrantsEffect,
        )

        for key, skill in self._members():
            with self.subTest(skill=key):
                for effect in skill.parsed_effects:
                    self.assertNotIsInstance(
                        effect,
                        (DamageEffect, HealEffect, SelfHealEffect),
                        key,
                    )
                    self.assertIsInstance(
                        effect,
                        (
                            ConferralEffect,
                            ConferGrowthRateEffect,
                            RevokeGrantsEffect,
                            DisguiseEffect,
                            RevealDisguiseEffect,
                            DivineMysteryEffect,
                        ),
                        key,
                    )


class DivineMysteryLineageTreeTests(unittest.TestCase):
    """The shipped divine-mystery graph: three chains and the capstone.

    The registry's load-time validator already accepted the graph at import
    (a dangling edge, cycle, or out-of-range threshold would have raised
    before any test ran). These assertions pin the derived caps the
    redesign prices (lore section 2): the three chain ends are consumed by
    the capstone at Lv.10, so each derives tip cap 10, the leaves nobody
    consumes cap at the canopy default, and the roots cap at the maximum
    edge that consumes them. The load-time reverse-edge cache is rebuilt
    against the current registry in ``setUp`` so the assertions stay
    order-independent within the suite.
    """

    def setUp(self):
        validate_prerequisite_graph(SKILL_REGISTRY)

    def test_each_chain_end_derives_the_capstone_threshold_as_its_cap(self):
        for key in (
            "sovereign_investiture",
            "undying_tutelage",
            "true_name_sight",
            "dominion_recall",
            "bestowed_veil",
        ):
            with self.subTest(key=key):
                self.assertEqual(proficiency_cap(key), 10, key)

    def test_chain_ends_are_consumed_only_by_the_capstone_at_ten(self):
        for key in (
            "sovereign_investiture",
            "undying_tutelage",
            "true_name_sight",
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    prerequisite_consumers(key),
                    (("crown_apotheosis", 10),),
                    key,
                )

    def test_chain_roots_derive_the_maximum_consuming_threshold(self):
        for key, threshold in (
            ("dominion_art", 3),
            ("mentors_covenant", 3),
            ("status_disguise", 5),
        ):
            with self.subTest(key=key):
                self.assertEqual(proficiency_cap(key), threshold, key)

    def test_exactly_one_shipped_skill_can_declare_a_reveal(self):
        # collapse-veil-reveal-line regression: before that change, this set
        # held two keys, and the weaker (bare, mundane-only) reveal was the
        # one able to strip an authored veil that always read mundane. After,
        # the weaker node is gone and the survivor is the only skill in the
        # catalog that can express a reveal at all.
        reveal_skills = {
            key
            for key, skill in SKILL_REGISTRY.items()
            if any(
                isinstance(effect, RevealDisguiseEffect)
                for effect in skill.parsed_effects
            )
        }
        self.assertEqual(reveal_skills, {"true_name_sight"})


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
            "SkillCategory.MARTIAL_ARTS",
            ast.unparse(category_value),
        )


#: The frozen ``usable_out_of_combat=False`` inventory. The policy the set
#: encodes (delta spec skill-registry::every-skill-declares-usable-out-of-
#: combat-deliberately-under-one-written-policy): an ACTIVE skill declares
#: True unless casting it with no fight in progress is meaningless (flee —
#: nothing to disengage from), and PASSIVE skills declare True because their
#: continuously-owned effects (stat multipliers, mastery, movement, body
#: enhancement, passive buffs, growth/longevity traits) apply regardless of a
#: battlefield; only a passive whose effect is combat-context-only would
#: declare False. Damage-carrying skills declare True as well: their outside-
#: combat use is exactly opening a fight, which the damaging-action gate
#: (skill-field-availability) then confines to a battlefield. A new skill
#: that omits a decision falls outside this set by the helpers' False
#: default and fails the inventory assertion.
USABLE_OUT_OF_COMBAT_FALSE_KEYS = frozenset({"flee"})


class OutOfCombatAvailabilityPolicyTests(unittest.TestCase):
    """The deliberate-value contract for ``usable_out_of_combat``."""

    @classmethod
    def setUpClass(cls):
        import world.rules.disengage  # noqa: F401  (registers flee)

        # The inventory covers the sexual-act catalog too; registering it is
        # a declared prerequisite of the assertion, not an import-order
        # side effect.
        import world.skills.sexual_acts  # noqa: F401

    @covers_requirement(
        "skill-registry::the-set-of-skills-declaring-usable-out-of-combat-false-is-a-frozen-inventory"
    )
    def test_false_inventory_equals_the_frozen_set_naming_undecided_keys(self):
        computed = {
            key for key, skill in SKILL_REGISTRY.items()
            if not skill.usable_out_of_combat
        }
        missing = sorted(USABLE_OUT_OF_COMBAT_FALSE_KEYS - computed)
        extra = sorted(computed - USABLE_OUT_OF_COMBAT_FALSE_KEYS)
        self.assertEqual(
            (missing, extra),
            ([], []),
            "missing (deliberately-False keys that now declare True): "
            f"{missing}; undecided (keys defaulting to False that no "
            f"inventory records): {extra}",
        )

    @covers_requirement(
        "skill-registry::the-set-of-skills-declaring-usable-out-of-combat-false-is-a-frozen-inventory"
    )
    def test_an_injected_skill_that_omits_the_decision_fails_and_is_named(self):
        from world.skills.registry import _skill

        # The author path for a new seed row: omitting the kwarg leaves the
        # helper's False default — exactly the undecided state the frozen
        # inventory must surface.
        undecided = _skill(
            "_test_undecided_skill",
            "測試未決定",
            "注入未宣告 usable_out_of_combat 的定義。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            category=SkillCategory.UTILITY,
        )
        self.assertFalse(undecided.usable_out_of_combat)
        try:
            SKILL_REGISTRY[undecided.key] = undecided
            computed = {
                key for key, skill in SKILL_REGISTRY.items()
                if not skill.usable_out_of_combat
            }
            extra = sorted(computed - USABLE_OUT_OF_COMBAT_FALSE_KEYS)
            self.assertEqual(
                extra,
                [undecided.key],
                "the frozen-inventory diff must name the undecided key",
            )
        finally:
            SKILL_REGISTRY.pop(undecided.key, None)

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_damage_carrying_skills_all_declare_true(self):
        offenders = sorted(
            key
            for key, skill in SKILL_REGISTRY.items()
            if any(
                isinstance(effect, DamageEffect) for effect in skill.parsed_effects
            )
            and not skill.usable_out_of_combat
        )
        self.assertEqual(
            offenders,
            [],
            "DamageEffect-carrying entries must be selectable outside combat",
        )

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_flee_declares_false_at_its_own_construction_site(self):
        self.assertFalse(SKILL_REGISTRY["flee"].usable_out_of_combat)

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_every_production_construction_site_supplies_the_kwarg(self):
        """Every SkillDef/_skill/_spell call that produces a registry row
        passes ``usable_out_of_combat`` as an argument (the helper defaults
        stay False so an omission can never pass unnoticed)."""
        root = pathlib.Path(__file__).resolve().parents[2]
        sources = {
            "skills/registry.py": {"SkillDef", "_skill", "_spell"},
            "skills/sexual_acts/_builder.py": {"SkillDef"},
            "skills/sexual_acts/divine.py": {"SkillDef"},
            "rules/disengage.py": {"SkillDef"},
        }
        for relative, call_names in sources.items():
            tree = ast.parse((root / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, ast.Name) else None
                if name not in call_names:
                    continue
                with self.subTest(site=relative, call=name, line=node.lineno):
                    self.assertIn(
                        "usable_out_of_combat",
                        {kw.arg for kw in node.keywords if kw.arg},
                        f"{relative}:{node.lineno} omits the deliberate value",
                    )

    @covers_requirement(
        "skill-registry::every-skill-declares-usable-out-of-combat-deliberately-under-one-written-policy"
    )
    def test_no_production_module_mutates_the_flag_after_construction(self):
        """No production code assigns ``usable_out_of_combat`` on an already
        built SkillDef (``dataclasses.replace`` copies are construction, not
        mutation; tests are exempt — this scan covers production sources)."""
        root = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for package in ("world", "commands", "typeclasses", "web"):
            for path in sorted((root / package).rglob("*.py")):
                if "tests" in path.parts or "test_" in path.name:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        targets = node.targets
                    elif isinstance(node, ast.AnnAssign):
                        targets = [node.target]
                    elif isinstance(node, ast.AugAssign):
                        targets = [node.target]
                    else:
                        continue
                    for target in targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and target.attr == "usable_out_of_combat"
                        ):
                            offenders.append(
                                f"{path.relative_to(root)}:{node.lineno}"
                            )
        self.assertEqual(offenders, [])
