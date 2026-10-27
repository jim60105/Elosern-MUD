"""Mechanism tests for the deterministic terrain rules and snapshot isolation."""

from __future__ import annotations

import pytest

from elosern_map_core.geometry import is_on_mainland
from elosern_map_core.terrain import (
    REGION_KEYS,
    TerrainDefinition,
    border_river_row,
    forest_edge_row,
    is_closed_ridge_cell,
    is_inland_water_cell,
    is_land_cell,
    is_passable_terrain,
    is_valid_wilderness_cell,
    is_walkable_cell,
    nominal_nation_for_coordinates,
    rasterize_routes,
    rasterize_segment,
    region_for_coordinates,
    ridge_center_x,
    ridge_span,
    route_row_at,
    terrain_description,
)

FLAVOR_X = 92821
FLAVOR_Y = 68917


def _flavors(prefix: str) -> dict[str, tuple[str, ...]]:
    return {key: (f"{prefix}-{key}-0", f"{prefix}-{key}-1", f"{prefix}-{key}-2") for key in REGION_KEYS}


def _world_a(**overrides) -> TerrainDefinition:
    inputs = dict(
        frame_cells=40,
        mainland_boundary_km=((0, 0), (40, 0), (40, 40), (0, 40)),
        forest_edge=((0, 30), (39, 30)),
        waterway_routes={"border_river": ((20, 20), (0, 20))},
        waterway_fords={"border_river": ((10, 20),)},
        border_river_key="border_river",
        ridge_base_x=10,
        ridge_period=5,
        ridge_step=1,
        ridge_min_x=0,
        ridge_max_x=39,
        ridge_north_limit=35,
        ridge_passes=((4, 5),),
        coastal_y_max=10,
        mountain_corridor_half_width=2,
        region_flavors=_flavors("a"),
    )
    inputs.update(overrides)
    return TerrainDefinition(**inputs)


def _world_b(**overrides) -> TerrainDefinition:
    inputs = dict(
        frame_cells=60,
        mainland_boundary_km=((0, 0), (60, 0), (60, 60), (0, 60)),
        forest_edge=((0, 25), (59, 25)),
        waterway_routes={"border_river": ((30, 15), (0, 15))},
        waterway_fords={},
        border_river_key="border_river",
        ridge_base_x=20,
        ridge_period=4,
        ridge_step=2,
        ridge_min_x=0,
        ridge_max_x=59,
        ridge_north_limit=50,
        ridge_passes=((3, 4),),
        coastal_y_max=5,
        mountain_corridor_half_width=1,
        region_flavors=_flavors("b"),
    )
    inputs.update(overrides)
    return TerrainDefinition(**inputs)


class TestSnapshotIsolation:
    def test_each_definition_classifies_from_its_own_inputs(self):
        world_a, world_b = _world_a(), _world_b()
        first = region_for_coordinates(world_a, 15, 12)
        assert first == "eastern_plains"
        assert region_for_coordinates(world_b, 15, 12) == "western_hills_valleys"
        # Returning to world A yields the same answer: world B's tables were
        # never installed over A's.
        assert region_for_coordinates(world_a, 15, 12) == first

    def test_column_tables_and_borders_belong_to_their_definition(self):
        world_a, world_b = _world_a(), _world_b()
        assert forest_edge_row(world_a, 50) == 30  # clamped to A's last column
        assert forest_edge_row(world_b, 50) == 25
        assert border_river_row(world_a, 25) == 20
        assert border_river_row(world_b, 25) == 15

        borders_a = world_a.national_borders
        assert world_a.national_borders is borders_a  # cached on the instance
        borders_b = world_b.national_borders
        assert borders_b is not borders_a
        assert world_a.national_borders == borders_a
        # The Altoria | Valhalla line follows each world's own river row.
        assert {point[1] for point in borders_a[0].points} == {20}
        assert {point[1] for point in borders_b[0].points} == {15}

    def test_flavour_selection_uses_only_the_current_definition(self):
        world_a, world_b = _world_a(), _world_b()
        text_a = terrain_description(world_a, 15, 12)
        text_b = terrain_description(world_b, 15, 12)
        region_a = region_for_coordinates(world_a, 15, 12)
        region_b = region_for_coordinates(world_b, 15, 12)
        assert text_a == world_a.region_flavors[region_a][(15 * FLAVOR_X + 12 * FLAVOR_Y) % 3]
        assert text_b == world_b.region_flavors[region_b][(15 * FLAVOR_X + 12 * FLAVOR_Y) % 3]
        assert text_a.startswith("a-")
        assert text_b.startswith("b-")
        assert terrain_description(world_a, 15, 12) == text_a

    def test_inputs_are_copied_so_later_mutation_cannot_change_results(self):
        routes = {"border_river": ((20, 20), (0, 20))}
        fords = {"border_river": ((10, 20),)}
        flavors = dict(_flavors("a"))
        passes = [[4, 5]]
        world = _world_a(
            waterway_routes=routes,
            waterway_fords=fords,
            region_flavors=flavors,
            ridge_passes=passes,
        )
        before_region = region_for_coordinates(world, 15, 12)
        before_water = is_inland_water_cell(world, (15, 20))
        before_text = terrain_description(world, 15, 12)
        before_ridge = is_closed_ridge_cell(world, (8, 0))
        before_borders = world.national_borders

        routes["border_river"] = ((5, 5), (0, 5))
        fords["border_river"] = ()
        flavors["eastern_plains"] = ("mutated",)
        # A list window must not stay reachable: widening it here would have
        # opened the ridge wall at row 0.
        passes[0][0] = 0

        assert region_for_coordinates(world, 15, 12) == before_region
        assert is_inland_water_cell(world, (15, 20)) == before_water
        assert terrain_description(world, 15, 12) == before_text
        assert is_closed_ridge_cell(world, (8, 0)) == before_ridge
        assert before_ridge is True
        assert world.national_borders == before_borders

    def test_same_sized_worlds_keep_separate_tables(self):
        # Equal frame sizes remove the accidental protection that different
        # table lengths would give; only per-instance ownership can pass this.
        world_a = _world_a()
        world_a.national_borders  # force every A cache
        world_b = _world_a(
            forest_edge=((0, 20), (39, 20)),
            waterway_routes={"border_river": ((30, 26), (0, 26))},
            waterway_fords={},
            coastal_y_max=6,
            region_flavors=_flavors("b"),
        )

        assert region_for_coordinates(world_a, 15, 12) == "eastern_plains"
        assert region_for_coordinates(world_b, 15, 12) == "eastern_plains"
        assert region_for_coordinates(world_a, 15, 25) == "eastern_plains"
        assert region_for_coordinates(world_b, 15, 25) == "north_deep_forest"
        assert forest_edge_row(world_a, 5) == 30
        assert forest_edge_row(world_b, 5) == 20
        assert border_river_row(world_a, 5) == 20
        assert border_river_row(world_b, 5) == 26
        assert terrain_description(world_a, 15, 12).startswith("a-")
        assert terrain_description(world_b, 15, 12).startswith("b-")


class TestClassification:
    def test_forest_edge_wins_before_the_mountain_corridor(self):
        world = _world_a()
        assert region_for_coordinates(world, 10, 30) == "north_deep_forest"
        assert region_for_coordinates(world, 10, 29) == "central_mountains"

    def test_the_corridor_follows_the_bending_ridge_centre(self):
        world = _world_a()
        assert ridge_center_x(world, 0) == 8
        assert ridge_center_x(world, 10) == 10
        assert ridge_center_x(world, 20) == 12
        assert region_for_coordinates(world, 8, 0) == "central_mountains"
        assert region_for_coordinates(world, 8 + 3, 0) == "southeast_coast"
        # The corridor moved north with the ridge: x 11 is inside it at y 15.
        assert region_for_coordinates(world, 8 + 3, 15) == "central_mountains"
        assert region_for_coordinates(world, 15, 15) == "eastern_plains"

    def test_east_west_split_and_coastal_band(self):
        world = _world_a()
        assert region_for_coordinates(world, 20, 5) == "southeast_coast"
        assert region_for_coordinates(world, 20, 15) == "eastern_plains"
        assert region_for_coordinates(world, 3, 5) == "southwest_coast"
        assert region_for_coordinates(world, 3, 15) == "western_hills_valleys"
        assert region_for_coordinates(world, 3, 25) == "northwest_highland_forest"

    def test_nominal_claims_follow_the_ridge_and_the_river(self):
        world = _world_a()
        assert nominal_nation_for_coordinates(world, 20, 12) == "grandia"
        assert nominal_nation_for_coordinates(world, 3, 20) == "altoria"
        assert nominal_nation_for_coordinates(world, 3, 21) == "valhalla"

    def test_every_classification_is_one_of_the_registered_regions(self):
        world = _world_b()
        seen = {
            region_for_coordinates(world, x, y)
            for x in range(0, world.frame_cells, 7)
            for y in range(0, world.frame_cells, 7)
        }
        assert seen <= REGION_KEYS
        assert len(seen) == len(REGION_KEYS)


class TestTerrainFeatures:
    def test_ridge_wall_keeps_its_diagonal_continuity_and_pass_windows(self):
        world = _world_a()
        assert ridge_span(world, 4) == (8, 9)
        assert ridge_span(world, 9) == (9, 10)
        assert is_closed_ridge_cell(world, (8, 0))
        # The row's span reaches the next row's centre, so the wall never
        # leaves a diagonal gap.
        assert is_closed_ridge_cell(world, (10, 9))
        assert not is_closed_ridge_cell(world, (8, 4))  # authored pass window
        assert not is_closed_ridge_cell(world, (8, 35))  # northern limit
        assert not is_closed_ridge_cell(world, (30, 0))  # outside the ridge span

    def test_waterways_are_impassable_except_at_declared_fords(self):
        world = _world_a()
        assert is_inland_water_cell(world, (15, 20))
        assert not is_inland_water_cell(world, (10, 20))  # ford
        assert is_passable_terrain(world, (10, 20))
        assert not is_passable_terrain(world, (15, 20))
        assert world.waterway_cells == rasterize_routes(world.waterway_routes) - {(10, 20)}

    def test_land_test_samples_the_cell_centre(self):
        world = _world_a()
        assert is_land_cell(world, (20, 20))
        assert not is_land_cell(world, (45, 20))
        # A sloped shore distinguishes the centre sample from the cell corner:
        # the corner (2, 2) is land, the centre (2.5, 2.5) is sea.
        sloped = _world_a(
            mainland_boundary_km=((0, 0), (4, 0), (4, 1), (0, 4)),
        )
        assert is_on_mainland(sloped.mainland_boundary_km, 2, 2)
        assert not is_land_cell(sloped, (2, 2))
        assert is_land_cell(sloped, (0, 0))

    def test_walkability_combines_frame_land_and_terrain(self):
        world = _world_a()
        assert is_walkable_cell(world, (5, 25))
        assert not is_walkable_cell(world, (40, 25))  # out of frame
        assert not is_walkable_cell(world, (15, 20))  # water
        assert not is_walkable_cell(world, (8, 0))  # ridge wall

    def test_validity_also_excludes_caller_supplied_footprint_cells(self):
        world = _world_a()
        footprints = frozenset({(5, 25)})
        assert not is_valid_wilderness_cell(world, footprints, (5, 25))
        assert is_valid_wilderness_cell(world, footprints, (6, 25))

    def test_region_search_boxes_cover_every_region(self):
        for world in (_world_a(), _world_b()):
            boxes = world.region_search_boxes
            assert set(boxes) == REGION_KEYS
            # Every classified cell of the frame lies inside its region's box,
            # so a sparse-index consumer can never miss valid terrain.
            for x in range(world.frame_cells):
                for y in range(world.frame_cells):
                    key = region_for_coordinates(world, x, y)
                    x_min, x_max, y_min, y_max = boxes[key]
                    assert x_min <= x <= x_max and y_min <= y <= y_max, (key, x, y)
            for key, (x_min, x_max, y_min, y_max) in boxes.items():
                assert any(
                    region_for_coordinates(world, x, y) == key
                    for x in range(x_min, x_max + 1)
                    for y in range(y_min, y_max + 1)
                ), key

    def test_national_borders_are_derived_from_the_river_and_the_ridge(self):
        world = _world_a()
        borders = {border.nation_keys: border.points for border in world.national_borders}
        assert set(borders) == {
            ("altoria", "valhalla"),
            ("altoria", "grandia"),
            ("grandia", "valhalla"),
        }
        river_line = borders[("altoria", "valhalla")]
        # The river reversed, then its source row east to the ridge centre.
        assert river_line[0] == (0, 20)
        assert river_line[-1] == (ridge_center_x(world, 20), 20)
        ridge_line = borders[("grandia", "valhalla")]
        assert {x for x, _ in ridge_line} <= {ridge_center_x(world, y) for _, y in ridge_line}


class TestRasterizer:
    def test_segment_rasterization_includes_both_endpoints(self):
        cells = rasterize_segment((0, 0), (3, 1))
        assert (0, 0) in cells
        assert (3, 1) in cells
        assert len(cells) == 4
        assert rasterize_segment((2, 2), (2, 2)) == {(2, 2)}

    def test_route_rows_follow_increasing_and_decreasing_shallow_routes(self):
        increasing = ((0, 0), (10, 5))
        decreasing = ((10, 5), (0, 0))
        assert route_row_at(increasing, 4) == 2
        assert route_row_at(decreasing, 4) == 2
        # Outside the span the nearest end row continues straight.
        assert route_row_at(increasing, 15) == 5
        assert route_row_at(increasing, -3) == 0

    def test_definition_validation_rejects_inconsistent_inputs(self):
        with pytest.raises(ValueError):
            _world_a(border_river_key="missing_river")
        with pytest.raises(ValueError):
            _world_a(forest_edge=((0, 30), (-1, 20)))
        with pytest.raises(ValueError):
            _world_a(waterway_routes={"border_river": ((0, 20), (20, 20))})
        with pytest.raises(ValueError):
            _world_a(region_flavors={"north_deep_forest": ("x",)})
        with pytest.raises(ValueError):
            _world_a(region_flavors={**_flavors("a"), "eastern_plains": ()})
        with pytest.raises(ValueError):
            _world_a(frame_cells=0)
        with pytest.raises(ValueError):
            _world_a(ridge_period=0)
        with pytest.raises(ValueError):
            _world_a(ridge_passes=((6, 5),))
        with pytest.raises(ValueError):
            _world_a(ridge_passes=((4, 5, 6),))
        with pytest.raises(ValueError):
            _world_a(mainland_boundary_km=((0, 0), (1, 1)))
        with pytest.raises(ValueError):
            _world_a(ridge_min_x=30, ridge_max_x=20)
