"""Status-removal item-use tests (受洗聖水 semantics, declarative model).

Covers the ``item-use-resolution`` delta requirement renaming
``blessed-cleansing-consumes-holy-water-to-purge-debuffs`` to ordinary
status-removal effects: a synthetic negative-selector consumable removes
every active debuff through the shared selector-driven removal, consumes
exactly one potion key atomically, emits the stable event with the settled
status keys and count, rejects a clean actor with ``no_debuffs`` (no
consume, no clock, zh prose through the reason surfaces), restores buffs on
a post-cleanse fault, and the loader rejects an ``amount`` on removal
entries. The potion is a synthetic consumable whose effect profile is
scoped through the kit's ``item_effect_profiles`` target.
"""

from tools.spec_traceability import covers_requirement

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from evennia.utils.test_resources import EvenniaTest

from world.lore.items import ItemUseMechanics
from world.rules.buffs import apply_buff, entity_active_buffs
from world.rules.clock import WorldClock
from world.rules.item_effects import (
    ItemEffectProfile,
    ItemEffectsRulebookError,
    StatusRemoveEffect,
)
from world.rules.items import (
    ItemUseReason,
    ItemUseRequest,
    preflight_item_use,
    use_item,
)
from world.rules.service_messages import rejection_message
from world.skills.equipment import list_items
from world.tests.synthetic_data import make_item

from ._combat_session_helpers import open_synthetic_scope

_VIAL_KEY = "t_blessed_vial"

_VIAL = make_item(
    _VIAL_KEY,
    display_name_zh="合成受洗水",
    price_table_key="t_mossmeals",
    sellable=True,
    use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
)

# The rulebook-side half of the scoped row: one negative-selector removal,
# the shape the shipped 受洗聖水 itself declares (magnitude-free by verb).
_VIAL_PROFILE = ItemEffectProfile(effects=(StatusRemoveEffect(selector="negative"),))

_SCOPE_EXTRA = {
    "items": {_VIAL_KEY: _VIAL},
    "item_effect_profiles": {_VIAL_KEY: _VIAL_PROFILE},
}


class StatusRemovalCleanseTests(EvenniaTest):
    """Settlement and rejection for a synthetic negative-removal consumable."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "items", extra=_SCOPE_EXTRA)
        self.actor = self.char1
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.inventory = [_VIAL_KEY]
        self.actor.db.equipment = None

    def _afflict(self, *keys: str) -> None:
        for key in keys:
            apply_buff(self.actor, key)

    @covers_requirement(
        "item-use-resolution::blessed-cleansing-consumes-holy-water-to-purge-debuffs"
    )
    def test_removal_clears_debuffs_consumes_and_logs_stable_event(self):
        self._afflict("poisoned", "fear")
        settlement = use_item(self.actor, _VIAL_KEY)
        result = settlement.result
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity_active_buffs(self.actor), set())
        self.assertEqual(list_items(self.actor), [])
        self.assertIsNotNone(result.event_log)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.kind, "item_used")
        # The per-family payload contract: status entries carry item_key /
        # consumable / status_keys / count and never an amount or effect key.
        self.assertEqual(
            set(entry.data),
            {"item_key", "consumable", "status_keys", "count"},
        )
        self.assertEqual(sorted(entry.data["status_keys"]), ["fear", "poisoned"])
        self.assertEqual(entry.data["count"], 2)
        self.assertNotIn("amount", entry.data)
        self.assertNotIn("effect_key", entry.data)
        self.assertIn("淨化", entry.text_template)

    def test_removal_keeps_buff_polarity_buffs(self):
        self._afflict("poisoned", "focus")
        result = use_item(self.actor, _VIAL_KEY).result
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity_active_buffs(self.actor), {"focus"})

    def test_no_debuffs_rejects_consuming_nothing_and_advancing_no_clock(self):
        clock = WorldClock()
        self.assertEqual(clock.tick, 0)
        self.actor.db.quest_log = None
        settlement = use_item(self.actor, _VIAL_KEY, clock=clock)
        result = settlement.result
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.NO_DEBUFFS)
        self.assertIsNone(result.event_log)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(list_items(self.actor), [_VIAL_KEY])
        self.assertEqual(rejection_message(result.reason), "你身上沒有需要淨化的負面狀態。")

    def test_preflight_rejects_no_debuffs_without_writing(self):
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key=_VIAL_KEY),
            in_combat=False,
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.NO_DEBUFFS)
        self.assertIsNone(preflight.plan)

    def test_none_alive_rejects_before_removal(self):
        self._afflict("poisoned")
        self.actor.traits.hp.current = 0
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key=_VIAL_KEY),
            in_combat=False,
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.NOT_ALIVE)

    def test_post_removal_fault_restores_potion_debuffs_and_live_reads(self):
        self._afflict("poisoned", "fear")
        before_inventory = list(self.actor.db.inventory)
        before_buffs = set(self.actor.buffs.all)
        with patch(
            "world.rules.items._delete_mirror",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                use_item(self.actor, _VIAL_KEY)
        self.assertEqual(list_items(self.actor), before_inventory)
        self.assertEqual(set(self.actor.buffs.all), before_buffs)
        self.assertEqual(entity_active_buffs(self.actor), {"poisoned", "fear"})

    def test_removal_consumes_contained_mirror_when_present(self):
        from world.rules.equipment import materialize_registry_object

        self._afflict("poisoned")
        materialize_registry_object(self.actor, _VIAL_KEY)
        result = use_item(self.actor, _VIAL_KEY).result
        self.assertEqual(result.outcome, "success")
        self.assertEqual(list_items(self.actor), [])
        self.assertEqual(
            [obj.key for obj in self.actor.contents],
            [],
        )

    def test_in_combat_preflight_shares_the_same_gate(self):
        clean = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key=_VIAL_KEY),
            in_combat=True,
        )
        self.assertFalse(clean.allowed)
        self.assertIs(clean.reason, ItemUseReason.NO_DEBUFFS)
        self._afflict("poisoned")
        allowed = preflight_item_use(
            ItemUseRequest(actor=self.actor, item_key=_VIAL_KEY),
            in_combat=True,
        )
        self.assertTrue(allowed.allowed)
        self.assertIsNone(allowed.reason)
        (step,) = allowed.plan.steps
        self.assertEqual(step.status_keys, ("poisoned",))


class ItemEffectsLoaderRemovalShapeTests(unittest.TestCase):
    """Loader shape contract for status-removal entries (delta scenario)."""

    def _document_with(self, entry):
        """The canonical document with its negative-removal entry replaced.

        The removal entry is located by content probe, so this fixture
        never names the shipped item whose entry it mutates.
        """
        source = Path(__file__).parents[1] / "rulebook" / "item_effects.yaml"
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
        replaced = 0
        for item_entry in document["items"].values():
            for effect in item_entry["effects"]:
                if effect.get("remove_status") == "negative":
                    effect.clear()
                    effect.update(entry)
                    replaced += 1
        self.assertEqual(replaced, 1)
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.safe_dump(document, handle, allow_unicode=True)
        handle.close()
        return Path(handle.name)

    def _load(self, entry):
        from world.rules.item_effects import load_item_effect_rules

        return load_item_effect_rules(self._document_with(entry))

    def test_removal_entry_with_amount_is_rejected(self):
        with self.assertRaises(ItemEffectsRulebookError):
            self._load({"remove_status": "negative", "amount": 40})

    def test_removal_entry_with_unknown_field_is_rejected(self):
        with self.assertRaises(ItemEffectsRulebookError):
            self._load({"remove_status": "negative", "cleanse": True})

    def test_verbless_entry_is_rejected(self):
        # The old cleanse shape (an amount-free empty mapping) is now a
        # verbless entry: the new model requires an explicit verb.
        with self.assertRaises(ItemEffectsRulebookError):
            self._load({})

    def test_removal_entry_shape_loads(self):
        loaded = self._load({"remove_status": "negative"})
        removal_profiles = [
            profile
            for profile in loaded["profiles"].values()
            if any(
                isinstance(effect, StatusRemoveEffect)
                for effect in profile.effects
            )
        ]
        self.assertEqual(len(removal_profiles), 1)


if __name__ == "__main__":
    unittest.main()
