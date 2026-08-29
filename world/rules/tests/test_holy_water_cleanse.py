"""Blessed cleansing (受洗聖水) item-use tests (P3, tasks 3.x).

Covers the ``item-use-resolution`` delta requirement
``blessed-cleansing-consumes-holy-water-to-purge-debuffs``: the registered
``blessed_cleansing`` effect removes every active debuff through the shipped
cleanse path, consumes exactly one potion key atomically, emits the stable
event, rejects a clean actor with ``no_debuffs`` (no consume, no clock, zh
prose through the shipped reason surfaces), restores buffs on a
post-cleanse fault, and the loader rejects an ``amount`` on cleanse entries.
"""

from tools.spec_traceability import covers_requirement

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from evennia.utils.test_resources import EvenniaTest

from world.rules.buffs import _add_buff, entity_active_buffs
from world.rules.clock import WorldClock
from world.rules.items import (
    ItemEffectKey,
    ItemUseReason,
    ItemUseRequest,
    load_item_effect_rules,
    preflight_item_use,
    use_item,
)
from world.rules.service_messages import rejection_message
from world.skills.equipment import list_items


class HolyWaterCleanseTests(EvenniaTest):
    """Settlement and rejection for the shipped 受洗聖水 definition."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.inventory = ["baptismal_holy_water"]
        self.actor.db.equipment = None

    def _afflict(self, *keys: str) -> None:
        for key in keys:
            _add_buff(self.actor, key)

    def test_cleanse_removes_debuffs_consumes_and_logs_stable_event(self):
        self._afflict("poisoned", "fear")
        settlement = use_item(self.actor, "baptismal_holy_water")
        result = settlement.result
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity_active_buffs(self.actor), set())
        self.assertEqual(list_items(self.actor), [])
        self.assertIsNotNone(result.event_log)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.kind, "item_used")
        # The per-family payload contract: cleanse entries carry item_key /
        # effect_key / consumable / count and never an amount.
        self.assertEqual(
            set(entry.data),
            {"item_key", "effect_key", "consumable", "count"},
        )
        self.assertEqual(entry.data["effect_key"], "blessed_cleansing")
        self.assertEqual(entry.data["count"], 2)
        self.assertNotIn("amount", entry.data)
        self.assertIn("淨化", entry.text_template)

    def test_cleanse_keeps_buff_polarity_buffs(self):
        self._afflict("poisoned", "focus")
        result = use_item(self.actor, "baptismal_holy_water").result
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity_active_buffs(self.actor), {"focus"})

    def test_no_debuffs_rejects_consuming_nothing_and_advancing_no_clock(self):
        clock = WorldClock()
        self.assertEqual(clock.tick, 0)
        self.actor.db.quest_log = None
        settlement = use_item(self.actor, "baptismal_holy_water", clock=clock)
        result = settlement.result
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.NO_DEBUFFS)
        self.assertIsNone(result.event_log)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(list_items(self.actor), ["baptismal_holy_water"])
        self.assertEqual(rejection_message(result.reason), "你身上沒有需要淨化的負面狀態。")

    def test_preflight_rejects_no_debuffs_without_writing(self):
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key="baptismal_holy_water"),
            in_combat=False,
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.NO_DEBUFFS)
        self.assertIsNone(preflight.plan)

    def test_none_alive_rejects_before_cleanse(self):
        self._afflict("poisoned")
        self.actor.traits.hp.current = 0
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key="baptismal_holy_water"),
            in_combat=False,
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.NOT_ALIVE)

    def test_post_cleanse_fault_restores_potion_debuffs_and_live_reads(self):
        self._afflict("poisoned", "fear")
        before_inventory = list(self.actor.db.inventory)
        before_buffs = set(self.actor.buffs.all)
        with patch(
            "world.rules.items._delete_mirror",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                use_item(self.actor, "baptismal_holy_water")
        self.assertEqual(list_items(self.actor), before_inventory)
        self.assertEqual(set(self.actor.buffs.all), before_buffs)
        self.assertEqual(entity_active_buffs(self.actor), {"poisoned", "fear"})

    def test_cleanse_consumes_contained_mirror_when_present(self):
        from world.rules.equipment import materialize_registry_object

        self._afflict("poisoned")
        materialize_registry_object(self.actor, "baptismal_holy_water")
        result = use_item(self.actor, "baptismal_holy_water").result
        self.assertEqual(result.outcome, "success")
        self.assertEqual(list_items(self.actor), [])
        self.assertEqual(
            [obj.key for obj in self.actor.contents],
            [],
        )

    @covers_requirement(
        "item-use-resolution::blessed-cleansing-consumes-holy-water-to-purge-debuffs"
    )
    def test_in_combat_preflight_shares_the_same_gate(self):
        clean = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key="baptismal_holy_water"),
            in_combat=True,
        )
        self.assertFalse(clean.allowed)
        self.assertIs(clean.reason, ItemUseReason.NO_DEBUFFS)
        self._afflict("poisoned")
        allowed = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key="baptismal_holy_water"),
            in_combat=True,
        )
        self.assertTrue(allowed.allowed)
        self.assertIsNone(allowed.reason)
        self.assertEqual(allowed.plan.cleansed_count, 1)
        self.assertIsNone(allowed.plan.gauge)


class ItemEffectsLoaderCleanseShapeTests(unittest.TestCase):
    """Loader shape contract for cleanse-family entries."""

    def _document_with(self, entry):
        source = Path(__file__).parents[1] / "rulebook" / "item_effects.yaml"
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
        document["effects"]["blessed_cleansing"] = entry
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.safe_dump(document, handle, allow_unicode=True)
        handle.close()
        return Path(handle.name)

    def test_cleanse_entry_with_amount_is_rejected(self):
        from world.rules.items import ItemEffectsRulebookError

        with self.assertRaises(ItemEffectsRulebookError):
            load_item_effect_rules(self._document_with({"amount": 40}))

    def test_cleanse_entry_with_unknown_field_is_rejected(self):
        from world.rules.items import ItemEffectsRulebookError

        with self.assertRaises(ItemEffectsRulebookError):
            load_item_effect_rules(self._document_with({"cleanse": True}))

    def test_cleanse_entry_with_empty_mapping_is_ok(self):
        result = load_item_effect_rules(self._document_with({}))
        self.assertIsNone(
            result["rules"][ItemEffectKey.BLESSED_CLEANSE.value].amount
        )


if __name__ == "__main__":
    unittest.main()