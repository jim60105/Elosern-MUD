"""Monster site journeys (row_vocabulary)."""

from evennia.utils.test_resources import EvenniaTest
from typeclasses.monsters import Monster
from world.lore.monster_placement import RECOVERY_CONDITION_FIELDS, MonsterSite, composition_variant_keys
from world.maps import monster_sites
from world.maps.monster_sites import SITE_STATE_POPULATED, site_state
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.wilderness_provider import WILDERNESS_NAME, ElosernWildernessMapProvider, region_for_coordinates
from world.maps.regional_population import initialize_population_seed
from world.tests.synthetic_data import synthetic_registries


from ._support import COMPOSITIONS, HOUR, PROBE, SEED, SOLO, STATIONARY_ACTIVITY, _members

class SiteRowVocabularyTests(EvenniaTest):
    """The authored vocabulary the owner reads is the registry's own."""

    def test_the_owner_reads_the_registry_instead_of_a_local_copy(self):
        site = MonsterSite(
            "t_vocabulary_site",
            "boss_site",
            region_for_coordinates(*PROBE),
            PROBE,
            SOLO,
            STATIONARY_ACTIVITY,
            1,
            False,
            HOUR,
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
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(wilderness, seed=SEED, tick=0)
        with self.captureOnCommitCallbacks(execute=True):
            settle_population_lifecycle(0, 0)
        members = _members(wilderness, site)
        self.assertEqual(len(members), site.capacity)
        self.assertEqual(RECOVERY_CONDITION_FIELDS, ("recover_after_ticks",))
        state = site_state(site.key, wilderness=wilderness)
        self.assertEqual(state.state, SITE_STATE_POPULATED)
        self.assertIsNone(state.cleared_at_tick)
        # The authored row drove the population: the owner holds no second copy
        # of a site's capacity or lifecycle.
        self.assertEqual(
            members[0].variant_key,
            composition_variant_keys(COMPOSITIONS[SOLO])[0],
        )
