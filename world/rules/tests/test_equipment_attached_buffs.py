"""Attached buffs travel with the equipment toggle (P3, tasks 2.x).

Covers the ``equipment-inventory`` delta requirement
``attached-buffs-travel-with-the-equipment-toggle``: instances are recomputed
from the worn-set diff inside the toggle transaction (removed first, then
applied), keyed by definition and item key with unique-per-source stacking;
the ``buffs`` attribute joins the snapshot/restore set so a failed toggle
restores persistence AND live handler reads; repeated toggling never
accumulates; attached instances carry no gauge-ceiling modifiers (loader
guard, tested in the rulebook suite).
"""

from tools.spec_traceability import covers_requirement

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff, entity_active_buffs, tick_buffs
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import reload_equipment_effect_rules


def _entity():
    entity = create_object(PlayerCharacter, key="attached target")
    entity.race = "human"
    entity.apply_race_baseline()
    entity.traits.hp.rate = 0
    return entity


def _canonical_with(attached_armor: tuple[str, ...] = ()) -> Path:
    """Write a deviant rulebook where the given armor items attach the regen buff."""
    source = Path(__file__).parents[1] / "rulebook" / "equipment_effects.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    for armor_key in attached_armor:
        document["effects"][armor_key]["attached_buffs"] = ["item_regen_light"]
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.safe_dump(document, handle, allow_unicode=True)
    handle.close()
    return Path(handle.name)


class AttachedBuffLifecycleTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.entity = _entity()
        self.entity.db.inventory = [
            "apothecary_beads",
            "knight_platemail",
            "chainmail",
        ]
        self.entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": "chainmail",
            "accessories": [],
        }
        # Deviant rulebook: BOTH armor items attach the regen buff, and the
        # canonical beads entry stays attached, so singleton-slot replacement
        # and multi-source coexistence are exercisable with shipped items.
        self.deviant = _canonical_with(("knight_platemail", "chainmail"))
        reload_equipment_effect_rules(self.deviant)
        self.addCleanup(reload_equipment_effect_rules)

    def _regen_instance_keys(self):
        return {
            key
            for key, buff in self.entity.buffs.all.items()
            if buff.definition_key == "item_regen_light"
        }

    def test_equipping_beads_applies_exactly_one_instance(self):
        result = toggle_equipment(self.entity, "apothecary_beads")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._regen_instance_keys(), {"item_regen_light:apothecary_beads"})
        self.assertEqual(len(self.entity.buffs.all), 1)

    @covers_requirement(
        "equipment-inventory::attached-buffs-travel-with-the-equipment-toggle"
    )
    def test_beads_heal_while_worn_through_the_tick_engine(self):
        toggle_equipment(self.entity, "apothecary_beads")
        self.entity.traits.hp.current = self.entity.traits.hp.max - 10
        before = self.entity.traits.hp.value
        tick_buffs(self.entity)
        self.assertEqual(self.entity.traits.hp.value, before + 3)

    def test_unequipping_removes_exactly_its_instance(self):
        toggle_equipment(self.entity, "apothecary_beads")
        _add_buff(self.entity, "focus")
        result = toggle_equipment(self.entity, "apothecary_beads")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._regen_instance_keys(), set())
        self.assertIn("focus", entity_active_buffs(self.entity))

    def test_singleton_replacement_swaps_instances_in_one_toggle(self):
        toggle_equipment(self.entity, "knight_platemail")
        self.assertEqual(self._regen_instance_keys(), {"item_regen_light:knight_platemail"})
        result = toggle_equipment(self.entity, "chainmail")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._regen_instance_keys(), {"item_regen_light:chainmail"})
        self.assertEqual(len(self.entity.buffs.all), 1)

    def test_equip_unequip_ten_times_leaves_exactly_one_instance(self):
        for _ in range(10):
            toggle_equipment(self.entity, "apothecary_beads")
            toggle_equipment(self.entity, "apothecary_beads")
        self.assertEqual(self.entity.db.equipment["accessories"], [])
        self.assertEqual(self._regen_instance_keys(), set())

    def test_two_items_attaching_the_same_buff_coexist_as_distinct_sources(self):
        toggle_equipment(self.entity, "apothecary_beads")
        toggle_equipment(self.entity, "knight_platemail")
        self.assertEqual(
            self._regen_instance_keys(),
            {"item_regen_light:knight_platemail", "item_regen_light:apothecary_beads"},
        )
        # Unequipping one accessory removes only its instance.
        toggle_equipment(self.entity, "apothecary_beads")
        self.assertEqual(self._regen_instance_keys(), {"item_regen_light:knight_platemail"})

    def test_failed_toggle_restores_equipment_and_buffs_and_live_reads(self):
        toggle_equipment(self.entity, "apothecary_beads")
        before_equipment = dict(self.entity.db.equipment)
        before_buffs = dict(self.entity.buffs.all)
        # toggle_equipment imports the helpers function-locally, so the
        # failure is injected at the shipped buff-module seam.
        with patch(
            "world.rules.buffs._remove_buff_keys",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, "apothecary_beads")
        self.assertEqual(self.entity.db.equipment, before_equipment)
        self.assertEqual(set(self.entity.buffs.all), set(before_buffs))
        # Live handler reads reflect the restored storage (even if the
        # attribute cache was mutated mid-flight, the handler re-reads it).
        self.assertEqual(
            self._regen_instance_keys(), {"item_regen_light:apothecary_beads"}
        )

    def test_failed_apply_restores_equipment_and_buffs(self):
        with patch(
            "world.rules.buffs._add_buff",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, "apothecary_beads")
        self.assertEqual(self.entity.db.equipment["accessories"], [])
        self.assertEqual(self._regen_instance_keys(), set())


if __name__ == "__main__":
    unittest.main()