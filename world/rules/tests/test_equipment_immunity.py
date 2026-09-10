"""Worn-equipment immunity tests (P2, tasks 2.4/2.5/2.6).

Covers the pure predicate, the ``_add_buff`` no-write backstop, and the
action-staging gate that emits the neutralization event.

Data-independent (migrate-rules-equipment-item-tests-off-real-data): the
accessories are synthetic kit rows bound to the rulebook's immunity rows
resolved by runtime feature probe, and the expected immune sets are the
probed rows' contents — never a shipped item name or copied buff key.
"""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import EquipmentSlot
from world.rules import buffs as buff_rules
from world.rules.action import (
    _entries_from_effect,
    _handle_buff_apply,
    _handle_self_buff_apply,
)
from world.rules.buffs import _add_buff, entity_active_buffs, tick_buffs
from world.rules.equipment_effects import equipment_immune_buff_keys
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import open_synthetic_scope
from ._equipment_rulebook_probes import immune_to_key, rule_for

# The shipped poison-immune and fear-immune rows, located by content probe
# (fail-fast unique match). The debuffs they grant are read from the rows.
_POISON_IMMUNE_KEY = immune_to_key("poisoned")
_FEAR_IMMUNE_KEY = immune_to_key("fear")
_POISON_IMMUNE = tuple(rule_for(_POISON_IMMUNE_KEY).immune)
_FEAR_IMMUNE = tuple(rule_for(_FEAR_IMMUNE_KEY).immune)

_PENDANT = make_item(
    "t_warden_medallion",
    display_name_zh="合成守護吊飾",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_POISON_IMMUNE_KEY,
)
_BROOCH = make_item(
    "t_steadfast_brooch",
    display_name_zh="合成無畏胸針",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_FEAR_IMMUNE_KEY,
)
_SCOPE_EXTRA = {"items": {_PENDANT.key: _PENDANT, _BROOCH.key: _BROOCH}}


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


class _ImmunityScope(EvenniaTestCase):
    """Shared scope so the fail-closed registry lookup sees the synth rows."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)


class EquipmentImmunityPredicateTests(_ImmunityScope):
    """Pure predicate contract over the scoped registry."""

    def _entity(self, equipment):
        return SimpleNamespace(
            db=SimpleNamespace(equipment=equipment),
        )

    @covers_requirement(
        "equipment-effects::equipment-immunity-predicate-is-pure-and-fail-closed"
    )
    def test_worn_pendant_grants_the_probed_immunity(self):
        entity = self._entity(
            {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [_PENDANT.key],
            }
        )
        self.assertEqual(
            equipment_immune_buff_keys(entity), set(_POISON_IMMUNE)
        )

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
            {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [_PENDANT.key, _PENDANT.key],
            },
        ]
        for equipment in malformed:
            with self.subTest(equipment=equipment):
                self.assertEqual(
                    equipment_immune_buff_keys(self._entity(equipment)), frozenset()
                )

    def test_worn_immunities_union_across_items(self):
        entity = self._entity(
            {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [_PENDANT.key, _BROOCH.key],
            }
        )
        self.assertEqual(
            equipment_immune_buff_keys(entity),
            set(_POISON_IMMUNE) | set(_FEAR_IMMUNE),
        )


class EquipmentImmunityBackstopTests(_ImmunityScope):
    """The `_add_buff` no-write gate protects every direct caller."""

    @covers_requirement(
        "equipment-effects::equipment-immunity-predicate-is-pure-and-fail-closed"
    )
    def test_immune_debuff_write_is_refused(self):
        entity = _entity()
        _wear(entity, _PENDANT.key)
        _add_buff(entity, "poisoned")
        self.assertEqual(entity_active_buffs(entity), set())

    def test_buff_polarity_grant_is_unaffected(self):
        entity = _entity()
        _wear(entity, _PENDANT.key)
        _add_buff(entity, "focus")
        self.assertIn("focus", entity_active_buffs(entity))

    def test_existing_poison_keeps_ticking_after_equipping(self):
        entity = _entity()
        _add_buff(entity, "poisoned")
        _wear(entity, _PENDANT.key)
        before = entity.traits.hp.value
        tick_buffs(entity)
        rate = buff_rules.BUFF_DEFINITIONS["poisoned"].modifiers["rate"]
        self.assertEqual(rate["target"], "hp")
        tick_damage = -rate["delta"]
        self.assertEqual(entity.traits.hp.value, before - tick_damage)
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
        _wear(entity, _PENDANT.key)
        for _ in range(3):
            _add_buff(entity, "poisoned")
        self.assertEqual(entity_active_buffs(entity), set())


class EquipmentImmunityStagingTests(_ImmunityScope):
    """The action staging gate emits a deterministic neutralization event."""

    def test_immune_target_stages_non_mutating_neutralization(self):
        entity = _entity()
        _wear(entity, _PENDANT.key)
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
        _wear(entity, _PENDANT.key)
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
        _wear(entity, _PENDANT.key)
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
        _wear(entity, _PENDANT.key)
        effects = _handle_buff_apply(entity, [entity], "buff_apply:focus", {}, 1.0)
        self.assertEqual(
            [effect.description for effect in effects],
            [f"buff_applied|{entity.key}|focus"],
        )

    def test_self_buff_apply_gates_the_caster(self):
        entity = _entity()
        _wear(entity, _PENDANT.key)
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
    def test_warden_brooch_neutralizes_the_probed_fear_row(self):
        entity = _entity()
        _wear(entity, _BROOCH.key)
        (fear_buff,) = _FEAR_IMMUNE
        effects = _handle_buff_apply(
            entity, [entity], f"buff_apply:{fear_buff}", {}, 1.0
        )
        self.assertEqual(
            [effect.description for effect in effects],
            [f"equipment_immune|{entity.key}|{fear_buff}"],
        )
        self.assertEqual(entity_active_buffs(entity), set())


if __name__ == "__main__":
    unittest.main()
