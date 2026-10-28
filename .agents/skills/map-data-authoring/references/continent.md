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
    base_x: 1410
    period: 60            # ≥ 1
    step: 10              # ≥ 1
    min_x: 1300           # ≤ max_x
    max_x: 1520
    north_limit_y: 2200
    mountain_corridor_half_width: 100
    passes:               # ≥ 1 window, y_min ≤ y_max
      - {y_min: 410, y_max: 425}
  coastal_y_max: 500
  waterways:
    <waterway_id>:
      route: [{cell_x, cell_y}, ...]   # ≥ 2 points
      fords: [{cell_x, cell_y}, ...]   # optional; crossing cells on the route
  border_river_key: border_river       # must name a waterway, never removed
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
- **Ridge.** For row `y`, the ridge centre is
  `base_x + ((y // period) % 5 − 2) · step`: a zig-zag bend. Within
  `min_x … max_x`, and below `north_limit_y`, the cells between this row's
  centre and the next row's centre are closed walls, **except** rows inside a
  pass window. Land crossings between west and east therefore need a pass.
- **Mountain corridor.** `|x − ridge_centre(y)| ≤ mountain_corridor_half_width`
  is `central_mountains`. East of the corridor is `southeast_coast` when
  `y ≤ coastal_y_max`, and `eastern_plains` otherwise. West of it is
  `southwest_coast` when `y ≤ coastal_y_max`, `northwest_highland_forest` north
  of the border river, and `western_hills_valleys` otherwise.
- **Waterways.** Rasterized route segments are impassable water. Ford cells
  are subtracted, so a ford must be a cell on the route to have any effect.
- **Border river.** This route must be strictly X-**decreasing**: it runs from
  its source next to the ridge westward to its mouth. Its per-column row also
  divides Altoria (the river row and south) from Valhalla (north), west of the
  ridge. East of the ridge centre line is Grandia.

## Validation

- Schema and type errors are **structure** errors: the editor freezes and
  shows a stale preview.
- Inconsistent terrain is a saveable **semantic** `terrain_inconsistent`
  diagnostic. Examples: a non-monotone forest edge or border river, an
  inverted pass, `min_x > max_x`, a missing border river. The editor then shows
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
  waterway routes and fords;
- `set_terrain_parameter` for ridge fields, `coastal_y_max` and
  `border_river_key`;
- ridge passes: add, set and remove;
- `add_waterway` and `remove_waterway` (the border river is never removed);
- `set_region_field`;
- harbour sites: add, set and remove.

You may make any of these edits by hand with the same constraints. Do not
add or remove a region key.
