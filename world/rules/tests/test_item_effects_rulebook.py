"""Validation tests for the deterministic item-effect rulebook (D1/D2)."""

import tempfile
import unittest
from pathlib import Path

from world.lore.items import ITEM_REGISTRY, ItemEffectKey
from world.rules.items import (
    ITEM_EFFECT_RULES,
    ITEM_USE_SECONDS,
    MAX_EFFECT_AMOUNT,
    ItemEffectRule,
    ItemEffectsRulebookError,
    load_item_effect_rules,
    reload_item_effect_rules,
)

_CANONICAL = """\
item_use_seconds: 6

effects:
  self_heal:
    amount: 40
  greater_heal:
    amount: 120
  mana_restore:
    amount: 40
  blessed_cleansing: {}
"""


class ItemEffectRulebookTests(unittest.TestCase):
    def _rulebook(self, text: str = _CANONICAL) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        handle.write(text)
        handle.close()
        path = Path(handle.name)
        self.addCleanup(path.unlink, True)
        return path
    def test_canonical_rulebook_validates(self):
        loaded = load_item_effect_rules()
        self.assertEqual(loaded["item_use_seconds"], ITEM_USE_SECONDS)
        self.assertGreaterEqual(ITEM_USE_SECONDS, 1)
        self.assertEqual(
            set(ITEM_EFFECT_RULES), {key for key in ItemEffectKey}
        )
        rule = ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL]
        self.assertIsInstance(rule, ItemEffectRule)
        self.assertGreaterEqual(rule.amount, 1)
        self.assertLessEqual(rule.amount, MAX_EFFECT_AMOUNT)

    def test_every_registry_effect_key_resolves_in_the_rulebook(self):
        for definition in ITEM_REGISTRY.values():
            if definition.use_mechanics is None:
                continue
            with self.subTest(item=definition.key):
                self.assertIn(
                    definition.use_mechanics.effect_key, ITEM_EFFECT_RULES
                )

    def test_reload_is_idempotent(self):
        before = dict(ITEM_EFFECT_RULES)
        before_seconds = ITEM_USE_SECONDS
        reload_item_effect_rules()
        self.assertEqual(ITEM_USE_SECONDS, before_seconds)
        self.assertEqual(dict(ITEM_EFFECT_RULES), before)

    def test_valid_override_path_loads(self):
        loaded = load_item_effect_rules(self._rulebook(_CANONICAL))
        self.assertEqual(loaded["item_use_seconds"], 6)
        self.assertEqual(loaded["rules"][ItemEffectKey.SELF_HEAL].amount, 40)

    def test_malformed_rulebooks_are_rejected(self):
        cases = {
            "not-a-mapping": "- 1\n- 2\n",
            "missing-seconds": "effects:\n  self_heal:\n    amount: 40\n",
            "extra-top-key": (
                "item_use_seconds: 6\neffects:\n  self_heal:\n    amount: 40\n"
                "extra: 1\n"
            ),
            "unknown-effect": (
                "item_use_seconds: 6\neffects:\n  fireball:\n    amount: 40\n"
            ),
            "zero-use-seconds": (
                "item_use_seconds: 0\neffects:\n  self_heal:\n    amount: 40\n"
            ),
            "string-amount": (
                "item_use_seconds: 6\neffects:\n  self_heal:\n    amount: '40'\n"
            ),
            "bool-amount": (
                "item_use_seconds: 6\neffects:\n  self_heal:\n    amount: true\n"
            ),
            "zero-amount": (
                "item_use_seconds: 6\neffects:\n  self_heal:\n    amount: 0\n"
            ),
            "oversized-amount": (
                "item_use_seconds: 6\neffects:\n  self_heal:\n"
                f"    amount: {MAX_EFFECT_AMOUNT + 1}\n"
            ),
            "missing-effect-entry": "item_use_seconds: 6\neffects: {}\n",
            "effect-extra-field": (
                "item_use_seconds: 6\neffects:\n"
                "  self_heal:\n    amount: 40\n    kind: self_heal\n"
            ),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ItemEffectsRulebookError):
                    load_item_effect_rules(self._rulebook(text))

    def test_amount_is_read_only_from_the_rulebook(self):
        # The magnitude must come from the canonical rulebook mapping rather
        # than any duplicated constant in consuming modules.
        import world.rules.items as items_module

        self.assertEqual(
            items_module.ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL].amount,
            load_item_effect_rules()["rules"][ItemEffectKey.SELF_HEAL].amount,
        )


if __name__ == "__main__":
    unittest.main()
