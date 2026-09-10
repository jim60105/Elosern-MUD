"""Gauge-ceiling sync tests for the equipment toggle (P2, design D1).

The toggle is the single writer of the non-literal gauge ceiling: every
successful toggle recomputes ``mod`` from scratch as the sum of the worn
items' caps inside the equipment transaction, settles a lowered ceiling's
excess current, and restores trait storage alongside the equipment mapping
when the write fails.

Data-independent (migrate-rules-equipment-item-tests-off-real-data): the two
capped synthetic items bind to the rulebook's hp gauge-cap rows resolved by
runtime feature probe (asserted distinct), and every expected ceiling is the
probed cap value — never a copied number.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.items import EquipmentSlot
from world.rules.combat import _apply_heal
from world.rules.equipment import toggle_equipment
from world.rules.status_query import build_status_read_model
from world.rules.traits import restore_gauges_to_full
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import open_synthetic_scope
from ._equipment_rulebook_probes import gauge_cap_row_keys, rule_for

# Two distinct hp gauge-cap rows, probed at import (fail-fast on ambiguity):
# the heavier row rides the armor slot, the lighter one the accessory slot.
_CAP_HEAVY, _CAP_LIGHT = (lambda pairs: (pairs[-1], pairs[0]))(gauge_cap_row_keys())
_CAP_HEAVY_VALUE = rule_for(_CAP_HEAVY).gauge_caps["hp"]
_CAP_LIGHT_VALUE = rule_for(_CAP_LIGHT).gauge_caps["hp"]

_HEAVY = make_item(
    "t_bulwark_harness",
    display_name_zh="合成厚背護甲",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_CAP_HEAVY,
)
_LIGHT = make_item(
    "t_light_guard_ring",
    display_name_zh="合成輕護指環",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_CAP_LIGHT,
)
_SCOPE_EXTRA = {"items": {_HEAVY.key: _HEAVY, _LIGHT.key: _LIGHT}}


class _FakeAtomic:
    """Simulate a commit failure after the transaction body completed."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise RuntimeError("simulated db commit failure")
        return False


class _GaugeSyncCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        self.entity = create_object(PlayerCharacter, key="gauge sync probe")
        self.entity.race = "human"
        self.entity.apply_race_baseline()
        self.entity.traits.hp.rate = 0
        self.entity.db.equipment = None
        self.entity.db.inventory = [_HEAVY.key, _LIGHT.key]
        self.base_max = self.entity.traits.hp.max

    def gauge_state(self) -> dict:
        hp = self.entity.traits.hp
        return {
            "mod": hp.mod,
            "max": hp.max,
            "current": hp.current,
            "base": hp._data["base"],
        }


class GaugeCeilingSyncTests(_GaugeSyncCase):
    @covers_requirement(
        "equipment-inventory::gauge-ceilings-stay-synced-with-worn-equipment"
    )
    def test_equipping_raises_the_live_ceiling_without_touching_base(self):
        before = self.gauge_state()
        result = toggle_equipment(self.entity, _HEAVY.key)
        self.assertEqual(result.outcome, "success")
        hp = self.entity.traits.hp
        self.assertEqual(hp.mod, _CAP_HEAVY_VALUE)
        self.assertEqual(hp.max, self.base_max + _CAP_HEAVY_VALUE)
        self.assertEqual(hp._data["base"], before["base"])

        # Healing reaches past the pre-equip maximum up to the raised one.
        hp.current = self.base_max - 10
        _apply_heal(self.entity, _CAP_HEAVY_VALUE * 2)
        self.assertEqual(hp.current, self.base_max + _CAP_HEAVY_VALUE)

        # A full restore fills to the effective maximum.
        hp.current = 1
        restore_gauges_to_full(self.entity)
        self.assertEqual(hp.current, self.base_max + _CAP_HEAVY_VALUE)

    @covers_requirement(
        "equipment-inventory::gauge-ceilings-stay-synced-with-worn-equipment"
    )
    def test_unequipping_settles_excess_current_and_renders(self):
        toggle_equipment(self.entity, _HEAVY.key)
        restore_gauges_to_full(self.entity)
        self.assertEqual(
            self.entity.traits.hp.current, self.base_max + _CAP_HEAVY_VALUE
        )
        toggle_equipment(self.entity, _HEAVY.key)
        hp = self.entity.traits.hp
        # Stored current settled to the lowered ceiling inside the toggle.
        self.assertEqual(hp.mod, 0)
        self.assertEqual(hp.current, self.base_max)
        model = build_status_read_model(self.entity)
        self.assertEqual(model.resources["hp"].maximum, self.base_max)
        self.assertEqual(model.resources["hp"].current, self.base_max)

    @covers_requirement(
        "equipment-inventory::gauge-ceilings-stay-synced-with-worn-equipment"
    )
    def test_ten_toggles_recompute_without_accumulating(self):
        heavy, light = _CAP_HEAVY_VALUE, _CAP_LIGHT_VALUE
        h, l = _HEAVY.key, _LIGHT.key
        # (action, expected worn-cap sum) across the two capped rows.
        sequence = [
            (h, heavy),
            (l, heavy + light),
            (h, light),
            (h, heavy + light),
            (l, heavy),
            (l, heavy + light),
            (h, light),
            (l, 0),
            (h, heavy),
            (h, 0),
        ]
        for step, (item_key, expected_mod) in enumerate(sequence, start=1):
            with self.subTest(step=step):
                result = toggle_equipment(self.entity, item_key)
                self.assertEqual(result.outcome, "success")
                self.assertEqual(self.entity.traits.hp.mod, expected_mod)
                self.assertEqual(
                    self.entity.traits.hp.max, self.base_max + expected_mod
                )

    @covers_requirement(
        "equipment-inventory::gauge-ceilings-stay-synced-with-worn-equipment"
    )
    def test_failed_toggle_restores_equipment_and_gauge_traits(self):
        toggle_equipment(self.entity, _HEAVY.key)
        self.entity.traits.hp.current = self.base_max - _CAP_HEAVY_VALUE - 5
        equipment_before = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": _HEAVY.key,
            "accessories": [],
        }
        state_before = self.gauge_state()
        self.assertEqual(state_before["mod"], _CAP_HEAVY_VALUE)

        with patch(
            "world.rules.equipment.transaction.atomic",
            return_value=_FakeAtomic(),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, _LIGHT.key)

        self.assertEqual(self.entity.db.equipment, equipment_before)
        self.assertEqual(self.gauge_state(), state_before)
