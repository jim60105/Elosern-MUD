"""Shared fixture for the monster site test package."""

from evennia.utils.test_resources import EvenniaTest
from typeclasses.monsters import Monster
from world.lore.monster_placement import CompositionMember, EcologyZone, EncounterComposition, MonsterSite, WeightedComposition
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps import monster_sites
from world.maps import regional_population
from world.maps.geography import current as current_geography
from world.maps.population_geometry import INHABITED_SETTLEMENT_KINDS, eligible_birth_cells
from world.maps.monster_sites import SITE_STAGE_KIND
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.wilderness_population import _stored_hp
from world.maps.wilderness_provider import WILDERNESS_NAME, ElosernWildernessMapProvider, is_valid_wilderness_cell, region_for_coordinates
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.maps.regional_population import initialize_population_seed
from world.rules import clock as clock_module
from world.rules.clock import get_world_clock
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import SYNTH_MONSTER_ACTIVITIES, SYNTH_MONSTER_TIERS, SYNTH_MONSTER_VARIANTS, synthetic_registries


def _members(wilderness, site: MonsterSite) -> tuple[Monster, ...]:
    return monster_sites._members(wilderness, site)

def _living(wilderness, site: MonsterSite) -> tuple[Monster, ...]:
    return tuple(member for member in _members(wilderness, site) if _stored_hp(member) > 0)

def _cell_zone(cell: tuple[int, int], region: str) -> EcologyZone:
    """One synthetic ecology zone covering exactly ``cell``."""
    x, y = cell
    return EcologyZone(
        "t_probe_zone",
        region,
        ((x, x, y, y),),
        (WeightedComposition(SOLO, 1),),
        1,
        1,
        3,
        3600,
        600,
        3,
    )

def _eligible_birth_cells(zone: EcologyZone) -> tuple[tuple[int, int], ...]:
    """The ordinary birth cells of ``zone`` in the published test world."""
    return eligible_birth_cells(
        zone,
        geography=current_geography(),
        entries=WILDERNESS_ENTRY_REGISTRY,
        policies={},
    )

def _inhabited_settlement_cells():
    """Every published cell of an inhabited settlement (footprint or anchor)."""
    geography = current_geography()
    for anchor_key, anchor in geography.anchors.items():
        if anchor.kind not in INHABITED_SETTLEMENT_KINDS:
            continue
        entry = WILDERNESS_ENTRY_REGISTRY.get(anchor_key)
        if entry is not None and entry.footprint_cells:
            yield from sorted(entry.footprint_cells)
            continue
        published = geography.anchor_geography.get(anchor_key)
        if published is not None and published.cell is not None:
            yield published.cell

def _buffer_cell_inside_a_settlement_ring() -> tuple[int, int]:
    """A valid wild cell that ordinary birth geometry excludes.

    The cell is one Chebyshev step outside a published inhabited settlement, so
    it is lawful explicit-placement ground while the generic settlement buffer
    keeps it out of automatic birth geometry.
    """
    for settlement_cell in _inhabited_settlement_cells():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                cell = (settlement_cell[0] + dx, settlement_cell[1] + dy)
                if not is_valid_wilderness_cell(cell):
                    continue
                region = region_for_coordinates(*cell)
                if _eligible_birth_cells(_cell_zone(cell, region)):
                    continue
                return cell
    raise AssertionError("no excluded-but-valid wilderness cell was published")

_VARIANTS = tuple(SYNTH_MONSTER_VARIANTS)

ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]

ORDINARY, STRONGER = _VARIANTS[0], _VARIANTS[1]

_WITNESS_TIER = next(iter(SYNTH_MONSTER_TIERS))

#: A walkable south-western wild cell: outside the capital's and the village's
#: anchor footprints and far from the contract-pinned hunting band.
PROBE = (500, 700)

SOLITARY_ACTIVITY = "t_whisper_quail_solitary_activity"

GROUP_ACTIVITY = "t_whisper_quail_group_activity"

STATIONARY_ACTIVITY = "t_whisper_quail_stationary"

assert {SOLITARY_ACTIVITY, GROUP_ACTIVITY, STATIONARY_ACTIVITY} <= set(
    SYNTH_MONSTER_ACTIVITIES
)

NEST_KEY = "t_probe_nest"

CAMP_KEY = "t_probe_camp"

GROUP_KEY = "t_probe_group"

STRAY_KEY = "t_probe_stray"

COHESIVE_KEY = "t_probe_cohesive"

MIXED_KEY = "t_probe_mixed"

OVERRIDE_KEY = "t_probe_override"

LABELLED_KEY = "t_probe_labelled"

UNLABELLED_KEY = "t_probe_unlabelled"

LABEL = "探針首領"

HOUR = 3600

SEED = 11

PAIR = "t_probe_pair"

GROUP = "t_probe_group_composition"

SOLO = "t_probe_solo"

FLOCK = "t_probe_flock"

MIXED = "t_probe_mixed_composition"

#: One solitary composition, one same-variant group, one mixed pair and one
#: variable-range group, all built from the kit's synthetic variants. The
#: variable range is what makes a wrong occurrence input observable: a fixed
#: group would look deterministic even if the sampler ignored its seed.
COMPOSITIONS = {
    PAIR: EncounterComposition(
        PAIR,
        GROUP_ACTIVITY,
        (
            CompositionMember(ORDINARY, 1, 1),
            CompositionMember(STRONGER, 1, 1),
        ),
    ),
    GROUP: EncounterComposition(
        GROUP,
        GROUP_ACTIVITY,
        (
            CompositionMember(ORDINARY, 2, 2),
            CompositionMember(STRONGER, 1, 1),
        ),
    ),
    SOLO: EncounterComposition(
        SOLO, SOLITARY_ACTIVITY, (CompositionMember(STRONGER, 1, 1),)
    ),
    FLOCK: EncounterComposition(
        FLOCK, GROUP_ACTIVITY, (CompositionMember(ORDINARY, 1, 2),)
    ),
    # One cohesive pair beside one independent individual: the row bindings are
    # what separate them, because no site override is declared.
    MIXED: EncounterComposition(
        MIXED,
        GROUP_ACTIVITY,
        (
            CompositionMember(ORDINARY, 2, 2, GROUP_ACTIVITY),
            CompositionMember(STRONGER, 1, 1, SOLITARY_ACTIVITY),
        ),
    ),
}

class _MonsterSiteFixture(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """One provisioned site world per test; the subclasses carry the journeys."""

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        self.region = region_for_coordinates(*PROBE)
        self.sites = {
            NEST_KEY: MonsterSite(
                NEST_KEY,
                "nest",
                self.region,
                PROBE,
                PAIR,
                STATIONARY_ACTIVITY,
                2,
                True,
            ),
            CAMP_KEY: MonsterSite(
                CAMP_KEY,
                "camp",
                self.region,
                PROBE,
                PAIR,
                STATIONARY_ACTIVITY,
                2,
                False,
                HOUR,
            ),
            GROUP_KEY: MonsterSite(
                GROUP_KEY,
                "encounter",
                self.region,
                PROBE,
                GROUP,
                STATIONARY_ACTIVITY,
                3,
                True,
            ),
            STRAY_KEY: MonsterSite(
                STRAY_KEY,
                "stray",
                self.region,
                PROBE,
                SOLO,
                STATIONARY_ACTIVITY,
                1,
                True,
            ),
            MIXED_KEY: MonsterSite(
                MIXED_KEY,
                "encounter",
                self.region,
                PROBE,
                MIXED,
                None,
                3,
                True,
            ),
            OVERRIDE_KEY: MonsterSite(
                OVERRIDE_KEY,
                "encounter",
                self.region,
                PROBE,
                MIXED,
                STATIONARY_ACTIVITY,
                3,
                True,
            ),
            LABELLED_KEY: MonsterSite(
                LABELLED_KEY,
                "stray",
                self.region,
                PROBE,
                SOLO,
                None,
                1,
                True,
                individual_name_zh=LABEL,
            ),
            UNLABELLED_KEY: MonsterSite(
                UNLABELLED_KEY,
                "stray",
                self.region,
                PROBE,
                SOLO,
                None,
                1,
                True,
            ),
        }
        self.enterContext(
            synthetic_registries(
                "monster_species",
                "monster_variants",
                "monster_tiers",
                "monster_sites",
                extra={
                    "encounter_compositions": COMPOSITIONS,
                    "monster_sites": self.sites,
                },
            )
        )
        from world.maps.population_lifecycle import register_regional_population

        register_regional_population()
        self.addCleanup(clock_module._EVENT_SOURCES.pop, SITE_STAGE_KIND, None)

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        # The site owner derives each site's occurrence from the one explicit
        # world seed; a world without it refuses instead of guessing.
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.clock = get_world_clock()
    def _settle(self, end_tick: int = 0):
        with self.captureOnCommitCallbacks(execute=True):
            return settle_population_lifecycle(0, end_tick)
    def _defeat(self, site: MonsterSite) -> tuple[int, ...]:
        """Defeat every member and record each committed loss occurrence."""
        from world.maps import regional_population
        from world.rules.clock import read_world_clock

        clock = read_world_clock()
        tick = 0 if clock is None else clock.tick
        defeated = []
        for member in _members(self.wilderness, site):
            before = regional_population.presence_of(self.wilderness, member)
            member.traits.hp.current = 0
            defeated.append(member.pk)
            regional_population.record_population_transition(
                self.wilderness,
                regional_population.PopulationTransition(
                    source_id=f"test-defeat:{member.pk}",
                    individual_id=int(member.pk),
                    occurred_tick=tick,
                    before=before,
                    after=regional_population.presence_of(
                        self.wilderness, member, alive=False
                    ),
                ),
            )
        return tuple(defeated)
