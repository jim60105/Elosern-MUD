"""Regression tests for subrace adjustment order.

Runs on invented kit subraces with deliberately opposed modifiers: one lifts
agility while dropping defense, one overrides a vital band outright, one
carries nothing — so the fixed order (race baseline -> static modifiers ->
vital overrides) is the only way the observed numbers can land.
"""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.races import StatModifiers
from world.rules.traits import build_initial_traits
from world.tests.synthetic_data import (
    SYNTH_RACES,
    make_subrace,
    synthetic_registries,
)

_SWIFTFIN = make_subrace(
    "t_duskmari_swiftfin",
    # Large signed skews so the kit race's small floors move measurably.
    static_modifiers=StatModifiers(agility=1.0, defense=-0.5),
)
_DREAMWEAVER = make_subrace(
    "t_duskmari_dreamweaver",
    static_modifiers=StatModifiers(),
    vital_overrides={"mp": (40, 80)},
)
_PLAINSPAN = make_subrace(
    "t_duskmari_plainspan",
    static_modifiers=StatModifiers(),
)


@synthetic_registries(
    "races",
    "subraces",
    extra={
        "subraces": {
            _SWIFTFIN.key: _SWIFTFIN,
            _DREAMWEAVER.key: _DREAMWEAVER,
            _PLAINSPAN.key: _PLAINSPAN,
        }
    },
)
class SubraceOrderTests(unittest.TestCase):
    @covers_requirement("entity-trait-scales::subrace-static-modifiers-and-vital-overrides-apply-in-a-fixed-order-race-baseline-then-static-modifiers-then-vital-overrides")
    def test_static_modifiers_and_vital_overrides(self):
        race = SYNTH_RACES["t_duskmari"]
        baseline = build_initial_traits("t_duskmari")
        swift = build_initial_traits("t_duskmari", "t_duskmari_swiftfin")
        dreamer = build_initial_traits("t_duskmari", "t_duskmari_dreamweaver")

        # Static modifiers run on the race baseline, per axis and signed:
        # agility up and defense down relative to the same race floor.
        self.assertGreater(swift["agility"], baseline["agility"])
        self.assertLess(swift["defense"], baseline["defense"])
        self.assertEqual(
            swift["agility"],
            round(race.static_baseline.agility[0] * 2.0),
        )
        self.assertEqual(
            swift["defense"],
            round(race.static_baseline.defense[0] * 0.5),
        )

        # Vital overrides replace the vitals AFTER the modifiers stage, so an
        # overriding subrace lands exactly on its own band floor — not the
        # race vital floor.
        self.assertEqual(dreamer["mp"], 40)
        self.assertNotEqual(dreamer["mp"], race.vital_baseline.mp[0])

    def test_zero_modifier_subrace_matches_race_floor(self):
        self.assertEqual(
            build_initial_traits("t_duskmari", "t_duskmari_plainspan"),
            build_initial_traits("t_duskmari"),
        )

    def test_cross_race_subrace_fails_loudly(self):
        foreign = make_subrace("t_hollowborn_blooded", race_key="t_hollowborn")
        with synthetic_registries("subraces", extra={"subraces": {foreign.key: foreign}}):
            with self.assertRaisesRegex(ValueError, "belongs to race"):
                build_initial_traits("t_duskmari", foreign.key)


if __name__ == "__main__":
    unittest.main()
