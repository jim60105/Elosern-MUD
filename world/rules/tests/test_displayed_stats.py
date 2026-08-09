"""Tests for the displayed-stats block and the disguise-accessor hardening.

The renderer tests are pure: they exercise ``display_stat_block`` against a
lightweight fake that mirrors the Evennia lazy-handler surface the renderer
relies on (``entity.traits.<key>`` attribute access yielding ``None`` for a
missing trait, and ``entity.db.disguised_stats`` holding the disguise record).
"""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.displayed_stats import DISPLAYED_KEYS, display_stat_block
from world.rules.traits import get_display_value


class _FakeTrait:
    """One trait row exposing the ``value`` surface the accessor reads."""

    def __init__(self, value):
        self.value = value


class _FakeTraits:
    """Mirror the TraitHandler surface: a missing key reads as ``None``."""

    def __init__(self, mapping: dict[str, object]):
        self._mapping = mapping

    def __getattr__(self, key: str):
        return self._mapping.get(key)


class _FakeDB:
    def __init__(self, disguised_stats):
        self.disguised_stats = disguised_stats


class _FakeEntity:
    """A living-shaped entity: traits handler plus the disguise attribute."""

    def __init__(self, traits: dict[str, object], disguised_stats=None):
        self.traits = _FakeTraits(traits)
        self.db = _FakeDB(disguised_stats)


def _living(traits=None, disguised_stats=None):
    """Build the scenario entity with the combat-five true values."""
    values = {
        "atk_phys": _FakeTrait(88),
        "agility": _FakeTrait(92),
        "defense": _FakeTrait(90),
        "magic_level": _FakeTrait(250),
        "hp": _FakeTrait(120),
    }
    if traits is not None:
        values.update(traits)
    return _FakeEntity(values, disguised_stats)


class DisplayStatBlockTests(unittest.TestCase):
    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_disguised_entity_shows_disguised_and_true_keys_in_fixed_order(self):
        entity = _living(disguised_stats={"atk_phys": 60})
        self.assertEqual(
            display_stat_block(entity),
            "攻擊：60\n敏捷：92\n防禦：90\n魔法階級：250\n生命：120",
        )

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_undisguised_entity_shows_true_values_in_fixed_order(self):
        self.assertEqual(
            display_stat_block(_living()),
            "攻擊：88\n敏捷：92\n防禦：90\n魔法階級：250\n生命：120",
        )

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_non_living_target_yields_no_block(self):
        class _NonLiving:
            pass

        self.assertIsNone(display_stat_block(_NonLiving()))
        self.assertIsNone(display_stat_block(object()))

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_missing_trait_row_is_omitted_not_fatal(self):
        entity = _living(traits={"hp": None})
        block = display_stat_block(entity)
        self.assertEqual(
            block.splitlines(),
            ["攻擊：88", "敏捷：92", "防禦：90", "魔法階級：250"],
        )
        self.assertNotIn("生命", block)

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_malformed_trait_value_is_omitted_not_fatal(self):
        entity = _living(traits={"hp": _FakeTrait("garbage")})
        block = display_stat_block(entity)
        self.assertEqual(
            block.splitlines(),
            ["攻擊：88", "敏捷：92", "防禦：90", "魔法階級：250"],
        )
        self.assertNotIn("生命", block)

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_non_finite_disguise_value_is_omitted_not_fatal(self):
        entity = _living(traits={"hp": _FakeTrait(float("inf"))})
        block = display_stat_block(entity)
        self.assertEqual(
            block.splitlines(),
            ["攻擊：88", "敏捷：92", "防禦：90", "魔法階級：250"],
        )
        self.assertNotIn("生命", block)

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_entity_without_any_valid_row_yields_no_block(self):
        self.assertIsNone(display_stat_block(_FakeEntity({})))

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_hp_row_renders_the_gauge_current_value(self):
        block = display_stat_block(_living(disguised_stats={"hp": 999}))
        self.assertIn("生命：999", block)

    def test_block_key_order_matches_the_documented_five(self):
        self.assertEqual(
            DISPLAYED_KEYS, ("atk_phys", "agility", "defense", "magic_level", "hp")
        )


class GetDisplayValueHardeningTests(unittest.TestCase):
    @covers_requirement("displayed-stats-view::the-disguise-accessor-tolerates-a-malformed-disguise-record")
    def test_non_mapping_disguise_record_falls_back_to_true_value(self):
        entity = _living(disguised_stats=42)
        self.assertEqual(get_display_value(entity, "atk_phys"), 88)
        self.assertIn("攻擊：88", display_stat_block(entity))

    @covers_requirement("displayed-stats-view::the-disguise-accessor-tolerates-a-malformed-disguise-record")
    def test_boolean_disguise_record_falls_back_to_true_value(self):
        entity = _living(disguised_stats=True)
        self.assertEqual(get_display_value(entity, "atk_phys"), 88)
        self.assertIn("攻擊：88", display_stat_block(entity))

    @covers_requirement("displayed-stats-view::the-disguise-accessor-tolerates-a-malformed-disguise-record")
    def test_mapping_disguise_record_still_wins(self):
        entity = _living(disguised_stats={"atk_phys": 60})
        self.assertEqual(get_display_value(entity, "atk_phys"), 60)
        self.assertNotIn("攻擊：88", display_stat_block(entity))


if __name__ == "__main__":
    unittest.main()
