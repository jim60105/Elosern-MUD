"""Equipment immunity: pure predicate, staging gate, and write backstop (P3).

Covers the ``buff-handler-integration`` delta requirement
``action-workflow-debuff-grants-are-neutralized-by-worn-equipment-immunity``:
immune debuff grants stage a non-mutating neutralization event visible to
both sides while buff storage stays byte-identical; the ``_add_buff``
chokepoint independently refuses the write; buff-polarity grants and
equipment-less entities are unaffected; already-applied debuffs keep ticking.
"""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    _entries_from_effect,
    _handle_buff_apply,
    _handle_self_buff_apply,
)
from world.rules.buffs import (
    _add_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.equipment_effects import equipment_immune_buff_keys


def _entity():
    entity = create_object(PlayerCharacter, key="immunity target")
    entity.race = "human"
    entity.apply_race_baseline()
    entity.traits.hp.rate = 0
    return entity


def _wear(entity, *item_keys: str) -> None:
    """Write the canonical equipment shape for the given accessory keys."""
    entity.db.equipment = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": list(item_keys),
    }


class EquipmentImmunityPredicateTests(unittest.TestCase):
    """Pure predicate contract (no Evennia objects needed)."""

    def _entity(self, equipment):
        return SimpleNamespace(
            db=SimpleNamespace(equipment=equipment),
        )

    @covers_requirement(
        "equipment-effects::equipment-immunity-predicate-is-pure-and-fail-closed"
    )
    def test_worn_pendant_grants_poison_immunity(self):
        entity = self._entity(
            {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": ["purified_pendant"],
            }
        )
        self.assertEqual(equipment_immune_buff_keys(entity), {"poisoned"})

    def test_empty_and_absent_storage_grant_nothing(self):
        missing = SimpleNamespace(db=SimpleNamespace(equipment=None))
        empty = self._entity(
            {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}
        )
        self.assertEqual(equipment_immune_buff_keys(missing), frozenset())
        self.assertEqual(equipment_immune_buff_keys(empty), frozenset())

    @covers_requirement(
        "equipment-effects::equipment-immunity-predicate-is-pure-and-fail-closed"
    )
    def test_malformed_storage_grants_nothing(self):
        malformed = [
            {"weapon_main": 1, "weapon_off": None, "armor": None, "accessories": []},
            {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": "nope"},
            {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": ["purified_pendant", "purified_pendant"]},
        ]
        for equipment in malformed:
            with self.subTest(equipment=equipment):
                self.assertEqual(equipment_immune_buff_keys(self._entity(equipment)), frozenset())

    def test_worn_immunities_union_across_items(self):
        entity = self._entity(
            {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": ["purified_pendant", "fearless_brooch"],
            }
        )
        self.assertEqual(
            equipment_immune_buff_keys(entity), {"poisoned", "fear"}
        )


class EquipmentImmunityBackstopTests(EvenniaTestCase):
    """The `_add_buff` no-write gate protects every direct caller."""

    def test_immune_debuff_write_is_refused(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        _add_buff(entity, "poisoned")
        self.assertEqual(entity_active_buffs(entity), set())

    def test_buff_polarity_grant_is_unaffected(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        _add_buff(entity, "focus")
        self.assertIn("focus", entity_active_buffs(entity))

    def test_existing_poison_keeps_ticking_after_equipping(self):
        entity = _entity()
        _add_buff(entity, "poisoned")
        _wear(entity, "purified_pendant")
        before = entity.traits.hp.value
        tick_buffs(entity)
        self.assertEqual(entity.traits.hp.value, before - 5)
        self.assertIn("poisoned", entity_active_buffs(entity))

    def test_equipment_less_entity_is_unaffected(self):
        entity = _entity()
        _add_buff(entity, "poisoned")
        self.assertIn("poisoned", entity_active_buffs(entity))

    def test_malformed_storage_confers_no_immunity(self):
        entity = _entity()
        entity.db.equipment = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": 7}
        _add_buff(entity, "poisoned")
        self.assertIn("poisoned", entity_active_buffs(entity))

    def test_repeated_direct_grant_attempts_write_nothing(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        for _ in range(3):
            _add_buff(entity, "poisoned")
        self.assertEqual(entity_active_buffs(entity), set())


class EquipmentImmunityStagingTests(EvenniaTestCase):
    """The action staging gate emits a deterministic neutralization event."""

    def test_immune_target_stages_non_mutating_neutralization(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        before = entity.attributes.get("buffs", default={})
        effects = _handle_buff_apply(
            entity, [entity], "buff_apply:poisoned", {}, 1.0
        )
        self.assertEqual(len(effects), 1)
        self.assertEqual(
            effects[0].description,
            f"equipment_immune|{entity.key}|poisoned",
        )
        self.assertEqual(effects[0].surfaces, frozenset())
        effects[0].apply()
        self.assertEqual(entity_active_buffs(entity), set())
        self.assertEqual(entity.attributes.get("buffs", default={}), before)
        (entry,) = _entries_from_effect(str(entity.key), effects[0])
        self.assertEqual(entry.kind, "equipment_immune")
        self.assertEqual(entry.data, {"buff_key": "poisoned"})
        self.assertIn("免疫", entry.text_template)

    def test_mixed_targets_gate_per_target(self):
        entity = _entity()
        other = _entity()
        _wear(entity, "purified_pendant")
        effects = _handle_buff_apply(
            entity, [entity, other], "buff_apply:poisoned", {}, 1.0
        )
        descriptions = [effect.description for effect in effects]
        self.assertEqual(
            descriptions,
            [
                f"equipment_immune|{entity.key}|poisoned",
                f"buff_applied|{other.key}|poisoned",
            ],
        )

    def test_three_casts_produce_three_events_and_no_storage_change(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        before = entity.attributes.get("buffs", default={})
        staged: list = []
        for _ in range(3):
            effects = _handle_buff_apply(
                entity, [entity], "buff_apply:poisoned", {}, 1.0
            )
            self.assertEqual(
                [effect.description for effect in effects],
                [f"equipment_immune|{entity.key}|poisoned"],
            )
            staged.extend(effects)
        # Commit every staged effect: storage stays byte-identical and each
        # attempt produced its own convertable neutralization entry.
        for effect in staged:
            effect.apply()
        self.assertEqual(entity.attributes.get("buffs", default={}), before)
        self.assertEqual(entity_active_buffs(entity), set())
        entries = [
            _entries_from_effect(str(entity.key), effect) for effect in staged
        ]
        self.assertEqual(
            [entry[0].kind for entry in entries],
            ["equipment_immune"] * 3,
        )

    def test_buff_polarity_grant_has_no_neutralization_event(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        effects = _handle_buff_apply(entity, [entity], "buff_apply:focus", {}, 1.0)
        self.assertEqual(
            [effect.description for effect in effects],
            [f"buff_applied|{entity.key}|focus"],
        )

    def test_self_buff_apply_gates_the_caster(self):
        entity = _entity()
        _wear(entity, "purified_pendant")
        effects = _handle_self_buff_apply(entity, [], "self_buff_apply:poisoned", {}, 1.0)
        self.assertEqual(
            [effect.description for effect in effects],
            [f"equipment_immune|{entity.key}|poisoned"],
        )
        self.assertEqual(entity_active_buffs(entity), set())

    def test_malformed_storage_never_neutralizes(self):
        entity = _entity()
        entity.db.equipment = None
        effects = _handle_buff_apply(entity, [entity], "buff_apply:poisoned", {}, 1.0)
        self.assertEqual(
            [effect.description for effect in effects],
            [f"buff_applied|{entity.key}|poisoned"],
        )

    @covers_requirement(
        "buff-handler-integration::action-workflow-debuff-grants-are-neutralized-by-worn-equipment-immunity"
    )
    def test_fearless_brooch_neutralizes_fear(self):
        entity = _entity()
        _wear(entity, "fearless_brooch")
        effects = _handle_buff_apply(entity, [entity], "buff_apply:fear", {}, 1.0)
        self.assertEqual(
            [effect.description for effect in effects],
            [f"equipment_immune|{entity.key}|fear"],
        )
        self.assertEqual(entity_active_buffs(entity), set())


if __name__ == "__main__":
    unittest.main()