"""Regression tests for explicit named static tiers.

Runs on the synthetic kit's tier ladder: two kit tiers with deliberately
different physical and magic bands, so landing on a tier's own floor is only
possible through that tier's row (the fourth axis must read ``magic_band``,
never the shared ``band``).
"""

from tools.spec_traceability import covers_requirement

import unittest

from world.rules.traits import build_initial_traits
from world.tests.synthetic_data import (
    SYNTH_STATIC_TIERS,
    make_race,
    make_static_tier,
    synthetic_registries,
)

# A second synthetic race with its own tier, so the cross-race rejection is a
# synthetic-vs-synthetic collision.
_HOLLOW_FOLK = make_race("t_hollow_folk")
_HOLLOW_TIER = make_static_tier(
    "t_hollow_folk_warden",
    race_key="t_hollow_folk",
    band=(5, 12),
    magic_band=(8, 40),
)


@synthetic_registries(
    "races",
    "static_tiers",
    extra={
        "races": {_HOLLOW_FOLK.key: _HOLLOW_FOLK},
        "static_tiers": {_HOLLOW_TIER.key: _HOLLOW_TIER},
    },
)
class TierConstructionTests(unittest.TestCase):
    @covers_requirement("entity-trait-scales::a-caller-may-name-a-static-tier-registry-tier-to-land-inside-a-specific-power-band-instead-of-the-species-floor", "entity-trait-scales::a-caller-may-select-a-deterministic-position-within-a-monster-s-tier-band-instead-of-always-landing-at-the-floor")
    def test_named_tiers_land_on_their_documented_floor(self):
        for tier_key in ("t_duskmari_wanderer", "t_duskmari_warden"):
            tier = SYNTH_STATIC_TIERS[tier_key]
            values = build_initial_traits("t_duskmari", tier=tier_key)
            with self.subTest(tier=tier_key):
                # The named tier overrides the species floor with ITS band
                # floor — the two kit tiers disagree, so one shared number
                # cannot satisfy both.
                for axis in ("atk_phys", "agility", "defense"):
                    self.assertGreaterEqual(values[axis], tier.band[0])
                    self.assertLessEqual(values[axis], tier.band[1])
                    self.assertEqual(values[axis], tier.band[0])
                # The magic axis has its OWN tier band: with the kit tiers'
                # magic floors (6 vs 31) sitting outside the physical bands
                # (1-6 vs 7-18), a leak from ``band`` would land elsewhere.
                self.assertEqual(values["magic_power"], tier.magic_band[0])

    def test_cross_race_tier_fails_and_omission_preserves_floor(self):
        with self.assertRaisesRegex(ValueError, "belongs to race"):
            build_initial_traits("t_hollow_folk", tier="t_duskmari_wanderer")
        self.assertEqual(
            build_initial_traits("t_duskmari"),
            build_initial_traits("t_duskmari", tier=None),
        )


if __name__ == "__main__":
    unittest.main()
