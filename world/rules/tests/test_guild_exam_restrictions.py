"""Synthetic resolver-backed restriction, real equipment, and ownership tests."""

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch
from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.characters import PlayerCharacter
from world.lore.items import EquipmentModifierKey
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import preview_skill
from world.rules.combat import Battlefield, roll_initiative
from world.rules.combat_modifiers import adjusted_agility, evaluate_combat_modifiers, evaluate_combat_modifiers_no_create
from world.rules.economy import TradeError, TradeReason, buy, sell
from world.rules.equipment import InventoryError, materialize_registry_object, plan_inventory_delta, toggle_equipment
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.guild_exam_restrictions import (
    RestrictionError, RestrictionProfile, activate_exam_restriction,
    preflight_exam_restriction, remove_exam_restriction,
)
from world.rules.progression import can_use_skill
from world.rules.cross_lineage_unlock import UnlockRulebook
from world.rules.rulebook.schema import Rule
from world.rules.status_query import build_stat_breakdown
from world.rules.targeting import RoomActionContext
from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import make_buff, make_item, make_skill, synthetic_registries

_ROOT = make_skill("t_exam_cut", effects=["damage:none:physical"], cost={})
_BODY = make_skill("t_exam_body", effects=["stat_multiply:atk_phys:1.2", "stat_multiply:agility:1.2", "stat_multiply:defense:1.2"], kind=SkillKind.PASSIVE, target_spec=TargetSpec.SELF)
_HEAL = make_skill("t_exam_heal", effects=["heal:single"], cost={"mp": 50})
_GUARD = make_skill("t_exam_guard", effects=["passive_buff:t_exam_guard"], kind=SkillKind.PASSIVE, target_spec=TargetSpec.SELF)
_HIGH_BODY = make_skill("t_exam_high_body", effects=["stat_multiply:agility:100"], kind=SkillKind.PASSIVE, target_spec=TargetSpec.SELF)
_DOMAIN = make_skill("t_exam_domain_cast", effects=["self_buff_apply:t_exam_domain"], target_spec=TargetSpec.SELF, cost={"sp": 2})
_DOMAIN_BUFF = make_buff("t_exam_domain")
_POS_BUFF = make_buff("t_exam_pos")
_PEN_BUFF = make_buff("t_exam_pen")
_BLADE = make_item("t_exam_blade", equipment_slot=EquipmentSlot.WEAPON_MAIN, modifier_key=EquipmentModifierKey.PLAIN_SWORD)
_ARMOR = make_item("t_exam_armor", equipment_slot=EquipmentSlot.ARMOR, modifier_key=EquipmentModifierKey.LEATHER_ARMOR)
_RING = make_item("t_exam_ring", equipment_slot=EquipmentSlot.ACCESSORY, modifier_key=EquipmentModifierKey.GUILD_LIMIT_D, sellable=False, guild_property=True)
_OTHER = make_item("t_exam_other", equipment_slot=EquipmentSlot.ACCESSORY, modifier_key=EquipmentModifierKey.SILVER_HAIRPIN)
_OTHERS = tuple(replace(_OTHER, key=f"t_exam_other_{index}") for index in range(ACCESSORY_MAX_SLOTS))
_PROFILE = RestrictionProfile(
    "T", _RING.key, _BLADE.key, _ARMOR.key, _ROOT.key,
    ("basic_attack", "flee", _ROOT.key, _BODY.key),
    MappingProxyType({"hp": 77, "mp": 60, "sp": 80, "atk_phys": 29, "agility": 12, "defense": 31, "magic_power": 23}), 11,
)
_RULES = {
    _BLADE.modifier_key: EquipmentEffectRule({"atk_phys": 4}, {}, (), (), 0),
    _ARMOR.modifier_key: EquipmentEffectRule({"defense": 5, "agility": 1}, {}, (), (), 0),
    _RING.modifier_key: EquipmentEffectRule({}, {}, (), (), 0),
    _OTHER.modifier_key: EquipmentEffectRule({}, {}, (), (), 0),
}


class RestrictionBehaviorTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(synthetic_registries(
            "races", "skills", "items", "buffs", "sexual_acts",
            extra={"skills": {s.key: s for s in (_ROOT, _BODY, _HEAL, _GUARD, _HIGH_BODY, _DOMAIN)}, "items": {i.key: i for i in (_BLADE, _ARMOR, _RING, _OTHER, *_OTHERS)}, "buffs": {b.key: b for b in (_DOMAIN_BUFF, _POS_BUFF, _PEN_BUFF)}},
        ))
        stack.enter_context(patch("world.rules.guild_exam_restrictions.PROFILES", {"T": _PROFILE}))
        stack.enter_context(patch("world.rules.cross_lineage_unlock.RULEBOOK", UnlockRulebook((), {}, {}, {})))
        stack.enter_context(patch("world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", _RULES))
        stack.enter_context(patch("world.rules.combat_modifiers._RULES", [Rule("t_exam_guard", {"skill_owned": _GUARD.key}, {"defense": 9})]))
        self.host = create_object(NPC, key="synthetic restriction host", location=self.room1)
        self.host.race = "t_duskmari"
        self.host.apply_race_baseline()
        self.player = create_object(PlayerCharacter, key="synthetic restriction player", location=self.room1)
        self.player.race = "t_duskmari"
        self.player.apply_race_baseline()
        for key in ("hp", "mp", "sp"):
            gauge = self.host.traits.get(key)
            gauge.base = 200
            gauge.rate = 0
            gauge.current = 200
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            self.host.traits.get(key).base = 40
        self.host.db.skills = {"active": [_ROOT.key, _HEAL.key], "passive": [_BODY.key, _GUARD.key, _HIGH_BODY.key]}
        self.host.db.skill_proficiency = {_ROOT.key: 350.0, _HEAL.key: 123.0}
        self.host.db.inventory = [_BLADE.key, _ARMOR.key]
        for key in (_BLADE.key, _ARMOR.key):
            self.assertEqual(toggle_equipment(self.host, key).outcome, "success")

    def snapshot(self):
        return deepcopy({
            "traits": dict(self.host.traits.trait_data),
            "skills": dict(self.host.db.skills),
            "proficiency": dict(self.host.db.skill_proficiency),
            "inventory": list(self.host.db.inventory),
            "equipment": dict(self.host.db.equipment),
            "restriction": self.host.db.guild_exam_restriction,
            "buffs": self.host.db.buffs,
        })

    def learned_snapshot(self):
        state = self.snapshot()
        return ({key: row["base"] for key, row in state["traits"].items()}, state["skills"], state["proficiency"])

    @covers_requirement("skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-predicate")
    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")
    def test_sealed_heal_rejects_pre_cost_in_both_resolver_paths_and_view(self):
        activate_exam_restriction(self.host, "synthetic-exam", "T")
        before = self.snapshot()
        request = ActionRequest(self.host, _HEAL.key, [self.host], RoomActionContext(self.room1))
        for entrypoint in (ActionResolver.preflight, ActionResolver.resolve):
            result = entrypoint(request)
            self.assertEqual(result.reason, RejectReason.EXAM_SKILL_SEALED)
            self.assertEqual(self.snapshot(), before)
        self.assertFalse(can_use_skill(self.host, _HEAL))
        self.assertEqual(preview_skill(self.host, _HEAL.key, request.context).reason, RejectReason.EXAM_SKILL_SEALED)
        self.assertIn(_HEAL.key, self.host.skills.owned_keys())

    @covers_requirement("skill-handler::effective-value-is-the-sole-resolution-time-multiplier-application-point-and-never-writes-to-entity-traits")
    def test_real_accessory_reduces_stronger_host_and_seals_passives_reversibly(self):
        learned = self.learned_snapshot()
        original_kit = deepcopy(dict(self.host.db.equipment))
        activate_exam_restriction(self.host, "synthetic-exam", "T")
        self.assertIn(_RING.key, self.host.db.inventory)
        self.assertIn(_RING.key, self.host.equipment.slot_contents(EquipmentSlot.ACCESSORY))
        self.assertEqual(self.host.skills.effective_value("agility"), 11)
        self.assertEqual(adjusted_agility(self.host), 12)
        self.assertEqual(evaluate_combat_modifiers(self.host)["defense"], 5)
        self.assertEqual(self.host.skills.effective_value("defense") + evaluate_combat_modifiers(self.host)["defense"], 31)
        self.assertEqual(self.host.traits.hp.max, 77)
        self.assertIn(_GUARD.key, self.host.skills.owned_keys())
        self.assertEqual(self.learned_snapshot(), learned)
        before_reads = self.snapshot()
        self.assertEqual(evaluate_combat_modifiers_no_create(self.host), evaluate_combat_modifiers(self.host))
        rows = {row.key: row for row in build_stat_breakdown(self.host)}
        self.assertEqual(rows["agility"].effective, 12)
        self.assertEqual(rows["defense"].effective, 31)
        self.assertEqual(rows["hp"].effective, 77)
        self.assertEqual(self.snapshot(), before_reads)
        with self.assertRaises(RestrictionError):
            remove_exam_restriction(self.host, "stale-exam")
        self.assertEqual(self.snapshot(), before_reads)
        self.assertTrue(remove_exam_restriction(self.host, "synthetic-exam"))
        self.assertFalse(remove_exam_restriction(self.host, "synthetic-exam"))
        self.assertEqual(dict(self.host.db.equipment), original_kit)
        self.assertEqual(self.host.traits.hp.max, 200)
        self.assertEqual(self.learned_snapshot(), learned)
        self.assertNotIn(_RING.key, self.host.db.inventory)

    def test_hamstring_and_positive_caps_apply_to_reduced_neutral_first(self):
        activate_exam_restriction(self.host, "synthetic-exam", "T")
        from world.rules.buffs import apply_buff
        apply_buff(self.host, _POS_BUFF.key)
        apply_buff(self.host, _PEN_BUFF.key)
        rules = [
            Rule("t_exam_positive", {"buff_active": _POS_BUFF.key}, {"agility_flat": 100, "atk_phys": 100}),
            Rule("t_exam_penalty", {"buff_active": _PEN_BUFF.key}, {"agility_flat": -5, "atk_phys": -7}),
        ]
        with patch("world.rules.combat_modifiers._RULES", rules):
            self.assertEqual(adjusted_agility(self.host), 7)
            self.assertEqual(self.host.skills.effective_value("atk_phys") + evaluate_combat_modifiers(self.host)["atk_phys"], 22)
        with patch("world.rules.combat_modifiers._RULES", [Rule("t_exam_penalty", {"buff_active": _PEN_BUFF.key}, {"agility_flat": -5})]):
            self.assertEqual(adjusted_agility(self.host), 7)
        host_key, player_key = str(self.host.key), str(self.player.key)
        battlefield = Battlefield(
            {"one": frozenset({host_key}), "two": frozenset({player_key})},
            {host_key: self.host, player_key: self.player},
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=0):
            self.player.traits.agility.base = 12
            self.assertEqual(roll_initiative(battlefield)[0], player_key)

    @covers_requirement("equipment-inventory::accessory-is-a-bounded-multi-item-slot")
    def test_weak_host_and_overflow_fail_without_any_mutation(self):
        self.host.traits.agility.base = 8
        before = self.snapshot()
        with self.assertRaisesRegex(RestrictionError, "naturally weak"):
            activate_exam_restriction(self.host, "synthetic-exam", "T")
        self.assertEqual(self.snapshot(), before)
        self.host.traits.agility.base = 40
        self.host.db.inventory = [*self.host.db.inventory, *(item.key for item in _OTHERS)]
        kit = dict(self.host.db.equipment)
        kit["accessories"] = [item.key for item in _OTHERS]
        self.host.db.equipment = kit
        before = self.snapshot()
        with self.assertRaisesRegex(RestrictionError, "accessory slot"):
            activate_exam_restriction(self.host, "synthetic-exam", "T")
        self.assertEqual(self.snapshot(), before)

    def test_guild_property_cannot_be_bought_sold_transferred_or_awarded(self):
        activate_exam_restriction(self.host, "synthetic-exam", "T")
        before = self.snapshot()
        for trade in (buy, sell):
            with self.assertRaises(TradeError) as raised:
                trade(self.host, self.char2, _RING.key)
            self.assertEqual(raised.exception.args[0], TradeReason.UNSELLABLE)
        for delta in ({"additions": (_RING.key,)}, {"removals": (_RING.key,)}):
            with self.assertRaises(InventoryError):
                plan_inventory_delta(self.host, **delta)
        mirror = materialize_registry_object(self.host, _RING.key)
        self.assertFalse(mirror.move_to(self.char2, quiet=True, move_type="give"))
        self.assertFalse(mirror.move_to(self.room1, quiet=True, move_type="drop"))
        self.assertEqual(mirror.location, self.host)
        from world.rules.npc_intents import _transfer_items
        from world.rules.guild_config._commerce import validate_assortment_configs

        receiver_inventory = deepcopy(self.player.db.inventory)
        self.assertFalse(_transfer_items(self.host, self.player, _RING.key, 1).applied)
        self.assertEqual(self.player.db.inventory, receiver_inventory)
        with patch("world.rules.guild_config._commerce.ASSORTMENT_REGISTRY", {"t_bad": SimpleNamespace(item_keys=(_RING.key,))}):
            with self.assertRaisesRegex(ValueError, "guild property"):
                validate_assortment_configs([{"key": "t_bad", "offers": []}])
        self.assertEqual(toggle_equipment(self.host, _RING.key).outcome, "rejected")
        self.assertEqual(toggle_equipment(self.host, _BLADE.key).outcome, "rejected")
        self.assertEqual(self.snapshot(), before)

    def test_failed_activation_and_removal_restore_cached_and_stored_surfaces(self):
        before = self.snapshot()
        from world.rules.equipment import sync_equipment_gauge_limits
        def fail_after_gauges(host):
            sync_equipment_gauge_limits(host)
            raise RuntimeError("synthetic sync failure")
        with patch("world.rules.guild_exam_restrictions.sync_equipment_gauge_limits", side_effect=fail_after_gauges):
            with self.assertRaises(RuntimeError):
                activate_exam_restriction(self.host, "synthetic-exam", "T")
        self.assertEqual(self.snapshot(), before)
        activate_exam_restriction(self.host, "synthetic-exam", "T")
        active = self.snapshot()
        with patch("world.rules.guild_exam_restrictions.sync_equipment_gauge_limits", side_effect=fail_after_gauges):
            with self.assertRaises(RuntimeError):
                remove_exam_restriction(self.host, "synthetic-exam")
        self.assertEqual(self.snapshot(), active)

    def test_unbounded_senior_policy_retains_domain_bonus_and_basic_body(self):
        self.host.db.skills = {**dict(self.host.db.skills), "active": [*self.host.db.skills["active"], _DOMAIN.key]}
        unrestricted = replace(_PROFILE, accessory=None, ceilings=MappingProxyType({}), initiative_agility=None, allowed_skills=(*_PROFILE.allowed_skills, _DOMAIN.key))
        with patch("world.rules.guild_exam_restrictions.PROFILES", {"T": unrestricted}):
            activate_exam_restriction(self.host, "synthetic-exam", "T")
        self.assertEqual(self.host.skills.effective_value("atk_phys"), 48)
        with patch("world.rules.combat_modifiers._RULES", [Rule("t_exam_domain", {"buff_active": _DOMAIN_BUFF.key}, {"atk_phys": 10})]):
            result = ActionResolver.resolve(ActionRequest(self.host, _DOMAIN.key, [self.host], RoomActionContext(self.room1)))
            self.assertEqual(result.outcome, "success")
            self.assertEqual(self.host.skills.effective_value("atk_phys") + evaluate_combat_modifiers(self.host)["atk_phys"], 62)
        self.assertNotIn(_RING.key, self.host.db.inventory)
        self.assertEqual(self.host.skills.effective_value("agility"), 48)

    def test_player_is_not_eligible_for_host_restriction(self):
        with self.assertRaisesRegex(RestrictionError, "NPC host"):
            preflight_exam_restriction(self.player, "T")
