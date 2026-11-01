# `content/maps/continent.yaml`

The singleton continental document (`id: continent`). It holds every
**input** to the deterministic terrain classifier. National borders, regions
per cell, passability and districts are **derived output**. Nothing here
draws a political border: borders follow the ridge and the border river.

## Coordinate frame

- `frame_cells: 2700`. Wilderness cells satisfy `0 ≤ cell_x, cell_y < 2700`.
- `cell_size_km: 1`. The game accepts only `1`.
- `cell_x` grows **east**, `cell_y` grows **north**. The south coast is at low
  `y`, and the northern deep forest at high `y`.
- A cell's centre in metres is `E = 1000·x + 500`, `N = 1000·y + 500`.

## Fields

```yaml
version: 1
kind: continent
id: continent
frame_cells: 2700
cell_size_km: 1
mainland_boundary_km:          # ≥ 3 vertices, integer km, implicitly closed
  - {east_km: 450, north_km: 100}
regions:                       # exactly the 7 fixed keys below, no more, no fewer
  central_mountains:
    display_name_zh: 中央山脈
    nation_key:                # nullable: administrative owner, or empty for shared regions
    terrain_flavor_zh: [..., ...]   # ≥ 2 non-blank zh-TW prose variants
    nominal_nation_keys: [altoria, grandia, valhalla]   # optional list of claimants
    scene_archetype: mountain_path  # required by the game; must exist in the scene catalogue
harbor_sites:                  # reserved land-side port cells (not towns, not anchors)
  <site_id>:
    display_name: Imperial southeastern main port
    cell: {cell_x: 2070, cell_y: 241}
    role: Agricultural and magical-goods exports
terrain:
  forest_edge: [{cell_x, cell_y}, ...]   # ≥ 2 points, cell_x strictly increasing
  ridge:
    stem:                 # required, ≥ 2 cells, first row 0, rows strictly increasing
      - {cell_x: 1410, cell_y: 0}
      - {cell_x: 1408, cell_y: 1660}
      - {cell_x: 1420, cell_y: 2000}
    branches:             # optional; if present exactly west and east, each ≥ 2
      west:               # first cell equals the stem's last cell; tip west of it
        - {cell_x: 1420, cell_y: 2000}
        - {cell_x: 1320, cell_y: 2240}
      east:               # tip east of the crotch
        - {cell_x: 1420, cell_y: 2000}
        - {cell_x: 1510, cell_y: 2240}
    mountain_corridor_half_width: 100
    passes: []            # possibly empty, y_min ≤ y_max per window
  coastal_y_max: 500
  waterways:
    <waterway_id>:
      route: [{cell_x, cell_y}, ...]   # ≥ 2 points
      fords: [{cell_x, cell_y}, ...]   # optional; crossing cells on the route
  border_river_key: border_river       # must name a waterway, never removed
elevation_shapes:                      # optional ordered list of elevation shapes
  - shape: circle                      # circle | polygon
    op: raise                          # raise | lower | flatten | no_prominence
    centre: {cell_x: 100, cell_y: 100} # required for circle
    radius: 20                         # required for circle, integer ≥ 1
    amount: 5                          # 1..15, required for raise/lower
    feather: 5                         # integer ≥ 1, required for raise/lower/flatten
    note: Optional descriptive note    # optional string
  - shape: polygon
    op: flatten
    vertices: [{cell_x: 200, cell_y: 200}, {cell_x: 250, cell_y: 200}, {cell_x: 220, cell_y: 250}] # ≥ 3 distinct
    target_band: 8                     # 0..15, required for flatten
    feather: 10
```

Region keys (required, fixed): `central_mountains`, `eastern_plains`,
`north_deep_forest`, `northwest_highland_forest`, `southeast_coast`,
`southwest_coast`, `western_hills_valleys`. Nation keys must exist in the
reference index (`external_identifiers.nations`: `altoria`, `grandia`,
`valhalla`). Scene archetypes must appear in
`external_identifiers.scene_archetypes`.

## How each input shapes the derived map

Read this before you move anything. The effects reach far.

- **Mainland polygon.** A cell is land when its centre lies inside the
  polygon (boundary points count as land). Locations, harbour sites,
  footprints and landmarks must stay on land. Shrinking the coast can strand
  them in the sea.
- **Forest edge.** A per-column row table. Cells with `y ≥ forest_edge_row(x)`
  are `north_deep_forest`. The polyline must be strictly X-increasing, and
  should span `x = 0 … 2699`.
- **Ridge.** The authored `stem` is the single shape authority: each row's
  centre is the integer half-up interpolation along its segments (at most one
  column of movement per row), and the cells between this row's centre and the
  next row's centre are closed walls. `branches.west`/`east` start at the
  stem's last cell (the shared crotch), end north of it on opposite sides and
  are additional impassable forest barriers with **no** corridor and **no**
  political line; the deep forest between the arms stays walkable. A `passes`
  window (which may be empty, and ships empty) exempts only its stem rows, so
  the arms never open. The route endpoints therefore own every derived extent;
  no periodic sawtooth or separate reference axis exists.
- **Mountain corridor.** `|x − ridge_centre(y)| ≤ mountain_corridor_half_width`
  is `central_mountains`. East of the corridor is `southeast_coast` when
  `y ≤ coastal_y_max`, and `eastern_plains` otherwise. West of it is
  `southwest_coast` when `y ≤ coastal_y_max`, `northwest_highland_forest` north
  of the border river, and `western_hills_valleys` otherwise.
- **Waterways.** Rasterized route segments are impassable water. Ford cells
  are subtracted, so a ford must be a cell on the route to have any effect.
- **Border river.** This route must be strictly X-**decreasing**: it runs from
  its source next to the stem westward to its mouth, and its first vertex must
  be its easternmost; every active stem centre must lie strictly east of that
  source column. Its per-column row also
  divides Altoria (the river row and south) from Valhalla (north), west of the
  stem. East of the stem centre line is Grandia.

## Validation

- Schema and type errors are **structure** errors: the editor freezes and
  shows a stale preview.
- Inconsistent terrain is a saveable **semantic** `terrain_inconsistent`
  diagnostic. Examples: a non-monotone forest edge or border river, an
  inverted pass, a stem not beginning at row 0, a steeper-than-one-column
  segment, branches that do not start at the crotch or that cross/rejoin,
  a crotch pass, a stem west of the river source, an arm that leaves the
  frame/land/forest or hits a waterway, harbour, location or resolved
  landmark, a missing border river. The editor then shows
  `terrain_preview.status: unavailable`.
- Game-only rules:
  - all 7 regions are present, each with a registered `scene_archetype`;
  - nation keys are known;
  - every location and harbour cell is in the frame and on the mainland;
  - every footprint cell is walkable.

  The check script reports each of these.
- Every continent edit stales the district partition. Regenerate it (see
  [verification.md](verification.md)).

## Editor equivalents

The editor offers the following continent tools:
- control-point move, insert and remove for the mainland, forest edge and
  waterway routes and fords, and for the ridge routes (`feature:
  {kind: ridge_route, route: stem|west|east}`; moving or deleting a shared
  crotch cell is atomic/refused);
- `set_terrain_parameter` for `ridge.mountain_corridor_half_width`,
  `coastal_y_max` and `border_river_key`; the retired periodic fields are
  refused;
- ridge passes: add, set and remove;
- `add_waterway` and `remove_waterway` (the border river is never removed);
- `set_region_field`;
- harbour sites: add, set and remove.

You may make any of these edits by hand with the same constraints. Do not
add or remove a region key.
