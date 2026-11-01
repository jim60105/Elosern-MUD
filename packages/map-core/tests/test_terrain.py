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
    ridge_crest_center_x,
    ridge_polyline,
    ridge_span,
    ridge_spans,
    route_row_at,
    terrain_description,
)

FLAVOR_X = 92821
FLAVOR_Y = 68917

#: One authored synthetic stem and its paired arms. The stem begins at row 0,
#: bends, and ends at the shared crotch (26, 30); the arms start at the crotch
#: and end north of it on opposite sides.
_STEM_A = ((28, 0), (26, 10), (24, 20), (26, 30))
_WEST_A = ((26, 30), (22, 34), (18, 38))
_EAST_A = ((26, 30), (30, 34), (34, 38))


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
        ridge_stem=_STEM_A,
        ridge_branches={"west": _WEST_A, "east": _EAST_A},
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
        ridge_stem=((44, 0), (42, 25), (44, 59)),
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
        first = region_for_coordinates(world_a, 15, 25)
        assert first == "northwest_highland_forest"
        assert region_for_coordinates(world_b, 15, 25) == "north_deep_forest"
        # Returning to world A yields the same answer: world B's tables were
        # never installed over A's.
        assert region_for_coordinates(world_a, 15, 25) == first

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
        stem = [[28, 0], [26, 10], [24, 20], [26, 30]]
        world = _world_a(
            waterway_routes=routes,
            waterway_fords=fords,
            region_flavors=flavors,
            ridge_passes=passes,
            ridge_stem=tuple(tuple(point) for point in stem),
        )
        before_region = region_for_coordinates(world, 15, 12)
        before_water = is_inland_water_cell(world, (15, 20))
        before_text = terrain_description(world, 15, 12)
        before_ridge = is_closed_ridge_cell(world, (28, 0))
        before_borders = world.national_borders

        routes["border_river"] = ((5, 5), (0, 5))
        fords["border_river"] = ()
        flavors["eastern_plains"] = ("mutated",)
        # A list window must not stay reachable: widening it here would have
        # opened the ridge wall at row 0.
        passes[0][0] = 0
        # A caller-supplied stem list must not stay reachable either.
        stem[0][0] = 0

        assert region_for_coordinates(world, 15, 12) == before_region
        assert is_inland_water_cell(world, (15, 20)) == before_water
        assert terrain_description(world, 15, 12) == before_text
        assert is_closed_ridge_cell(world, (28, 0)) == before_ridge
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
            ridge_stem=((34, 0), (32, 20), (36, 30)),
            ridge_branches={},
            region_flavors=_flavors("b"),
        )

        assert region_for_coordinates(world_a, 15, 25) == "northwest_highland_forest"
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
        assert region_for_coordinates(world, 26, 30) == "north_deep_forest"
        assert region_for_coordinates(world, 26, 29) == "central_mountains"

    def test_the_corridor_follows_the_authored_stem_centre(self):
        world = _world_a()
        assert ridge_center_x(world, 0) == 28
        assert ridge_center_x(world, 10) == 26
        assert ridge_center_x(world, 20) == 24
        assert ridge_center_x(world, 30) == 26
        # Outside the stem the nearest authored endpoint continues straight.
        assert ridge_center_x(world, 35) == 26

        assert region_for_coordinates(world, 28, 0) == "central_mountains"
        assert region_for_coordinates(world, 31, 0) == "southeast_coast"
        assert region_for_coordinates(world, 25, 15) == "central_mountains"
        assert region_for_coordinates(world, 31, 15) == "eastern_plains"

    def test_east_west_split_and_coastal_band(self):
        world = _world_a()
        assert region_for_coordinates(world, 31, 5) == "southeast_coast"
        assert region_for_coordinates(world, 31, 15) == "eastern_plains"
        assert region_for_coordinates(world, 3, 5) == "southwest_coast"
        assert region_for_coordinates(world, 3, 15) == "western_hills_valleys"
        assert region_for_coordinates(world, 3, 25) == "northwest_highland_forest"

    def test_nominal_claims_follow_the_stem_and_the_river(self):
        world = _world_a()
        assert nominal_nation_for_coordinates(world, 31, 12) == "grandia"
        assert nominal_nation_for_coordinates(world, 3, 20) == "altoria"
        assert nominal_nation_for_coordinates(world, 3, 21) == "valhalla"

    def test_branches_leave_regions_and_nominal_claims_unchanged(self):
        # Changing only the arms must not move a single region, search window
        # or nominal claim: arms are barriers, never corridors.
        stem_only = _world_a(ridge_branches={})
        with_arms = _world_a()
        assert stem_only.region_search_boxes == with_arms.region_search_boxes
        for x in range(40):
            for y in range(40):
                assert region_for_coordinates(stem_only, x, y) == region_for_coordinates(with_arms, x, y)
                assert nominal_nation_for_coordinates(stem_only, x, y) == nominal_nation_for_coordinates(with_arms, x, y)

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
        span = ridge_span(world, 9)
        assert span is not None
        low, high = span
        assert is_closed_ridge_cell(world, (low, 9))
        assert is_closed_ridge_cell(world, (high, 9))
        # The row's span reaches the next row's centre, so the wall never
        # leaves a diagonal gap.
        assert is_closed_ridge_cell(world, (ridge_crest_center_x(world, "stem", 10), 9))
        # The authored pass window leaves the stem row open...
        assert ridge_spans(world, 4) == ()
        assert not is_closed_ridge_cell(world, (27, 4))
        # ...but ridge_span reports the physical closure regardless of passes.
        assert ridge_span(world, 4) is not None
        # Outside the stem rows there is no stem span and nothing to close.
        assert ridge_span(world, 40) is None
        assert not is_closed_ridge_cell(world, (0, 0))

    def test_each_crest_is_independently_addressable(self):
        world = _world_a()
        assert ridge_crest_center_x(world, "stem", 0) == 28
        assert ridge_crest_center_x(world, "stem", 31) is None
        assert ridge_crest_center_x(world, "west", 38) == 18
        assert ridge_crest_center_x(world, "east", 38) == 34
        assert ridge_crest_center_x(world, "west", 39) is None
        with pytest.raises(ValueError):
            ridge_crest_center_x(world, "north", 0)
        # A known arm that is absent is not an error: it simply has no rows.
        assert ridge_crest_center_x(_world_b(), "west", 0) is None

    def test_interpolation_is_integer_half_up_for_a_negative_bend(self):
        world = TerrainDefinition(
            frame_cells=24,
            mainland_boundary_km=((0, 0), (24, 0), (24, 24), (0, 24)),
            forest_edge=((0, 23), (23, 23)),
            waterway_routes={"border_river": ((5, 8), (0, 8))},
            waterway_fords={},
            border_river_key="border_river",
            ridge_stem=((12, 0), (10, 10), (8, 14)),
            ridge_passes=(),
            coastal_y_max=4,
            mountain_corridor_half_width=2,
            region_flavors=_flavors("i"),
        )
        centres = [ridge_crest_center_x(world, "stem", y) for y in range(10, 15)]
        assert centres == [10, 10, 9, 9, 8]

    def test_crotch_is_blocked_and_separated_arms_are_never_filled(self):
        world = _world_a()
        # The crotch row joins the stem terminal and both arm starts.
        assert ridge_spans(world, 30) == ((25, 27),)
        # Two separated arms at a northern row; the gap between them is open.
        assert ridge_spans(world, 36) == ((19, 20), (32, 33))
        assert not is_closed_ridge_cell(world, (27, 36))
        assert not is_closed_ridge_cell(world, (23, 36))

    def test_arms_are_blocked_and_a_stem_pass_does_not_open_them(self):
        world = _world_a(ridge_passes=((10, 12),))
        assert ridge_spans(world, 11) == ()  # the stem pass opens only the stem
        assert ridge_spans(world, 38) == ((18, 18), (34, 34))
        assert is_closed_ridge_cell(world, (18, 38))
        assert is_closed_ridge_cell(world, (34, 38))

    def test_ridge_polyline_clips_the_authored_vertices(self):
        world = _world_a()
        assert ridge_polyline(world, 0, 30) == ((28, 0), (26, 10), (24, 20), (26, 30))
        assert ridge_polyline(world, 5, 25) == ((27, 5), (26, 10), (24, 20), (25, 25))
        assert ridge_polyline(world, 10, 10) == ((26, 10),)
        assert ridge_polyline(world, 31, 35) == ()

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
        assert not is_walkable_cell(world, (28, 0))  # stem wall
        assert not is_walkable_cell(world, (18, 38))  # arm wall

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

    def test_national_borders_are_derived_from_the_river_and_the_stem(self):
        world = _world_a()
        borders = {border.nation_keys: border.points for border in world.national_borders}
        assert set(borders) == {
            ("altoria", "valhalla"),
            ("altoria", "grandia"),
            ("grandia", "valhalla"),
        }
        river_line = borders[("altoria", "valhalla")]
        # The river reversed, then its source row east to the stem centre.
        assert river_line[0] == (0, 20)
        assert river_line[-1] == (ridge_center_x(world, 20), 20)
        south = borders[("altoria", "grandia")]
        north = borders[("grandia", "valhalla")]
        # Both displayed ridge lines are exactly the clipped authored stem.
        assert south[0] == (ridge_center_x(world, south[0][1]), south[0][1])
        assert north[-1] == (ridge_center_x(world, north[-1][1]), north[-1][1])
        for point in (*south, *north):
            assert point[0] == ridge_center_x(world, point[1])


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
            _world_a(ridge_passes=((6, 5),))
        with pytest.raises(ValueError):
            _world_a(ridge_passes=((4, 5, 6),))
        with pytest.raises(ValueError):
            _world_a(mainland_boundary_km=((0, 0), (1, 1)))
        # A stem that does not begin at row 0.
        with pytest.raises(ValueError):
            _world_a(ridge_stem=((28, 1), (26, 10)), ridge_branches={})
        # Non-increasing rows.
        with pytest.raises(ValueError):
            _world_a(ridge_stem=((28, 0), (26, 0)), ridge_branches={})
        # A segment steeper than one column per row.
        with pytest.raises(ValueError):
            _world_a(ridge_stem=((28, 0), (20, 5)), ridge_branches={})
        # Wandering off the frame is rejected before any row table is built.
        with pytest.raises(ValueError):
            _world_a(ridge_stem=((28, 0), (26, 40)), ridge_branches={})
        # Branches must be paired.
        with pytest.raises(ValueError):
            _world_a(ridge_branches={"west": _WEST_A})
        # A branch must start at the stem's last point.
        with pytest.raises(ValueError):
            _world_a(
                ridge_branches={"west": ((20, 30), (18, 34), (16, 38)), "east": _EAST_A}
            )
        # Tips must stay on opposite sides of the crotch.
        with pytest.raises(ValueError):
            _world_a(
                ridge_branches={"west": ((26, 30), (30, 34), (34, 38)), "east": _EAST_A}
            )
        # The shared crotch cannot be a pass window.
        with pytest.raises(ValueError):
            _world_a(ridge_passes=((30, 30),))
        # Every active stem centre must lie strictly east of the river source.
        with pytest.raises(ValueError):
            _world_a(ridge_stem=((15, 0), (14, 10)), ridge_branches={})


class TestTerrainPreview:
    """The coarse preview is the classifier's own answer at its sample cells."""

    def test_every_sample_agrees_with_the_rule_functions(self):
        from elosern_map_core.terrain import (
            PREVIEW_SURFACES,
            is_closed_ridge_cell,
            is_inland_water_cell,
            is_land_cell,
            terrain_preview,
        )

        definition = _world_a()
        preview = terrain_preview(definition, max_side=8)
        assert preview.step == 5 and preview.columns == preview.rows == 8
        assert len(preview.samples) == 64
        for row in range(preview.rows):
            for column in range(preview.columns):
                x, y = column * 5 + 2, row * 5 + 2
                value = preview.samples[row * preview.columns + column]
                region, surface = divmod(value, len(PREVIEW_SURFACES))
                assert preview.regions[region] == region_for_coordinates(definition, x, y)
                expected = (
                    "sea"
                    if not is_land_cell(definition, (x, y))
                    else "ridge"
                    if is_closed_ridge_cell(definition, (x, y))
                    else "water"
                    if is_inland_water_cell(definition, (x, y))
                    else "land"
                )
                assert PREVIEW_SURFACES[surface] == expected

    def test_an_edited_river_changes_the_preview(self):
        from elosern_map_core.terrain import terrain_preview

        before = terrain_preview(_world_a(), max_side=40)
        moved = _world_a(waterway_routes={"border_river": ((20, 26), (0, 26))}, waterway_fords={})
        after = terrain_preview(moved, max_side=40)
        assert before.samples != after.samples
        # Row 20 lost its water and row 26 gained it.
        water = lambda preview, y: [preview.samples[y * 40 + x] % 4 == 2 for x in range(0, 20)]  # noqa: E731
        assert any(water(before, 20)) and not any(water(after, 20))
        assert any(water(after, 26))

    def test_pass_windows_split_the_stem_wall_and_arms_stay_closed(self):
        from elosern_map_core.terrain import terrain_preview

        preview = terrain_preview(_world_a(), max_side=40)
        assert [(low, high) for low, high, _ in preview.passes] == [(4, 5)]
        _, _, centre = preview.passes[0]
        assert centre == (ridge_center_x(_world_a(), 4), 4)
        # Two stem runs (0-3 and 6-30) plus one wall per arm.
        assert len(preview.ridge_walls) == 4
        stem_rows = sorted({y for wall in preview.ridge_walls for _, y in wall})
        assert stem_rows[0] == 0 and stem_rows[-1] == 38
        assert all(not (4 <= y <= 5) for y in stem_rows)

    def test_borders_are_the_derived_ones_or_explained(self):
        from elosern_map_core.terrain import terrain_preview

        definition = _world_a()
        preview = terrain_preview(definition, max_side=40)
        assert preview.national_borders == definition.national_borders
        assert preview.borders_reason is None
        sea = _world_a(mainland_boundary_km=((100, 100), (101, 100), (101, 101)))
        empty = terrain_preview(sea, max_side=40)
        assert empty.national_borders == () and empty.borders_reason

    def test_invalid_sampling_bound_is_rejected(self):
        from elosern_map_core.terrain import terrain_preview

        with pytest.raises(ValueError):
            terrain_preview(_world_a(), max_side=0)
