"""Cast-resolution tests for registry skills with combat handlers."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.elements import ELEMENT_REGISTRY
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.skills.effects import (
    BuffApplyEffect,
    DamageEffect,
    SelfBuffApplyEffect,
    parse_effect,
)
from world.skills.registry import SKILL_REGISTRY

from .test_spell_catalogs import EARTH_SPELL_CATALOG


class DualBladeMasteryCastTests(EvenniaTestCase):
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
            "active": ["dual_blade_mastery"],
            "passive": ["dual_wield_style"],
        }
        self.assertIn("dual_wield_style", self.actor.skills.owned_keys())
        sp_before = self.actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.sp.value, sp_before - 30)

class LightSwordStyleCastTests(EvenniaTestCase):
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

class EarthHardenedSkinCastTests(EvenniaTestCase):
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
