"""Data-contract test: skill registry content contract
Slice of ``test_skill_registry``: SkillContentCompletionTests, DivineMysteryFamilyInvariantTests, DivineMysteryLineageTreeTests.
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
