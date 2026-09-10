"""Regression tests for independent vital and static race scales.

Every scale read happens inside the synthetic kit: one kit race plus one
invented race whose vital and static bands deliberately differ from each
other, so an axis can only land where its OWN registry band puts it. Shipped
magnitude relationships are catalog data owned by the registered data-contract
suite in ``world/lore/tests/test_races.py``.
"""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.traits import initial_trait_config
from world.tests.synthetic_data import (
    StaticBand,
    SYNTH_RACES,
    Vitals,
    make_race,
    synthetic_registries,
)

# An invented race whose static floors sit far ABOVE its vital floors and far
# above the kit race's statics: any cross-wiring between the vital and static
# axes (or reading one race's band for another race) changes a base value.
_NOBLE_FOLK = make_race(
    "t_noble_folk",
    vital_baseline=Vitals(hp=(120, 240), mp=(40, 90), sp=(60, 130)),
    static_baseline=StaticBand(
        atk_phys=(96, 190),
        agility=(96, 190),
        defense=(96, 190),
        magic_power=(48, 96),
    ),
)


@synthetic_registries(
    "races",
    "static_tiers",
    extra={"races": {_NOBLE_FOLK.key: _NOBLE_FOLK}},
)
class RaceScaleTests(unittest.TestCase):
    @covers_requirement("entity-trait-scales::race-driven-gauge-and-counter-initial-values-come-from-raceprofile-never-a-hardcoded-per-race-number", "entity-trait-scales::static-combat-trait-bases-are-read-directly-from-raceprofile-static-baseline-never-derived-from-vital-baseline")
    def test_vitals_magic_and_statics_use_their_own_registry_axes(self):
        base = initial_trait_config("t_duskmari")
        noble = initial_trait_config("t_noble_folk")
        # The rows the in-scope registry resolves these keys to.
        race = SYNTH_RACES["t_duskmari"]
        strong = _NOBLE_FOLK

        # Gauge bases come from the race's own vital band floor — read through
        # the registry, never a per-race hardcode.
        self.assertEqual(base["hp"]["base"], race.vital_baseline.hp[0])
        self.assertEqual(noble["hp"]["base"], strong.vital_baseline.hp[0])

        # magic_power is a static axis: its base is the STATIC band floor even
        # though the vital mp band differs from it (and per race), which is
        # only observable because the two invented bands disagree.
        self.assertEqual(noble["magic_power"]["trait_type"], "static")
        self.assertEqual(
            noble["magic_power"]["base"],
            strong.static_baseline.magic_power[0],
        )
        self.assertNotEqual(
            noble["magic_power"]["base"],
            strong.vital_baseline.mp[0],
        )

        # The counter axis has its own fixed contract, independent of bands.
        self.assertEqual(noble["guild_merit"]["base"], 0)
        self.assertIsNone(noble["guild_merit"]["max"])

        # Static combat bases read their own race's static band — a race with
        # high statics gets high statics, whatever its vitals say.
        for key in ("atk_phys", "agility", "defense"):
            with self.subTest(axis=key):
                self.assertEqual(
                    base[key]["base"],
                    getattr(race.static_baseline, key)[0],
                )
                self.assertEqual(
                    noble[key]["base"],
                    getattr(strong.static_baseline, key)[0],
                )

    @covers_requirement("entity-trait-scales::static-combat-trait-bases-are-read-directly-from-raceprofile-static-baseline-never-derived-from-vital-baseline")
    def test_statics_do_not_derive_from_vital_scales(self):
        # The invented race's atk floor is 8x its hp floor; the kit race's atk
        # floor is well under its hp floor. A derivation from vitals would
        # collapse both ratios to one.
        base = initial_trait_config("t_duskmari")
        noble = initial_trait_config("t_noble_folk")
        kit_ratio = base["atk_phys"]["base"] / base["hp"]["base"]
        noble_ratio = noble["atk_phys"]["base"] / noble["hp"]["base"]
        self.assertGreater(noble_ratio / kit_ratio, 30)


if __name__ == "__main__":
    unittest.main()
