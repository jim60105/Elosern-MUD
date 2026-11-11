"""Behavior tests: one boundary zone pass reads shared population facts once."""

from __future__ import annotations

from types import MappingProxyType
from unittest import TestCase
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
)
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from world.lore.monster_placement import EcologyZone
from world.maps import monster_sites, population_lifecycle
from world.maps import regional_population as owner
from world.maps.population_forecast import ActivitySnapshot, ProjectedZone, _Projection
from world.maps.regional_population import (
    PopulationPresence,
    PopulationPosition,
    counts_from_presence,
    initialize_population_seed,
    note_population_boundaries,
    note_population_boundary,
    zone_counts_from_presence,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import synthetic_registries

KEYS = ("t_a", "t_b", "t_c", "t_d", "t_e", "t_f")
SEED = 11
DELAY = 40
WILDERNESS = "w"


def _index(key: str) -> int:
    return KEYS.index(key)


def _cell(key: str, slot: int = 0) -> tuple[int, int]:
    """One deterministic cell of a synthetic zone's disjoint two-cell area."""
    return (_index(key) * 10 + slot, 0)


def _cells(key: str) -> frozenset[tuple[int, int]]:
    return frozenset({_cell(key, 0), _cell(key, 1)})


#: One placeholder zone object per key, so the geometry seam maps the object
#: ``_zone`` returned to that key's cells without naming a shipped zone.
_PLACEHOLDERS = {key: object() for key in KEYS}
_CELLS_BY_ZONE = {_PLACEHOLDERS[key]: _cells(key) for key in KEYS}


def _zones() -> dict[str, EcologyZone]:
    """Six synthetic zones: 100 eligible cells at 1/99 give a lower bound of 1."""
    return {
        key: EcologyZone(
            key,
            "t_region_placeholder",
            ((0, 0, 0, 0),),
            (),
            lower_density=1,
            upper_density=99,
            cell_capacity=1,
            recovery_delay=DELAY,
            replenishment_interval=5,
            wave_budget=1,
        )
        for key in KEYS
    }


def _eligible_birth_cells(
    zone: EcologyZone, **_: object
) -> tuple[tuple[int, int], ...]:
    """One hundred synthetic eligible cells per zone (a placeholder geometry)."""
    base = _index(zone.key) * 1000
    return tuple((base + offset, 0) for offset in range(100))


def _fact(
    *,
    alive: bool = True,
    cell: tuple[int, int] | None = None,
    home: str | None = None,
    wilderness: str = WILDERNESS,
) -> PopulationPresence:
    return PopulationPresence(
        alive,
        None if cell is None else PopulationPosition(wilderness, cell[0], cell[1]),
        home,
        None,
    )


class CountingPresence(dict):
    """A presence mapping that counts how often it is iterated."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_calls = 0

    def items(self):
        self.items_calls += 1
        return super().items()


def _presence() -> CountingPresence:
    """One living occupant per zone, one outside home owner, one dead, one foreign."""
    presence = CountingPresence()
    for offset, key in enumerate(KEYS):
        presence[100 + offset] = _fact(cell=_cell(key))
    presence[200] = _fact(cell=(999, 999), home="t_c")
    presence[201] = _fact(alive=False, cell=_cell("t_a"))
    presence[202] = _fact(cell=_cell("t_b"), wilderness="other")
    return presence


class ZoneCountsIndexTests(TestCase):
    """The batch reader measures many zones from one presence scan."""

    def _use_seams(self) -> None:
        self.enterContext(patch.object(owner, "_zone", lambda key: _PLACEHOLDERS[key]))
        self.enterContext(
            patch.object(owner, "_region_cells", lambda zone: _CELLS_BY_ZONE[zone])
        )

    @covers_requirement(
        "regional-population::boundary-zone-passes-read-shared-population-facts-once-per-pass"
    )
    def test_one_scan_serves_every_zone(self):
        self._use_seams()
        presence = _presence()

        counts = zone_counts_from_presence(KEYS, presence, wilderness=WILDERNESS)

        self.assertEqual(presence.items_calls, 1)
        for offset, key in enumerate(KEYS):
            self.assertEqual(counts[key].local_ids, frozenset({100 + offset}))
            self.assertEqual(
                counts[key].cell_ids, {_cell(key): frozenset({100 + offset})}
            )
        self.assertEqual(counts["t_c"].home_ids, frozenset({200}))
        for key in KEYS:
            if key != "t_c":
                self.assertEqual(counts[key].home_ids, frozenset())
        self.assertNotIn(201, counts["t_a"].local_ids)
        self.assertNotIn(202, counts["t_b"].local_ids)
        self.assertEqual(counts["t_a"].cell_ids.keys(), {_cell("t_a")})
        # A home owner with no position is still home-owned, never local.
        positionless = _presence()
        positionless[203] = _fact(cell=None, home="t_c")
        counted = zone_counts_from_presence(
            KEYS, positionless, wilderness=WILDERNESS
        )
        self.assertEqual(counted["t_c"].home_ids, frozenset({200, 203}))
        self.assertNotIn(203, counted["t_c"].local_ids)
        # A repeated key and an empty key list keep the per-key answer.
        repeated = zone_counts_from_presence(
            KEYS + ("t_a",), positionless, wilderness=WILDERNESS
        )
        self.assertEqual(repeated["t_a"], counted["t_a"])
        self.assertEqual(
            zone_counts_from_presence((), positionless, wilderness=WILDERNESS), {}
        )

    @covers_requirement(
        "regional-population::boundary-zone-passes-read-shared-population-facts-once-per-pass"
    )
    def test_single_zone_reader_agrees(self):
        self._use_seams()
        presence = _presence()

        batch = zone_counts_from_presence(KEYS, presence, wilderness=WILDERNESS)

        for key in KEYS:
            self.assertEqual(
                counts_from_presence(key, presence, wilderness=WILDERNESS),
                batch[key],
            )


class ZonePassDecodeTests(RegistryIsolationMixin, EvenniaTest):
    """One boundary zone pass decodes the shared state map once."""

    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.enterContext(
            patch.object(
                owner, "ECOLOGY_ZONE_REGISTRY", MappingProxyType(_zones())
            )
        )
        self.enterContext(
            patch.object(owner, "_region_cells", lambda zone: _cells(zone.key))
        )
        self.enterContext(
            patch.object(owner, "eligible_birth_cells", _eligible_birth_cells)
        )
        self.enterContext(
            patch.object(
                monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({})
            )
        )
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)

    def _state(self, due: dict[str, int | None] | None = None) -> None:
        """Commit every synthetic zone's selection state directly."""
        due = due or {}
        self.wilderness.db.regional_population = {
            key: {
                "initialized": True,
                "seed": SEED,
                "generation_sequence": 0,
                "recovery_due_tick": due.get(key),
                "settled_through_tick": 0,
            }
            for key in KEYS
        }

    def _records(self) -> dict[str, dict]:
        return {
            key: dict(value)
            for key, value in self.wilderness.db.regional_population.items()
        }

    @covers_requirement(
        "regional-population::boundary-zone-passes-read-shared-population-facts-once-per-pass"
    )
    def test_note_pass_decodes_once(self):
        self._state()
        original = self._records()

        with patch.object(owner, "_state_map", wraps=owner._state_map) as decode:
            note_population_boundaries(self.wilderness, KEYS, tick=100)

        self.assertEqual(decode.call_count, 1)
        batch = self._records()
        for key in KEYS:
            self.assertEqual(batch[key]["recovery_due_tick"], 100 + DELAY)
            self.assertEqual(batch[key]["settled_through_tick"], 100)
        # The single-zone call is the reference result the pass must reproduce.
        self.wilderness.db.regional_population = original
        for key in KEYS:
            note_population_boundary(self.wilderness, key, tick=100)
            self.assertEqual(self._records()[key], batch[key])

    @covers_requirement(
        "regional-population::boundary-zone-passes-read-shared-population-facts-once-per-pass"
    )
    def test_due_reader_decodes_once_and_filters(self):
        self._state({"t_b": 50, "t_e": 50, "t_c": 500})

        with patch.object(owner, "_state_map", wraps=owner._state_map) as decode:
            due = owner.due_recovery_zone_keys(self.wilderness, tick=100)

        self.assertEqual(due, ("t_b", "t_e"))
        self.assertEqual(decode.call_count, 1)

    @covers_requirement(
        "regional-population::boundary-zone-passes-read-shared-population-facts-once-per-pass"
    )
    def test_lifecycle_settles_only_due_zones(self):
        self._state({"t_b": 50, "t_e": 50, "t_c": 500})

        with patch.object(
            population_lifecycle.regional_population,
            "settle_recovery_due",
            wraps=population_lifecycle.regional_population.settle_recovery_due,
        ) as settle:
            population_lifecycle._settle_population_at(self.wilderness, 100)

        self.assertEqual(
            [call.args[1] for call in settle.call_args_list], ["t_b", "t_e"]
        )


class ForecastZoneNoteTests(TestCase):
    """One projected zone note scans the projected presence once."""

    @covers_requirement(
        "regional-population::boundary-zone-passes-read-shared-population-facts-once-per-pass"
    )
    def test_zone_note_scans_once(self):
        self.enterContext(patch.object(owner, "_zone", lambda key: _PLACEHOLDERS[key]))
        self.enterContext(
            patch.object(owner, "_region_cells", lambda zone: _CELLS_BY_ZONE[zone])
        )
        self.enterContext(patch.object(owner, "zone_lower_bound", lambda key: 1))
        self.enterContext(
            patch.object(
                owner, "ECOLOGY_ZONE_REGISTRY", MappingProxyType(_zones())
            )
        )
        snapshot = ActivitySnapshot(
            groups=(),
            journeys=(),
            presence=(),
            zones=tuple(
                ProjectedZone(
                    key=key,
                    seed=SEED,
                    generation_sequence=0,
                    recovery_due_tick=None,
                    settled_through_tick=0,
                )
                for key in KEYS
            ),
            sites=(),
            protection=(),
            room_protection=(),
            physiology=(),
            condition_ticks=(),
            wilderness=WILDERNESS,
        )
        projection = _Projection(
            snapshot, start_tick=0, wilderness=WILDERNESS, observers=()
        )

        with patch.object(
            owner,
            "zone_counts_from_presence",
            wraps=owner.zone_counts_from_presence,
        ) as batch:
            projection._note_zone_boundary(10)

        self.assertEqual(batch.call_count, 1)
        for key in KEYS:
            self.assertEqual(projection.zones[key].recovery_due_tick, 10 + DELAY)
