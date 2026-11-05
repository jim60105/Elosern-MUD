"""Monster site journeys (without_world)."""

from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTest
from typeclasses.monsters import Monster
from world.lore.monster_placement import MonsterSite
from world.maps import monster_sites
from world.maps.monster_sites import SITE_STAGE_KIND, SITE_READ_WORLD_UNAVAILABLE, site_living_members, site_state, snapshot_monster_site_surfaces
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.wilderness_provider import WILDERNESS_NAME, ElosernWildernessMapProvider
from world.maps.regional_population import PopulationSeedUninitialized
from world.rules import clock as clock_module
from world.rules.clock import AdvanceSource, get_world_clock
from world.tests.synthetic_data import synthetic_registries


from ._support import COMPOSITIONS, SOLO, STATIONARY_ACTIVITY

class MonsterSiteStageWithoutWorldTests(EvenniaTest):
    """The stage is silent while no wilderness script exists."""

    def test_settlement_and_contract_are_absent_tolerant(self):
        from world.maps.population_lifecycle import register_regional_population

        register_regional_population()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)
        self.assertFalse(search_script(WILDERNESS_NAME))
        with (
            patch("world.maps.monster_sites.log_info") as info,
            patch("world.maps.monster_sites.log_warn") as warn,
            self.captureOnCommitCallbacks(execute=True),
        ):
            events = get_world_clock().advance(60, AdvanceSource.SKIP, [])
            self.assertEqual(settle_population_lifecycle(0, 1000), [])
            self.assertEqual(snapshot_monster_site_surfaces(0, 1000), {})
        info.assert_not_called()
        warn.assert_not_called()
        self.assertEqual(
            [event.kind for event in events if event.kind == "monster_site_recovered"],
            [],
        )

    @covers_requirement("monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain")
    @covers_requirement("monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site")
    def test_the_read_refuses_when_no_world_is_provisioned(self):
        # Refusing is the read's answer, not an exception, and it provisions
        # nothing: no wilderness script may appear because a quest asked.
        self.assertFalse(search_script(WILDERNESS_NAME))

        read = site_living_members("t_absent_site")

        self.assertFalse(read.available)
        self.assertEqual(read.reason, SITE_READ_WORLD_UNAVAILABLE)
        self.assertEqual(read.members, ())
        self.assertIsNone(read.site)
        self.assertIsNone(read.state)
        self.assertFalse(search_script(WILDERNESS_NAME))

class MonsterSiteWithoutWorldSeedTests(EvenniaTest):
    """A world that never initialized its seed refuses before any site write."""

    @covers_requirement("monster-site-placement::placement-samples-complete-deterministic-occurrences")
    def test_first_population_refuses_without_an_explicit_world_seed(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
        )

        site = MonsterSite(
            "t_seedless_site",
            "nest",
            "t_bramble_wold",
            (5, 5),
            SOLO,
            STATIONARY_ACTIVITY,
            1,
            True,
        )
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": {site.key: site},
                },
            )
        )

        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters_before = sorted(Monster.objects.values_list("pk", flat=True))

        with self.assertRaises(PopulationSeedUninitialized):
            with self.captureOnCommitCallbacks(execute=True):
                monster_sites.settle_monster_sites_at(0)

        self.assertIsNone(site_state(site.key, wilderness=wilderness))
        self.assertEqual(
            sorted(Monster.objects.values_list("pk", flat=True)), monsters_before
        )
