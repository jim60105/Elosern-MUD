"""Data-contract test: skill registry content contract
Slice of ``test_skill_registry``: SkillRegistryTests.
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
