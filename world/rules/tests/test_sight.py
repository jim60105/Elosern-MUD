"""Data-contract test: the sight rulebook's schema keys and loader rejection boundaries are the contract under test; every assertion injects a synthetic policy and never pins shipped values or wording

Focused tests for the pure wilderness sight rules (wilderness-sight-rules).

Every case injects a synthetic policy, synthetic sources and fixed calendar
hours, so no expected value comes from the shipped rulebook, from a coordinate
table or from the function under test. The assertions establish the mechanism:
the phase boundaries, the radius composition (terrain, canopy-suppressed tier,
vantage override, the hard maximum), the disc predicate's edges, the phase
visibility of distant sources, bearing and distance rounding ties, source
privacy and merging, policy rejection boundaries, and the fact that reading
markers writes nothing and never lights a district.
"""

from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

from world.lore.anchors import AnchorKind
from world.rules.sight import (
    BEARINGS,
    HIDDEN_ANCHOR_KINDS,
    MARKER_KEYS,
    MAX_GROUND_SIGHT_RADIUS,
    SILHOUETTE_MAX_CODE_POINTS,
    GroundSightInputs,
    LandmarkSighting,
    SettlementFootprint,
    SightRulebookError,
    SightSource,
    bearing_index,
    bearing_label,
    distant_markers,
    distant_sources,
    ground_radius,
    in_ground_disc,
    landmark_sources,
    light_phase,
    load_policy,
    merge_sources,
    rounded_distance_km,
    settlement_sources,
    settlement_placements,
    validate_sight_region_coverage,
)


def _document(**overrides):
    """One synthetic sight policy with distinctive, round numbers."""

    document = {
        "phases": [
            {"name": "day", "start_hour": 8, "column": "day"},
            {"name": "dusk", "start_hour": 16, "column": "twilight"},
            {"name": "night", "start_hour": 20, "column": "night"},
            {"name": "dawn", "start_hour": 4, "column": "twilight"},
        ],
        "terrain_radius": {
            "meadow": {"day": 2, "twilight": 1, "night": 0},
            "ridge": {"day": 3, "twilight": 2, "night": 1},
            "canopy": {"day": 1, "twilight": 1, "night": 0},
        },
        "region_terrain": {
            "t_meadow_region": "meadow",
            "t_ridge_region": "ridge",
            "t_canopy_region": "canopy",
        },
        "canopy_terrain": ["canopy"],
        "prominence_bonus": [
            {"day": 0, "twilight": 0, "night": 0},
            {"day": 1, "twilight": 0, "night": 0},
            {"day": 2, "twilight": 1, "night": 0},
            {"day": 3, "twilight": 2, "night": 0},
        ],
        "vantage_radius": {"day": 6, "twilight": 4, "night": 2},
        "twilight_factor": 0.5,
        "settlement_footprint_factor": {"day": 3, "night": 1},
        "settlement_silhouettes": {
            "capital": {"day": "合成城牆側影", "night": "合成城鎮燈火"}
        },
    }
    document.update(overrides)
    return document


def _synthetic_policy(**overrides):
    """Load one synthetic policy from an explicit temporary document."""

    document = _document(**overrides)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "sight.yaml"
        path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")
        return load_policy(path)


def _rejected(test: unittest.TestCase, document) -> str:
    """The rejection message of an invalid policy document."""

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "sight.yaml"
        path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")
        with test.assertRaises(SightRulebookError) as caught:
            load_policy(path)
    return str(caught.exception)


def _hour(hour: int) -> SimpleNamespace:
    return SimpleNamespace(hour=hour)


class LightPhaseTests(unittest.TestCase):
    """Phase boundaries are inclusive at their start hour."""

    def test_every_phase_boundary_belongs_to_the_phase_that_starts_at_it(self):
        policy = _synthetic_policy()
        cases = {
            0: "night",
            3: "night",
            4: "dawn",
            7: "dawn",
            8: "day",
            15: "day",
            16: "dusk",
            19: "dusk",
            20: "night",
            23: "night",
        }
        for hour, expected in cases.items():
            with self.subTest(hour=hour):
                self.assertEqual(light_phase(_hour(hour), policy=policy), expected)
                self.assertEqual(policy.phase_for_hour(hour)[0], expected)

    def test_the_phase_column_is_the_twilight_column_at_dusk_and_dawn(self):
        policy = _synthetic_policy()
        self.assertEqual(policy.phase_for_hour(5)[1], "twilight")
        self.assertEqual(policy.phase_for_hour(17)[1], "twilight")
        self.assertEqual(policy.phase_for_hour(9)[1], "day")
        self.assertEqual(policy.phase_for_hour(21)[1], "night")

    def test_an_hour_outside_the_clock_is_rejected(self):
        policy = _synthetic_policy()
        for hour in (-1, 24, True, "8", None):
            with self.subTest(hour=hour):
                with self.assertRaises(ValueError):
                    light_phase(SimpleNamespace(hour=hour), policy=policy)


class GroundRadiusTests(unittest.TestCase):
    """The radius composition, its override rule and its hard maximum."""

    def test_terrain_and_prominence_add_while_a_vantage_overrides(self):
        policy = _synthetic_policy()
        noon = _hour(12)
        # ridge day 3 + tier 2 bonus 2 = 5.
        self.assertEqual(
            ground_radius(noon, GroundSightInputs("ridge", 2, False), policy=policy), 5
        )
        # The vantage row (6) is larger, so it wins instead of being added.
        self.assertEqual(
            ground_radius(noon, GroundSightInputs("ridge", 2, True), policy=policy), 6
        )
        # At twilight the same cell picks the twilight column: 2 + 1 = 3.
        self.assertEqual(
            ground_radius(_hour(17), GroundSightInputs("ridge", 2, False), policy=policy), 3
        )
        # At dawn (twilight column) the vantage row 4 wins again.
        self.assertEqual(
            ground_radius(_hour(5), GroundSightInputs("ridge", 2, True), policy=policy), 4
        )

    def test_canopy_suppresses_the_tier_but_a_vantage_stays_eligible(self):
        policy = _synthetic_policy()
        noon = _hour(12)
        # Canopy day 1 + tier 3 bonus 3 would be 4; the canopy forces tier 0.
        self.assertEqual(
            ground_radius(noon, GroundSightInputs("canopy", 3, False), policy=policy), 1
        )
        # The vantage row still applies on a canopy cell.
        self.assertEqual(
            ground_radius(noon, GroundSightInputs("canopy", 3, True), policy=policy), 6
        )

    def test_the_hard_maximum_is_reachable_but_never_exceeded(self):
        policy = _synthetic_policy(vantage_radius={"day": 8, "twilight": 5, "night": 2})
        self.assertEqual(
            ground_radius(
                _hour(12), GroundSightInputs("meadow", 0, True), policy=policy
            ),
            MAX_GROUND_SIGHT_RADIUS,
        )

    def test_an_unclassifiable_cell_or_tier_is_rejected(self):
        policy = _synthetic_policy()
        for inputs in (
            GroundSightInputs("t_absent_row", 0, False),
            GroundSightInputs("meadow", 4, False),
            GroundSightInputs("meadow", -1, False),
            GroundSightInputs("meadow", True, False),
        ):
            with self.subTest(inputs=inputs):
                with self.assertRaises((ValueError, SightRulebookError)):
                    ground_radius(_hour(12), inputs, policy=policy)

    def test_a_policy_change_moves_only_the_corresponding_results(self):
        baseline = _synthetic_policy()
        # One terrain radius changes, and only the day column of that row.
        changed_row = dict(_document()["terrain_radius"])
        changed_row["meadow"] = {"day": 5, "twilight": 1, "night": 0}
        changed = _synthetic_policy(terrain_radius=changed_row)
        meadow = GroundSightInputs("meadow", 0, False)
        ridge = GroundSightInputs("ridge", 0, False)
        self.assertEqual(ground_radius(_hour(12), meadow, policy=baseline), 2)
        self.assertEqual(ground_radius(_hour(12), meadow, policy=changed), 5)
        # Everything the edit did not name is unchanged.
        self.assertEqual(
            ground_radius(_hour(12), ridge, policy=baseline),
            ground_radius(_hour(12), ridge, policy=changed),
        )
        self.assertEqual(
            ground_radius(_hour(17), meadow, policy=baseline),
            ground_radius(_hour(17), meadow, policy=changed),
        )


class GroundDiscTests(unittest.TestCase):
    """The one disc predicate, including its radius 0 and radius 8 edges."""

    def test_radius_zero_covers_only_the_observer_cell(self):
        self.assertTrue(in_ground_disc((5, 5), (5, 5), 0))
        for target in ((6, 5), (5, 6), (6, 6), (4, 5)):
            with self.subTest(target=target):
                self.assertFalse(in_ground_disc((5, 5), target, 0))

    def test_the_edge_is_the_half_cell_inclusive_circle(self):
        # radius 1: (1,1) is sqrt(2) ~ 1.414 <= 1.5, (2,0) is 2 > 1.5.
        self.assertTrue(in_ground_disc((0, 0), (1, 1), 1))
        self.assertFalse(in_ground_disc((0, 0), (2, 0), 1))
        self.assertTrue(in_ground_disc((0, 0), (1, 0), 1))

    def test_radius_eight_reaches_the_diagonal_inside_and_rejects_outside(self):
        # 5-5-... diagonal: 6 * sqrt(2) = 8.49 <= 8.5, 7 sqrt(2) = 9.9 > 8.5.
        self.assertTrue(in_ground_disc((10, 10), (16, 16), 8))
        self.assertFalse(in_ground_disc((10, 10), (17, 17), 8))
        self.assertFalse(in_ground_disc((10, 10), (19, 10), 8))
        self.assertTrue(in_ground_disc((10, 10), (18, 10), 8))


class BearingAndDistanceTests(unittest.TestCase):
    """Sixteen north-clockwise sectors and 5 km rounding, ties clockwise/up."""

    def test_sectors_are_north_clockwise_and_wrap_at_north(self):
        origin = (0, 0)
        cases = {
            (0, 10): "北",
            (10, 0): "東",
            (0, -10): "南",
            (-10, 0): "西",
            (10, 10): "東北",
            (-10, 10): "西北",
            (10, -10): "東南",
            (-10, -10): "西南",
        }
        for target, expected in cases.items():
            with self.subTest(target=target):
                self.assertEqual(bearing_label(origin, target), expected)
        self.assertEqual(len(BEARINGS), 16)
        self.assertEqual(len(set(BEARINGS)), 16)

    def test_a_half_sector_tie_goes_clockwise(self):
        # 11.25, 33.75 ... are the sector edges; a tie rounds to the sector that
        # starts there, which is the clockwise neighbour.
        self.assertEqual(BEARINGS[bearing_index(0)], "北")
        self.assertEqual(BEARINGS[bearing_index(11.25)], "北北東")
        self.assertEqual(BEARINGS[bearing_index(33.75)], "東北")
        self.assertEqual(BEARINGS[bearing_index(348.75)], "北")
        # Just below an edge stays in the counter-clockwise sector.
        self.assertEqual(BEARINGS[bearing_index(11.24)], "北")
        self.assertEqual(BEARINGS[bearing_index(348.7)], "北北西")
        # Just above the same edge has already crossed clockwise into north.
        self.assertEqual(BEARINGS[bearing_index(348.8)], "北")
        # Exactly north, east, south and west are sector centres, not edges.
        self.assertEqual(BEARINGS[bearing_index(90)], "東")
        self.assertEqual(BEARINGS[bearing_index(180)], "南")
        self.assertEqual(BEARINGS[bearing_index(270)], "西")
        # The angular sector math stays consistent with the integer cells.
        self.assertEqual(bearing_label((0, 0), (5, 5)), "東北")
        self.assertEqual(bearing_label((0, 0), (5, 12)), "北北東")

    def test_distances_round_to_the_nearest_five_with_ties_upward(self):
        cases = {0: 0, 2.4: 0, 2.5: 5, 4.9: 5, 7.5: 10, 12.4: 10, 12.5: 15}
        for distance, expected in cases.items():
            with self.subTest(distance=distance):
                self.assertEqual(rounded_distance_km(distance), expected)


def _marker_source(**overrides):
    fields = {
        "source_key": "landmark:t_watchtower",
        "cell": (40, 0),
        "sight_km": 10.0,
        "light_km": 0.0,
        "silhouette_day": "合成白日側影",
        "silhouette_night": "合成夜間側影",
        "district_key": "t_district",
        "authored": True,
    }
    fields.update(overrides)
    return SightSource(**fields)


def _markers(policy, sources, *, observer=(0, 0), hour=12, terrain="meadow", lit=(), names=None):
    return distant_markers(
        observer,
        _hour(hour),
        sources,
        lit,
        inputs=GroundSightInputs(terrain, 0, False),
        cell_size_km=1.0,
        district_names={} if names is None else names,
        policy=policy,
    )


class DistantMarkerTests(unittest.TestCase):
    """Visibility by phase and range, canopy, privacy and merging."""

    def test_visibility_follows_the_phase_and_the_authored_range(self):
        policy = _synthetic_policy()
        source = _marker_source(cell=(14, 0), sight_km=10.0, light_km=0.0)
        # Day: 14 km away is inside a 10 km range? No -- outside.
        self.assertEqual(_markers(policy, [source], hour=12), ())
        inside = _marker_source(cell=(10, 0))
        self.assertEqual(len(_markers(policy, [inside], hour=12)), 1)
        # Twilight: the daytime range is scaled by 0.5, so 10 km is out.
        self.assertEqual(_markers(policy, [inside], hour=17), ())
        # Night: only the light range counts, and this source has none.
        self.assertEqual(_markers(policy, [inside], hour=21), ())
        lighting = _marker_source(cell=(3, 0), sight_km=0.0, light_km=4.0)
        self.assertEqual(_markers(policy, [lighting], hour=21)[0]["silhouette_zh"], "合成夜間側影")
        self.assertEqual(_markers(policy, [lighting], hour=12), ())

    def test_a_source_inside_live_sight_or_under_a_canopy_never_marks(self):
        policy = _synthetic_policy()
        # meadow day radius 2 + tier 0: a cell 2 cells away is inside, 3 outside.
        inside = _marker_source(cell=(2, 0), sight_km=10.0)
        outside = _marker_source(cell=(3, 0), sight_km=10.0)
        self.assertEqual(_markers(policy, [inside], hour=12), ())
        self.assertEqual(len(_markers(policy, [outside], hour=12)), 1)
        self.assertEqual(_markers(policy, [outside], hour=12, terrain="canopy"), ())

    def test_a_hidden_place_is_never_a_source_in_any_phase(self):
        policy = _synthetic_policy()
        for kind in sorted(HIDDEN_ANCHOR_KINDS):
            placement = SettlementFootprint(
                anchor_key="t_concealed", kind=kind, cell=(9, 0), occupied_cells=64
            )
            with self.subTest(kind=kind):
                self.assertEqual(settlement_sources([placement], policy=policy), ())
        hidden_landmark = LandmarkSighting(
            source_key="landmark:t_glade",
            cell=(9, 0),
            district_key="t_glade_district",
            sight_km=10.0,
            light_km=5.0,
            silhouette_zh="合成林地側影",
            hidden=True,
        )
        self.assertEqual(landmark_sources([hidden_landmark]), ())
        for hour in (12, 17, 21):
            with self.subTest(hour=hour):
                self.assertEqual(_markers(policy, landmark_sources([hidden_landmark]), hour=hour), ())

    def test_a_landmark_without_an_authored_range_produces_no_marker(self):
        policy = _synthetic_policy()
        silent = LandmarkSighting(
            source_key="landmark:t_stone",
            cell=(9, 0),
            district_key="t_stone_district",
            sight_km=0.0,
            light_km=0.0,
            silhouette_zh="合成石碑側影",
        )
        self.assertEqual(landmark_sources([silent]), ())
        self.assertEqual(_markers(policy, landmark_sources([silent])), ())
        # A range without an authored silhouette is an authoring error, never a
        # marker with an empty description.
        anonymous = LandmarkSighting(
            source_key="landmark:t_silent",
            cell=(9, 0),
            district_key="t_silent_district",
            sight_km=12.0,
            light_km=0.0,
            silhouette_zh="  ",
        )
        with self.assertRaises(SightRulebookError):
            landmark_sources([anonymous])

    def test_duplicate_sources_merge_without_losing_a_night_light(self):
        policy = _synthetic_policy()
        authored = _marker_source(cell=(8, 0), sight_km=30.0, light_km=0.0)
        settlement = _marker_source(
            source_key="settlement:t_town",
            cell=(8, 0),
            sight_km=6.0,
            light_km=9.0,
            silhouette_day="合成聚落白日",
            silhouette_night="合成聚落燈火",
            district_key=None,
            authored=False,
        )
        merged = merge_sources([settlement, authored])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].sight_km, 30.0)
        # The authored day-only record must not erase the automatic night light.
        self.assertEqual(merged[0].light_km, 9.0)
        # Day and twilight carry one marker; the night column still marks it.
        self.assertEqual(len(_markers(policy, merged, hour=12)), 1)
        self.assertEqual(len(_markers(policy, merged, hour=21)), 1)

    def test_a_merged_unlit_place_keeps_the_anonymous_kind_silhouette(self):
        policy = _synthetic_policy()
        authored = _marker_source(
            cell=(8, 0),
            sight_km=30.0,
            light_km=6.0,
            silhouette_day="合成被動地標白日",
            silhouette_night="合成被動地標夜色",
        )
        settlement = _marker_source(
            source_key="settlement:t_town",
            cell=(8, 0),
            sight_km=6.0,
            light_km=9.0,
            silhouette_day="合成聚落白日",
            silhouette_night="合成聚落燈火",
            district_key=None,
            authored=False,
        )
        merged = merge_sources([authored, settlement])
        self.assertEqual(len(merged), 1)
        # The place is a settlement, so its validated kind/phase anonymity wins
        # even though an authored landmark description exists for the same cell.
        self.assertEqual(merged[0].silhouette_day, "合成聚落白日")
        self.assertEqual(merged[0].silhouette_night, "合成聚落燈火")
        marker = _markers(policy, merged, hour=12, names={"t_district": "合成燈塔"})[0]
        self.assertEqual(marker["silhouette_zh"], "合成聚落白日")
        self.assertIsNone(marker["name"])
        # Lighting its district only adds the permitted name.
        lit = _markers(
            policy, merged, hour=12, lit=("t_district",), names={"t_district": "合成燈塔"}
        )[0]
        self.assertEqual(lit["silhouette_zh"], "合成聚落白日")
        self.assertEqual(lit["name"], "合成燈塔")

    def test_merge_order_never_decides_conflicting_metadata(self):
        policy = _synthetic_policy()
        east = _marker_source(cell=(8, 0), district_key="t_east", sight_km=20.0)
        west = _marker_source(
            cell=(8, 0), source_key="landmark:t_west", district_key="t_west", sight_km=20.0
        )
        forward = merge_sources([east, west])
        backward = merge_sources([west, east])
        self.assertEqual(forward, backward)
        self.assertEqual(forward[0].district_key, "t_east")
        self.assertEqual(
            _markers(policy, forward, hour=12), _markers(policy, backward, hour=12)
        )

    def test_only_a_lit_district_adds_the_name_and_nothing_else_changes(self):
        policy = _synthetic_policy()
        source = _marker_source(cell=(10, 0))
        names = {"t_district": "合成燈塔"}
        unlit = _markers(policy, [source], hour=12, names=names)
        lit = _markers(policy, [source], hour=12, lit=("t_district",), names=names)
        self.assertEqual(len(unlit), len(lit))
        self.assertIsNone(unlit[0]["name"])
        self.assertEqual(lit[0]["name"], "合成燈塔")
        self.assertEqual(
            {key: value for key, value in lit[0].items() if key != "name"},
            {key: value for key, value in unlit[0].items() if key != "name"},
        )

    def test_unlit_settlement_uses_kind_silhouette_not_identity(self):
        policy = _synthetic_policy()
        # The identifying text a location carries: its anchor identity. None of
        # it may reach the marker of an unlit settlement.
        sentinel_key = "t_village_that_must_not_be_named"
        placement = SettlementFootprint(
            anchor_key=sentinel_key, kind="capital", cell=(6, 0), occupied_cells=4
        )
        markers = _markers(
            policy, settlement_sources([placement], policy=policy), hour=12
        )
        self.assertEqual(len(markers), 1)
        marker = markers[0]
        self.assertEqual(set(marker), set(MARKER_KEYS))
        self.assertEqual(marker["silhouette_zh"], "合成城牆側影")
        self.assertIsNone(marker["name"])
        rendered = repr(markers)
        self.assertNotIn(sentinel_key, rendered)
        self.assertNotIn("capital", rendered)

    def test_the_wire_marker_carries_no_source_cell_identity_or_district_key(self):
        policy = _synthetic_policy()
        source = _marker_source(cell=(10, 0))
        marker = _markers(policy, [source], hour=12, lit=("t_district",), names={"t_district": "合成燈塔"})[0]
        self.assertEqual(set(marker), set(MARKER_KEYS))
        self.assertEqual(marker["bearing"], "東")
        self.assertEqual(marker["distance_km"], 10)
        rendered = repr(marker)
        for value in source.source_key, source.district_key, source.cell:
            with self.subTest(value=value):
                self.assertNotIn(str(value), rendered)

    def test_markers_are_recomputed_and_never_write_or_light_anything(self):
        policy = _synthetic_policy()
        sources = (_marker_source(cell=(10, 0)), _marker_source(cell=(-10, 0), source_key="landmark:t_west"))
        lit = frozenset()
        calendar = _hour(12)
        first = _markers(policy, sources, hour=12, lit=lit)
        second = _markers(policy, sources, hour=12, lit=lit)
        self.assertEqual(first, second)
        self.assertEqual(lit, frozenset())
        self.assertEqual(vars(calendar), {"hour": 12})
        # The source records themselves are frozen, so a read cannot mutate one.
        with self.assertRaises(dataclasses.FrozenInstanceError):
            sources[0].sight_km = 1.0
        # A different hour is a different projection of the same immutable input.
        self.assertNotEqual(_markers(policy, sources, hour=21, lit=lit), first)


class PublishedCompositionTests(unittest.TestCase):
    """The pure composition the published seams delegate to."""

    def test_placements_skip_incomplete_views_and_stay_ordered(self):
        placements = settlement_placements(
            {"t_town": "capital", "t_glade": "elven_village"},
            {"t_town": (4, 4), "t_glade": (6, 6), "t_cave": (9, 9)},
            {"t_town": 4, "t_glade": 9, "t_cave": 1, "t_absent": 7},
        )
        # No kind (t_cave) or no cell (t_absent) means no placement at all.
        self.assertEqual([row.anchor_key for row in placements], ["t_glade", "t_town"])
        self.assertEqual([row.cell for row in placements], [(6, 6), (4, 4)])

    def test_distant_sources_filter_hidden_and_zero_range_and_merge_a_settlement(self):
        policy = _synthetic_policy()
        rows = [
            # A hidden place with a range is still not a source.
            LandmarkSighting(
                source_key="landmark:t_glade",
                cell=(6, 6),
                district_key="t_glade_district",
                sight_km=40.0,
                light_km=10.0,
                silhouette_zh="合成林地側影",
                hidden=True,
            ),
            # No authored range means no marker.
            LandmarkSighting(
                source_key="landmark:t_stone",
                cell=(12, 0),
                district_key="t_stone_district",
                sight_km=0.0,
                light_km=0.0,
                silhouette_zh="合成石碑側影",
            ),
            # A landmark that references the settlement at the same place.
            LandmarkSighting(
                source_key="settlement:t_town",
                cell=(4, 4),
                district_key="t_town_district",
                sight_km=25.0,
                light_km=0.0,
                silhouette_zh="合成被動地標白日",
            ),
        ]
        placements = settlement_placements(
            {"t_town": "capital", "t_glade": "elven_village"},
            {"t_town": (4, 4), "t_glade": (6, 6)},
            {"t_town": 4, "t_glade": 9},
        )
        sources = distant_sources(rows, placements, policy=policy)
        # One merged settlement source: the hidden and rangeless rows are gone,
        # and the elven village contributes no automatic source either.
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].cell, (4, 4))
        self.assertEqual(sources[0].sight_km, 25.0)
        # The automatic settlement contributed its light range and anonymity.
        self.assertEqual(sources[0].light_km, 2 * 1.0)
        self.assertEqual(sources[0].silhouette_day, "合成城牆側影")

    def test_the_sources_a_marker_read_needs_are_immutable(self):
        sources = distant_sources([], [])
        self.assertEqual(sources, ())


class PublishedSeamTests(unittest.TestCase):
    """The published seams over synthetic registries (no game world, no DB)."""

    @staticmethod
    def _published(*, landmarks=(), districts=True):
        """Patch the published registry readers with synthetic views."""

        from contextlib import ExitStack
        from unittest.mock import patch

        from world.lore import anchors as anchors_module
        from world.lore import map_districts as districts_module
        from world.lore import wilderness_entry as entry_module
        from world.maps import static_references

        registry = {
            "t_town": SimpleNamespace(kind=AnchorKind.CAPITAL),
            "t_glade": SimpleNamespace(kind=AnchorKind.ELVEN_VILLAGE),
        }
        geography = {
            "t_town": SimpleNamespace(cell=(4, 4)),
            "t_glade": SimpleNamespace(cell=(6, 6)),
        }
        entries = {
            "t_town": SimpleNamespace(hash_cell_count=4),
            "t_glade": SimpleNamespace(hash_cell_count=9),
        }
        district_registry = {
            row.district_key: row
            for row in (
                SimpleNamespace(
                    district_id="t_ridge",
                    district_key="t_ridge",
                    vantage=True,
                    sight_km=22.0,
                    light_km=4.0,
                    silhouette_zh="合成山脊側影",
                    landmark=SimpleNamespace(
                        domain="wilderness_cell", object_id="ridge", map_id=None
                    ),
                ),
                SimpleNamespace(
                    district_id="t_glade",
                    district_key="t_glade",
                    vantage=False,
                    sight_km=30.0,
                    light_km=0.0,
                    silhouette_zh="合成林地側影",
                    landmark=SimpleNamespace(domain="location", object_id="t_glade", map_id=None),
                ),
                SimpleNamespace(
                    district_id="t_stone",
                    district_key="t_stone",
                    vantage=False,
                    sight_km=0.0,
                    light_km=0.0,
                    silhouette_zh="合成石碑側影",
                    landmark=SimpleNamespace(
                        domain="wilderness_cell", object_id="stone", map_id=None
                    ),
                ),
                SimpleNamespace(
                    district_id="t_town_spire",
                    district_key="t_town_spire",
                    vantage=False,
                    sight_km=20.0,
                    light_km=1.0,
                    silhouette_zh="合成城塔側影",
                    landmark=SimpleNamespace(
                        domain="wilderness_cell", object_id="spire", map_id=None
                    ),
                ),
            )
        }
        cells = {
            "ridge": (9, 0),
            "stone": (12, 0),
            "spire": (4, 4),
            "t_glade": (6, 6),
        }

        def fake_resolve(reference, *, index=None, source=""):
            return SimpleNamespace(cell=cells[reference.object_id], position_m=None)

        stack = ExitStack()
        stack.enter_context(patch.object(anchors_module, "anchors", lambda: registry))
        stack.enter_context(patch.object(anchors_module, "anchor_geography", lambda: geography))
        stack.enter_context(patch.object(entry_module, "WILDERNESS_ENTRY_REGISTRY", entries))
        stack.enter_context(patch.object(static_references, "map_reference_index", lambda: object()))
        stack.enter_context(patch.object(static_references, "resolve_static", fake_resolve))
        if districts:
            stack.enter_context(
                patch.object(
                    districts_module,
                    "current",
                    lambda: SimpleNamespace(districts=district_registry),
                )
            )
        return stack

    def test_the_published_automatic_sources_come_from_the_live_registries(self):
        from world.rules import sight

        with self._published():
            sources = sight.published_settlement_sources()
        # The hidden elven village is never a source; the capital is, with its
        # footprint-derived visibility and the policy silhouette.
        self.assertEqual([source.source_key for source in sources], ["settlement:t_town"])
        self.assertEqual(sources[0].cell, (4, 4))
        factor = sight.POLICY.settlement_footprint_factor
        # Four occupied cells -> a footprint size of two cells.
        self.assertEqual(sources[0].sight_km, 2 * factor["day"])
        self.assertEqual(sources[0].light_km, 2 * factor["night"])
        self.assertEqual(
            sources[0].silhouette_day, sight.POLICY.settlement_silhouettes["capital"]["day"]
        )

    def test_the_published_composition_filters_and_merges_district_landmarks(self):
        from world.rules import sight

        with self._published():
            sources = sight.published_distant_sources()
        by_cell = {source.cell: source for source in sources}
        # The hidden place's ranged landmark is dropped entirely, and the
        # rangeless stone landmark emits no marker either.
        self.assertEqual(set(by_cell), {(9, 0), (4, 4)})
        self.assertEqual(by_cell[(9, 0)].sight_km, 22.0)
        # The settlement cell carries both the automatic source and the
        # landmark that stands on it, merged once: ranges widen, and the
        # validated settlement anonymity survives the merge.
        merged = by_cell[(4, 4)]
        self.assertEqual(merged.sight_km, 20.0)
        # The automatic night light is larger than the landmark's own range.
        self.assertEqual(
            merged.light_km, max(1.0, 2 * sight.POLICY.settlement_footprint_factor["night"])
        )
        # The merged record keeps the settlement anonymity, not the authored
        # landmark description, because the place is a settlement.
        self.assertEqual(
            merged.silhouette_day, sight.POLICY.settlement_silhouettes["capital"]["day"]
        )

    def test_a_vantage_flag_projects_the_landmark_cell_it_names(self):
        from world.rules import sight

        with self._published():
            self.assertEqual(sight.published_vantage_cells(), frozenset({(9, 0)}))


class PolicyValidationTests(unittest.TestCase):
    """Closed, fail-closed policy validation."""

    def test_a_complete_synthetic_policy_loads(self):
        policy = _synthetic_policy()
        self.assertEqual(policy.twilight_factor, 0.5)
        self.assertEqual(policy.region_terrain["t_canopy_region"], "canopy")

    def test_two_phases_cannot_start_at_the_same_hour(self):
        document = _document()
        document["phases"] = [
            {"name": "day", "start_hour": 8, "column": "day"},
            {"name": "dusk", "start_hour": 8, "column": "twilight"},
            {"name": "night", "start_hour": 20, "column": "night"},
        ]
        self.assertIn("duplicate phase start hours", _rejected(self, document))
        duplicate_name = _document()
        duplicate_name["phases"] = [
            {"name": "day", "start_hour": 8, "column": "day"},
            {"name": "day", "start_hour": 16, "column": "twilight"},
        ]
        self.assertIn("duplicate phase names", _rejected(self, duplicate_name))

    def test_declaration_order_never_decides_a_phase(self):
        document = _document()
        document["phases"] = list(reversed(document["phases"]))
        reordered = _synthetic_policy(phases=document["phases"])
        baseline = _synthetic_policy()
        for hour in range(24):
            with self.subTest(hour=hour):
                self.assertEqual(
                    reordered.phase_for_hour(hour), baseline.phase_for_hour(hour)
                )

    def test_malformed_phases_are_rejected(self):
        cases = {
            "unknown column": {"column": "midnight"},
            "out of range hour": {"start_hour": 25},
            "missing name": {"name": ""},
        }
        for label, patch in cases.items():
            document = _document()
            document["phases"] = [dict(entry) for entry in document["phases"]]
            document["phases"][0].update(patch)
            with self.subTest(label=label):
                self.assertIn("sight rulebook", _rejected(self, document))
        extra = _document()
        extra["phases"] = [dict(entry, extra=1) for entry in extra["phases"]]
        self.assertIn("each phase declares exactly", _rejected(self, extra))

    def test_an_incomplete_radius_table_is_rejected(self):
        document = _document()
        document["terrain_radius"] = {
            "meadow": {"day": 2, "twilight": 1},
            "ridge": {"day": 3, "twilight": 2, "night": 1},
            "canopy": {"day": 1, "twilight": 1, "night": 0},
        }
        self.assertIn("exactly ['day', 'twilight', 'night']", _rejected(self, document))

    def test_an_impossible_reachable_radius_is_rejected(self):
        # Every single value is legal, but ridge day 5 + tier 3 bonus 5 = 10.
        document = _document()
        document["terrain_radius"]["ridge"] = {"day": 5, "twilight": 2, "night": 1}
        document["prominence_bonus"] = [
            {"day": 0, "twilight": 0, "night": 0},
            {"day": 1, "twilight": 0, "night": 0},
            {"day": 2, "twilight": 1, "night": 0},
            {"day": 5, "twilight": 2, "night": 0},
        ]
        self.assertIn("above the maximum 8", _rejected(self, document))

    def test_a_single_radius_above_the_maximum_is_rejected(self):
        document = _document()
        document["vantage_radius"] = {"day": 9, "twilight": 4, "night": 2}
        self.assertIn("inside 0..8", _rejected(self, document))

    def test_non_finite_and_negative_factors_are_rejected(self):
        for label, value in (("negative", -0.5), ("string", "0.5"), ("bool", True)):
            document = _document(twilight_factor=value)
            with self.subTest(label=label):
                self.assertIn("twilight_factor", _rejected(self, document))
        infinite = _document()
        infinite["twilight_factor"] = float("inf")
        self.assertIn("twilight_factor", _rejected(self, infinite))
        # An integer beyond the float range is a rulebook error, not a crash.
        huge = _document()
        huge["twilight_factor"] = 10**400
        self.assertIn("twilight_factor", _rejected(self, huge))
        footprint = _document()
        footprint["settlement_footprint_factor"] = {"day": -1, "night": 1}
        self.assertIn("settlement_footprint_factor.day", _rejected(self, footprint))

    def test_an_unknown_terrain_row_or_region_target_is_rejected(self):
        document = _document()
        document["region_terrain"]["t_meadow_region"] = "t_absent_row"
        self.assertIn("unknown terrain row", _rejected(self, document))
        document = _document()
        document["canopy_terrain"] = ["t_absent_row"]
        self.assertIn("canopy rows without a terrain table", _rejected(self, document))

    def test_missing_blank_and_over_bound_silhouettes_are_rejected(self):
        missing = _document()
        missing["settlement_silhouettes"] = {}
        self.assertIn("must cover exactly", _rejected(self, missing))
        for label, value in (
            ("blank", "   "),
            ("over bound", "字" * (SILHOUETTE_MAX_CODE_POINTS + 1)),
            ("not text", 1),
        ):
            document = _document()
            document["settlement_silhouettes"]["capital"]["night"] = value
            with self.subTest(label=label):
                self.assertIn("settlement_silhouettes.capital.night", _rejected(self, document))

    def test_the_region_coverage_join_rejects_a_missing_row(self):
        policy = _synthetic_policy()
        validate_sight_region_coverage(policy.region_terrain, policy=policy)
        with self.assertRaises(SightRulebookError) as caught:
            validate_sight_region_coverage(
                (*policy.region_terrain, "t_absent_region"), policy=policy
            )
        self.assertIn("t_absent_region", str(caught.exception))

    def test_an_unknown_region_key_raises_instead_of_defaulting(self):
        policy = _synthetic_policy()
        with self.assertRaises(SightRulebookError):
            policy.terrain_for_region("t_absent_region")


class CopyIsolationTests(unittest.TestCase):
    """A policy is immutable, so one read can never move another's numbers."""

    def test_the_shipped_policy_tables_cannot_be_mutated_through_a_read(self):
        from world.rules.sight import POLICY

        snapshot = {key: dict(row) for key, row in POLICY.terrain_radius.items()}
        with self.assertRaises(TypeError):
            POLICY.terrain_radius["open_ground"] = {}  # type: ignore[index]
        self.assertEqual({key: dict(row) for key, row in POLICY.terrain_radius.items()}, snapshot)


if __name__ == "__main__":
    unittest.main()
