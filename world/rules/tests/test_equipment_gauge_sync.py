"""Gauge-ceiling sync tests for the equipment toggle (P2, design D1).

The toggle is the single writer of the non-literal gauge ceiling: every
successful toggle recomputes ``mod`` from scratch as the sum of the worn
items' caps inside the equipment transaction, settles a lowered ceiling's
excess current, and restores trait storage alongside the equipment mapping
when the write fails.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.combat import _apply_heal
from world.rules.equipment import toggle_equipment
from world.rules.status_query import build_status_read_model
from world.rules.traits import restore_gauges_to_full

# Rulebook caps used here: knight_platemail {hp: 15}, protective_ring {hp: 10}.
_PLATEMAIL = "knight_platemail"
_RING = "protective_ring"


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
        self.entity = create_object(PlayerCharacter, key="gauge sync probe")
        self.entity.race = "human"
        self.entity.apply_race_baseline()
        self.entity.traits.hp.rate = 0
        self.entity.db.equipment = None
        self.entity.db.inventory = [_PLATEMAIL, _RING]
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
        result = toggle_equipment(self.entity, _PLATEMAIL)
        self.assertEqual(result.outcome, "success")
        hp = self.entity.traits.hp
        self.assertEqual(hp.mod, 15)
        self.assertEqual(hp.max, self.base_max + 15)
        self.assertEqual(hp._data["base"], before["base"])

        # Healing reaches past the pre-equip maximum up to the raised one.
        hp.current = self.base_max - 10
        _apply_heal(self.entity, 30)
        self.assertEqual(hp.current, self.base_max + 15)

        # A full restore fills to the effective maximum.
        hp.current = 1
        restore_gauges_to_full(self.entity)
        self.assertEqual(hp.current, self.base_max + 15)

    @covers_requirement(
        "equipment-inventory::gauge-ceilings-stay-synced-with-worn-equipment"
    )
    def test_unequipping_settles_excess_current_and_renders(self):
        toggle_equipment(self.entity, _PLATEMAIL)
        restore_gauges_to_full(self.entity)
        self.assertEqual(
            self.entity.traits.hp.current, self.base_max + 15
        )
        toggle_equipment(self.entity, _PLATEMAIL)
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
        # (action, expected worn-cap sum) across two capped items.
        sequence = [
            (_PLATEMAIL, 15),
            (_RING, 25),
            (_PLATEMAIL, 10),
            (_PLATEMAIL, 25),
            (_RING, 15),
            (_RING, 25),
            (_PLATEMAIL, 10),
            (_RING, 0),
            (_PLATEMAIL, 15),
            (_PLATEMAIL, 0),
        ]
        for step, (item_key, expected_mod) in enumerate(sequence, start=1):
            with self.subTest(step=step, item=item_key):
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
        toggle_equipment(self.entity, _PLATEMAIL)
        self.entity.traits.hp.current = self.base_max - 20
        equipment_before = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": _PLATEMAIL,
            "accessories": [],
        }
        state_before = self.gauge_state()
        self.assertEqual(state_before["mod"], 15)

        with patch(
            "world.rules.equipment.transaction.atomic",
            return_value=_FakeAtomic(),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, _RING)

        self.assertEqual(self.entity.db.equipment, equipment_before)
        self.assertEqual(self.gauge_state(), state_before)
