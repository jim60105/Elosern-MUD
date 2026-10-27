"""Data-contract test: nation data contract
Self-consistency checks for nations and capital anchors."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.anchors import AnchorKind, anchors
from world.lore.nations import (
    CAPITAL_POPULATION_SHARE,
    CAPITAL_SUPPORT_REGISTRY,
    CONTINENT_AREA_KM2,
    CONTINENT_POPULATION,
    ELVEN_POPULATION,
    NEUTRAL_LANDS_AREA_KM2,
    NEUTRAL_LANDS_POPULATION,
    NATION_REGISTRY,
    SupplyBasis,
)
from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    publish_shipped_geography()


class NationRegistryTests(unittest.TestCase):
    def test_three_nations_and_capitals(self):
        self.assertEqual(set(NATION_REGISTRY), {"grandia", "altoria", "valhalla"})
        for nation in NATION_REGISTRY.values():
            anchor = anchors()[nation.capital_anchor_key]
            self.assertEqual(anchor.kind, AnchorKind.CAPITAL)
            self.assertEqual(anchor.nation_key, nation.key)

    @covers_requirement("lore-registries::nation-registry-covers-the-three-states")
    def test_territory_shares_leave_neutral_land(self):
        total = sum(nation.territory_share for nation in NATION_REGISTRY.values())
        self.assertGreaterEqual(total, 0.85)
        self.assertLessEqual(total, 1.0)

    @covers_requirement(
        "continental-geography::population-and-territory-targets-preserve-authored-settlement-scale"
    )
    def test_rounded_national_targets_fill_the_continental_area(self):
        self.assertEqual(CONTINENT_AREA_KM2, 5_000_000)
        self.assertEqual(CONTINENT_POPULATION, 30_000_000)
        self.assertEqual(NEUTRAL_LANDS_AREA_KM2, 500_000)
        self.assertIsNone(NEUTRAL_LANDS_POPULATION)
        expected = {
            "grandia": (12_000_000, 0.38, 1_900_000),
            "altoria": (9_000_000, 0.27, 1_350_000),
            "valhalla": (9_000_000, 0.25, 1_250_000),
        }
        # Design §4 means: the totals produce an average of ~6-7 inhabitants
        # per km², so density is an authored mean, never a per-cell allocation.
        expected_density = {"grandia": 6.3, "altoria": 6.7, "valhalla": 7.2}
        for key, (population, share, area_km2) in expected.items():
            with self.subTest(nation=key):
                nation = NATION_REGISTRY[key]
                self.assertEqual(nation.population, population)
                self.assertEqual(nation.territory_share, share)
                self.assertEqual(nation.territory_km2, area_km2)
                self.assertEqual(share * CONTINENT_AREA_KM2, area_km2)
                self.assertAlmostEqual(
                    nation.mean_inhabitants_per_km2, expected_density[key], places=1
                )
        self.assertEqual(
            sum(nation.population for nation in NATION_REGISTRY.values()),
            CONTINENT_POPULATION,
        )
        self.assertEqual(
            sum(nation.territory_km2 for nation in NATION_REGISTRY.values())
            + NEUTRAL_LANDS_AREA_KM2,
            CONTINENT_AREA_KM2,
        )

    @covers_requirement(
        "continental-geography::population-and-territory-targets-preserve-authored-settlement-scale"
    )
    def test_capitals_hold_six_percent_with_authored_regional_support(self):
        capitals = {
            key: anchor
            for key, anchor in anchors().items()
            if anchor.kind == AnchorKind.CAPITAL
        }
        self.assertEqual(
            {key: anchor.population for key, anchor in capitals.items()},
            {
                "capital_grandia": 800_000,
                "capital_altoria": 600_000,
                "capital_valhalla": 400_000,
            },
        )
        self.assertEqual(sum(anchor.population for anchor in capitals.values()), 1_800_000)
        self.assertEqual(
            sum(anchor.population for anchor in capitals.values()),
            CAPITAL_POPULATION_SHARE * CONTINENT_POPULATION,
        )
        self.assertEqual(set(CAPITAL_SUPPORT_REGISTRY), set(capitals))
        for key in capitals:
            with self.subTest(capital=key):
                support = CAPITAL_SUPPORT_REGISTRY[key]
                self.assertTrue(
                    {
                        SupplyBasis.REGIONAL_FOOD,
                        SupplyBasis.STORAGE,
                        SupplyBasis.WATER,
                    }
                    <= support.supply_bases
                )
        self.assertTrue(
            {
                SupplyBasis.PASTORAL_PRODUCTION,
                SupplyBasis.TRADE,
            }
            <= CAPITAL_SUPPORT_REGISTRY["capital_valhalla"].supply_bases
        )

    @covers_requirement(
        "continental-geography::population-and-territory-targets-preserve-authored-settlement-scale"
    )
    def test_elven_population_is_the_three_village_rounded_total(self):
        elven = [
            anchor
            for anchor in anchors().values()
            if anchor.kind == AnchorKind.ELVEN_VILLAGE
        ]
        self.assertEqual(len(elven), 3)
        self.assertEqual(sum(anchor.population for anchor in elven), ELVEN_POPULATION)
        self.assertEqual(ELVEN_POPULATION, 300)
