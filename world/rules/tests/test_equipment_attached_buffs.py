"""Attached buffs travel with the equipment toggle (P3, tasks 2.x).

Covers the ``equipment-inventory`` delta requirement
``attached-buffs-travel-with-the-equipment-toggle``: instances are recomputed
from the worn-set diff inside the toggle transaction (removed first, then
applied), keyed by definition and item key with unique-per-source stacking;
the ``buffs`` attribute joins the snapshot/restore set so a failed toggle
restores persistence AND live handler reads; repeated toggling never
accumulates; attached instances carry no gauge-ceiling modifiers (loader
guard, tested in the rulebook suite).

Data-independent (migrate-rules-equipment-item-tests-off-real-data): the gear
is synthetic kit rows bound to rulebook rows resolved at runtime — the row
that naturally attaches a buff (probed by feature) plus two rows deviantly
patched to attach the same definition — and the regen amount is the live
definition's rate delta, never a copied number.
"""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import EquipmentSlot
from world.rules import buffs as buff_rules
from world.rules.buffs import _add_buff, entity_active_buffs, tick_buffs
from world.rules.equipment import toggle_equipment
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import open_synthetic_scope
from ._equipment_rulebook_probes import (
    attached_buffs_rule,
    gauge_cap_row_keys,
    rule_for,
)

# The shipped row that attaches a buff, plus its attached definition — read
# from the rulebook, never hardcoded (fail-fast on ambiguity).
_ATTACHED_MODIFIER, _ATTACHED_ROW = attached_buffs_rule()
_REGEN_BUFF = _ATTACHED_ROW.attached_buffs[0]

# Two further rows (the distinct hp gauge-cap rows) patched to attach the
# SAME definition, so singleton-slot replacement and multi-source
# coexistence are exercisable without naming a shipped item.
_ARMOR_CAP_KEYS = gauge_cap_row_keys()[:2]


def _entity():
    entity = create_object(PlayerCharacter, key="attached target")
    entity.race = "human"
    entity.apply_race_baseline()
    entity.traits.hp.rate = 0
    return entity


# Synthetic gear: the naturally-attaching accessory and two armors riding the
# deviantly-patched gauge-cap rows (heavier cap = the first swap target).
_ACCESSORY = make_item(
    "t_herb_satchel",
    display_name_zh="合成藥草囊",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_ATTACHED_MODIFIER,
)
_ARMOR_HEAVY = make_item(
    "t_plate_harness",
    display_name_zh="合成重甲背具",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_ARMOR_CAP_KEYS[1],
)
_ARMOR_LIGHT = make_item(
    "t_quilted_jacket",
    display_name_zh="合成棉裡外衣",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_ARMOR_CAP_KEYS[0],
)
_ATTACHED_ITEMS = (_ACCESSORY, _ARMOR_HEAVY, _ARMOR_LIGHT)


class _AttachedBuffScope(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self, "items", extra={"items": {d.key: d for d in _ATTACHED_ITEMS}}
        )
        deviant = {
            cap_key: replace(rule_for(cap_key), attached_buffs=(_REGEN_BUFF,))
            for cap_key in _ARMOR_CAP_KEYS
        }
        patcher = patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", deviant
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.entity = _entity()
        self.entity.db.inventory = [d.key for d in _ATTACHED_ITEMS]
        self.entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": _ARMOR_LIGHT.key,
            "accessories": [],
        }


class AttachedBuffLifecycleTests(_AttachedBuffScope):
    def _regen_instance_keys(self):
        return {
            key
            for key, buff in self.entity.buffs.all.items()
            if buff.definition_key == _REGEN_BUFF
        }

    def _instance_key(self, item) -> str:
        return f"{_REGEN_BUFF}:{item.key}"

    def test_equipping_accessory_applies_exactly_one_instance(self):
        result = toggle_equipment(self.entity, _ACCESSORY.key)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._regen_instance_keys(), {self._instance_key(_ACCESSORY)})
        self.assertEqual(len(self.entity.buffs.all), 1)

    @covers_requirement(
        "equipment-inventory::attached-buffs-travel-with-the-equipment-toggle"
    )
    def test_accessory_heals_while_worn_through_the_tick_engine(self):
        toggle_equipment(self.entity, _ACCESSORY.key)
        self.entity.traits.hp.current = self.entity.traits.hp.max - 10
        before = self.entity.traits.hp.value
        tick_buffs(self.entity)
        rate = buff_rules.BUFF_DEFINITIONS[_REGEN_BUFF].modifiers["rate"]
        self.assertEqual(rate["target"], "hp")
        self.assertEqual(
            self.entity.traits.hp.value, before + rate["delta"]
        )

    def test_unequipping_removes_exactly_its_instance(self):
        toggle_equipment(self.entity, _ACCESSORY.key)
        _add_buff(self.entity, "focus")
        result = toggle_equipment(self.entity, _ACCESSORY.key)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._regen_instance_keys(), set())
        self.assertIn("focus", entity_active_buffs(self.entity))

    def test_singleton_replacement_swaps_instances_in_one_toggle(self):
        toggle_equipment(self.entity, _ARMOR_HEAVY.key)
        self.assertEqual(self._regen_instance_keys(), {self._instance_key(_ARMOR_HEAVY)})
        result = toggle_equipment(self.entity, _ARMOR_LIGHT.key)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._regen_instance_keys(), {self._instance_key(_ARMOR_LIGHT)})
        self.assertEqual(len(self.entity.buffs.all), 1)

    def test_equip_unequip_ten_times_leaves_exactly_one_instance(self):
        for _ in range(10):
            toggle_equipment(self.entity, _ACCESSORY.key)
            toggle_equipment(self.entity, _ACCESSORY.key)
        self.assertEqual(self.entity.db.equipment["accessories"], [])
        self.assertEqual(self._regen_instance_keys(), set())

    def test_two_items_attaching_the_same_buff_coexist_as_distinct_sources(self):
        toggle_equipment(self.entity, _ACCESSORY.key)
        toggle_equipment(self.entity, _ARMOR_HEAVY.key)
        self.assertEqual(
            self._regen_instance_keys(),
            {self._instance_key(_ARMOR_HEAVY), self._instance_key(_ACCESSORY)},
        )
        # Unequipping one accessory removes only its instance.
        toggle_equipment(self.entity, _ACCESSORY.key)
        self.assertEqual(self._regen_instance_keys(), {self._instance_key(_ARMOR_HEAVY)})

    def test_failed_toggle_restores_equipment_and_buffs_and_live_reads(self):
        toggle_equipment(self.entity, _ACCESSORY.key)
        before_equipment = dict(self.entity.db.equipment)
        before_buffs = dict(self.entity.buffs.all)
        # toggle_equipment imports the helpers function-locally, so the
        # failure is injected at the shipped buff-module seam.
        with patch(
            "world.rules.buffs._remove_buff_keys",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, _ACCESSORY.key)
        self.assertEqual(self.entity.db.equipment, before_equipment)
        self.assertEqual(set(self.entity.buffs.all), set(before_buffs))
        # Live handler reads reflect the restored storage (even if the
        # attribute cache was mutated mid-flight, the handler re-reads it).
        self.assertEqual(
            self._regen_instance_keys(), {self._instance_key(_ACCESSORY)}
        )

    def test_failed_apply_restores_equipment_and_buffs(self):
        with patch(
            "world.rules.buffs._add_buff",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, _ACCESSORY.key)
        self.assertEqual(self.entity.db.equipment["accessories"], [])
        self.assertEqual(self._regen_instance_keys(), set())


if __name__ == "__main__":
    unittest.main()
