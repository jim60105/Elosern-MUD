"""Tests for the ordered-level Evennia trait."""

from tools.spec_traceability import covers_requirement

from evennia.contrib.rpg.traits import TraitHandler
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.rules.rulebook.schema import evaluate_condition


class OrderedLevelTraitTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        entity = create_object(PlayerCharacter, key="ordered levels")
        self.handler = TraitHandler(entity, db_attribute_key="ordered_level_tests")

    def _trait(self, value=0):
        key = f"trait_{len(self.handler.all())}"
        self.handler.add(
            key,
            trait_type="ordered_level",
            levels=AROUSAL_LEVELS,
            value=value,
        )
        return self.handler[key]

    def test_defaults_labels_and_bounds(self):
        trait = self._trait()
        self.assertEqual((trait.value, trait.level), (0, "平靜"))
        trait.value = -20
        self.assertEqual(trait.value, 0)
        trait.value = 20
        self.assertEqual((trait.value, trait.level), (4, "極限"))

    @covers_requirement("ordered-level-trait::comparison-operators-accept-a-raw-vocabulary-string-another-orderedleveltrait-or-a-bare-ordinal", "ordered-level-trait::orderedleveltrait-s-level-property-returns-the-current-chinese-label")
    def test_all_comparisons_accept_label_trait_and_ordinal(self):
        trait = self._trait("中等")
        peer = self._trait(2)
        for other in ("中等", peer, 2):
            with self.subTest(other=other):
                self.assertTrue(trait == other)
                self.assertTrue(trait >= other)
                self.assertFalse(trait > other)
                self.assertTrue(trait <= other)
                self.assertFalse(trait < other)
        self.assertGreater(trait, "微興奮")
        self.assertLess(trait, "高度")
        self.assertGreater(trait, self._trait(1))
        self.assertLess(trait, self._trait(3))
        self.assertGreater(trait, 1)
        self.assertLess(trait, 3)
        self.assertGreaterEqual(trait, self._trait(1))
        self.assertLessEqual(trait, self._trait(3))
        self.assertGreaterEqual(trait, 1)
        self.assertLessEqual(trait, 3)

    @covers_requirement("ordered-level-trait::orderedleveltrait-is-a-from-scratch-trait-subclass-storing-a-bounded-ordinal-into-a-fixed-vocabulary-tuple")
    def test_invalid_or_crossed_bounds_are_rejected(self):
        trait = self._trait("中等")
        with self.assertRaisesRegex(ValueError, "min"):
            trait.min = -1
        with self.assertRaisesRegex(ValueError, "max"):
            trait.max = len(AROUSAL_LEVELS)
        trait.max = 1
        self.assertEqual(trait.value, 1)
        with self.assertRaisesRegex(ValueError, "min"):
            trait.min = 2

    @covers_requirement("ordered-level-trait::an-unrecognized-level-string-raises-rather-than-silently-failing")
    def test_invalid_label_raises_and_condition_uses_native_comparison(self):
        trait = self._trait("高度")
        with self.assertRaisesRegex(ValueError, "高渡"):
            _ = trait == "高渡"
        self.assertTrue(
            evaluate_condition(
                {"field": "arousal", "gte": "高度"},
                {"arousal": trait},
            )
        )
