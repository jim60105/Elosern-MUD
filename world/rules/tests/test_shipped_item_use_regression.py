"""Data-contract test: shipped usable-item regression contract

Pins the current observable behaviour of the four shipped usable items
(added-declarative-item-effects task 1.1): restored magnitudes 40/120/40,
the ``hp_full``/``mp_full``/``no_debuffs`` rejection codes, one-unit
consumption counts, the rendered event wording, and the six-second
out-of-combat clock advance. This file names shipped catalog rows on
purpose — it is the frozen contract the declarative-effect rewrite must
reproduce byte-for-byte (design Risks: a migrated item silently changing
magnitude or reason code)."""

import unittest

from evennia.utils.test_resources import EvenniaTest
from world.rules.buffs import apply_buff, entity_active_buffs
from world.rules.clock import WorldClock
from world.rules.items import (
    ItemUseRequest,
    resolve_item_use,
    use_item,
)
from world.skills.equipment import list_items

_HEALING_KEY = "healing_potion"
_GREATER_KEY = "greater_healing_potion"
_MANA_KEY = "mana_potion"
_HOLY_WATER_KEY = "baptismal_holy_water"


class ShippedItemUseRegressionTests(EvenniaTest):
    """The frozen behaviour of the four shipped usable consumables."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.inventory = []
        self.actor.db.equipment = None

    def _set_gauge(self, gauge: str, missing: int) -> tuple[int, int]:
        maximum = int(getattr(self.actor.traits, gauge).max)
        getattr(self.actor.traits, gauge).current = maximum - missing
        return maximum - missing, maximum

    def _use(self, item_key: str):
        return resolve_item_use(
            ItemUseRequest(actor=self.actor, item_key=item_key), in_combat=False
        )

    def _assert_single_entry(self, result, text: str) -> None:
        self.assertEqual(result.outcome, "success")
        self.assertIsNotNone(result.event_log)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.kind, "item_used")
        self.assertEqual(entry.text_template, text)

    def test_healing_potion_restores_forty_and_consumes_one_of_two(self):
        before, _ = self._set_gauge("hp", 60)
        self.actor.db.inventory = [_HEALING_KEY, _HEALING_KEY]
        result = self._use(_HEALING_KEY)
        self._assert_single_entry(
            result, "你使用了「治療藥水」，恢復了 40 點生命值。"
        )
        self.assertEqual(int(self.actor.traits.hp.current), before + 40)
        self.assertEqual(list_items(self.actor), [_HEALING_KEY])

    def test_greater_healing_potion_restores_one_hundred_twenty(self):
        # The human baseline caps HP below the 200-point gap the 120 restore
        # needs to stay unclamped, so the fixture lifts the base first.
        self.actor.traits.hp.base = 300
        before, _ = self._set_gauge("hp", 200)
        self.actor.db.inventory = [_GREATER_KEY]
        result = self._use(_GREATER_KEY)
        self._assert_single_entry(
            result, "你使用了「強效治療藥水」，恢復了 120 點生命值。"
        )
        self.assertEqual(int(self.actor.traits.hp.current), before + 120)
        self.assertEqual(list_items(self.actor), [])

    def test_mana_potion_restores_forty_mp_only(self):
        hp_before = int(self.actor.traits.hp.current)
        mp_before, _ = self._set_gauge("mp", 60)
        self.actor.db.inventory = [_MANA_KEY]
        result = self._use(_MANA_KEY)
        self._assert_single_entry(
            result, "你使用了「魔力藥水」，恢復了 40 點魔力值。"
        )
        self.assertEqual(int(self.actor.traits.mp.current), mp_before + 40)
        self.assertEqual(int(self.actor.traits.hp.current), hp_before)
        self.assertEqual(list_items(self.actor), [])

    def test_holy_water_removes_two_debuffs_and_consumes_one(self):
        apply_buff(self.actor, "poisoned")
        apply_buff(self.actor, "fear")
        self.actor.db.inventory = [_HOLY_WATER_KEY]
        result = self._use(_HOLY_WATER_KEY)
        self._assert_single_entry(
            result, "你使用了「受洗聖水」，淨化了 2 個負面狀態。"
        )
        self.assertEqual(entity_active_buffs(self.actor), set())
        self.assertEqual(list_items(self.actor), [])

    def test_single_gauge_full_rejections_keep_their_specific_codes(self):
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        self.actor.db.inventory = [_HEALING_KEY]
        rejected = self._use(_HEALING_KEY)
        self.assertEqual(rejected.outcome, "rejected")
        self.assertEqual(str(rejected.reason), "hp_full")

        maximum = int(self.actor.traits.mp.max)
        self.actor.traits.mp.current = maximum
        self.actor.db.inventory = [_MANA_KEY]
        rejected = self._use(_MANA_KEY)
        self.assertEqual(rejected.outcome, "rejected")
        self.assertEqual(str(rejected.reason), "mp_full")

    def test_clean_actor_holy_water_rejects_with_no_debuffs(self):
        self.actor.db.inventory = [_HOLY_WATER_KEY]
        rejected = self._use(_HOLY_WATER_KEY)
        self.assertEqual(rejected.outcome, "rejected")
        self.assertEqual(str(rejected.reason), "no_debuffs")
        self.assertEqual(list_items(self.actor), [_HOLY_WATER_KEY])

    def test_out_of_combat_use_advances_the_canonical_six_seconds(self):
        self._set_gauge("hp", 60)
        self.actor.db.inventory = [_HEALING_KEY]
        clock = WorldClock()
        settlement = use_item(self.actor, _HEALING_KEY, clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(clock.tick, 6)
        self.assertEqual(list_items(self.actor), [])


if __name__ == "__main__":
    unittest.main()
