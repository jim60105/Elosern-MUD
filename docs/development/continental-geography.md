# Continental geography and coordinate units

`world/lore/` owns the frozen physical geography of the known continent. These
declarations are authoring contracts only: they spawn no rooms and are
independent of persistent room lifecycle. `rescale-wilderness-geography`
activates them in `world/maps/wilderness_provider.py`: the runtime provider is
now the same 2700 by 2700 one-kilometre frame, and the variable cell span the
travel-cost core reads is `WILDERNESS_KM_PER_CELL = 1`.

## Runtime terrain and validity

The provider owns one shared cell-validity rule
(`is_valid_wilderness_cell`): inside the frame, inside the mainland polygon
evaluated at the cell centre, off the cliff-walled central summit ridge, off
the authored inland waterways, and outside every live anchor footprint. Sea,
ridge and water are impassable on foot; three authored pass windows
(`RIDGE_PASSES`, the principal one near `(1410, 980)`) and the declared
`WATERWAY_FORDS` are ordinary walkable ground. Every query is bounded local
arithmetic — no frame scan, no room materialization.

`region_for_coordinates` classifies the whole frame into the seven registry
regions with the authored bending mountain corridor, the meandering northern
deep forest edge (`NORTH_FOREST_EDGE`, averaging about Y 1920 and covering
about one fifth of the land) and the border river; `terrain_description`
stays the pinned `(x * 92821 + y * 68917) % len(variants)` form. Altoria's
rasterized footprint is a 40 km² irregular mask and Ciaran is a hidden point
entrance with one authored entry direction, so unrelated directions there stay
ordinary wilderness steps.

## Border river, forest edge and nominal claims

界河 (`WATERWAY_ROUTES["border_river"]`) rises at the mountain corridor's
first cell `(1320, 1410)` and meanders west inside Y 1290..1410 to the west
coast at `(124, 1290)`. Its segments are all shallower than 45 degrees, so the
existing rasterizer lays exactly one water cell per column and
`border_river_row(x)` returns that cell. Corner cutting is forbidden for
diagonal steps, so the one-cell line is a complete barrier; its three fords
(`WATERWAY_FORDS["border_river"]`: upstream `(1150, 1363)`, principal
`(830, 1370)` on the line between the Altoria and Valhalla capitals,
downstream `(450, 1345)`) are the only crossings west of the source. East of
the source the mountain corridor and the ridge passes still connect the two
banks over mountain-trail ground.

The river divides `western_hills_valleys` from `northwest_highland_forest`;
`forest_edge_row(x)` starts `north_deep_forest`. The summit ridge keeps its
own northern limit at Y 2200 inside the forest, and the forest keeps ordinary
woodland travel speed. Region keys stay terrain only:
`nominal_nation_for_coordinates` is the coordinate-sensitive nominal claim
(Grandia east of the ridge centre line, Altoria west of it on or south of the
river row, Valhalla north of it; the source row continues east to the ridge).
The land shares are about Grandia 43 %, Altoria 30 %, Valhalla 27 %; these are
nominal claims, while `Nation.territory_share` keeps the effective-rule
targets. `WildernessRegion.nominal_nation_keys` lists every claimant of a
region, and `nation_key` is `None` for the two shared regions
(`central_mountains`, `north_deep_forest`). Anchor `nation_key` values are
lore identity and are not recomputed from cells: 幽月谷村 lies east of the
ridge in the forest (nominally Grandia) yet stays administratively
independent.

`national_borders()` derives the displayed national lines from the same
geometry: the river plus its source row to the ridge (Altoria | Valhalla) and
the ridge centre line split at that row (Altoria | Grandia,
Grandia | Valhalla), stopping at the forest edge. No political polyline is
authored. The layout prototype under `docs/design/world-map/` predates this
geography and is not runtime data.

## Map districts

`world/lore/map_districts.py` declares `MAP_DISTRICT_REGISTRY`, the frozen
districts of the world map (world-map drawer design §4.1). Each `MapDistrict`
has exactly one landmark and six fields: `key`, `district_name_zh`,
`landmark_name_zh`, `landmark_node`, `kind` (`voronoi` or `region`) and
`region_key` (set only for a `region` district).

- `landmark_node` is the canonical map-knowledge node ID the player's arrival
  records: `wild:elosern:<x>:<y>`, or `grid:<map>:<x>:<y>` for an existing
  settlement node. A grid landmark is placed on the continent through the
  settlement's local frame (`world_position_m`); Altoria's central plaza lands
  on the centre of cell `(860, 1080)`.
- `region` districts take every cell of one terrain region. The northern deep
  forest is the only one: its single landmark, 古樹之心 at `(1250, 2420)`, lies
  about 500 km beyond the forest edge and covers both nominal claims.
- `voronoi` districts seed the walking-distance partition (computed by a later
  change). Two Voronoi landmarks are never closer than
  `MIN_VORONOI_SPACING_KM` (100 km, below the roughly 200 km district target).
  The registry ships a small seed set with at least one seed in each nation
  outside the forest; the landmark-authoring change expands it to 110–130.

`validate_map_districts(registry=None, terrain=None)` is pure and
database-free and reports every fault with its district key: identity and
field shape, kind/region pairing, duplicate keys, nodes and names, canonical
node grammar, sea, blocked terrain (ridge, river or anchor footprint), absent
grid nodes, unreachable landmarks, region membership (a Voronoi seed may not
sit in region-district land) and the spacing rule. A wilderness landmark is
reachable when it lies in the same walkable component as a registered
gateway approach (`world/maps/wilderness_reachability.py` indexes the exact
components); a grid landmark is reachable when the settlement graph routes to
it from a gate whose approach is reachable. Validation is not a startup step;
the data-contract test `world.lore.tests.test_map_district_content` runs it
against the shipped registry, and synthetic rule tests pass their own
`terrain`. The registry is browsable in the GM portal index; it is not
mirrored by `world/lore/sync.py`.

Lighting is derived, never stored: `world/rules/map_district_lighting.py`
lights a district if and only if its exact landmark node is in the visited
record read through `parse_knowledge`. Nearby cells never light a district;
`record_arrival` stays the only writer and no discovery attribute, name or
geometry is added to knowledge. The first-arrival `已探明` narrative belongs to
the world-map panel change.

## Declarations

| Module | Declaration | Contract |
| --- | --- | --- |
| `world/lore/wilderness_regions.py` | `MAINLAND_BOUNDARY_KM` | Ordered mainland boundary vertices in absolute `(east, north)` kilometres; implicitly closed. Shoelace area is exactly 5,000,000 km². |
| `world/lore/wilderness_regions.py` | `CELL_CENTER_OFFSET_M`, `CONTINENT_FRAME_CELLS`, `CONTINENT_CELL_SIZE_KM` | Wilderness cells are logical one-kilometre areas; the frame is 2700 × 2700 cells (`0 <= X, Y < 2700`). |
| `world/lore/wilderness_regions.py` | `HARBOR_SITE_REGISTRY` | Six reserved land-side harbor cells with their intended roles. A functional site is not a named anchor, city, quest or population. |
| `world/lore/wilderness_regions.py` | `cell_center_m`, `is_wilderness_cell`, `mainland_area_km2`, `is_on_mainland` | Pure geometry helpers over the declarations above; boundary points count as land. |
| `world/lore/anchors.py` | `ANCHOR_GEOGRAPHY_REGISTRY` | The canonical wilderness cell and geographic constraint of all nine lore anchors. Separate from both lore identity (`ANCHOR_REGISTRY`) and built grid rooms (`ANCHOR_PLACEMENT_REGISTRY`, deliberately still two entries). |
| `world/lore/anchors.py` | `LOCAL_FRAME_ANCHOR_REGISTRY`, `world_position_m` | Settlement-local metre anchor bindings and the cross-layer transform. |
| `world/lore/nations.py` | `CONTINENT_AREA_KM2`, `CONTINENT_POPULATION`, `ELVEN_POPULATION`, `NEUTRAL_LANDS_AREA_KM2`, `NEUTRAL_LANDS_POPULATION`, `CAPITAL_POPULATION_SHARE` | Rounded continental totals. The neutral lands have no separate regional population total. |
| `world/lore/nations.py` | `Nation.territory_km2`, `CapitalSupport`, `CAPITAL_SUPPORT_REGISTRY` | National area targets and the authored regional food/storage/water support (Valhalla additionally declares pastoral production and trade). |

National `territory_share` and `territory_km2` are area targets. They are
neither terrain nor actual control, and the mean inhabitants per square
kilometre they produce is an average, never a per-cell population raster.
Nothing in the declarations creates per-cell population or resource state.

## Coordinate units

- A wilderness cell is an area. Its representative center in absolute metres is
  `E = 1000 * X + 500`, `N = 1000 * Y + 500` (`cell_center_m`).
- Settlement positions are integer metres east/north. Their `z` coordinate
  remains the logical grid/layer and is never physical elevation.
- Cross-layer geometry uses the bound local anchor:
  `world_m = wilderness_anchor_center_m + local_m - local_anchor_m`
  (`world_position_m`). Altoria's plaza `(3500, 2850)` binds to cell
  `(860, 1080)`; Ciaran's plaza `(220, 305)` binds to cell `(1340, 1220)`.
- Never subtract settlement-local metres directly from wilderness cell indices.
  Interiors without coordinates stay coordinate-free connected scenes.
- The frame describes one continent. No planet size or further continent is
  inferred.

## Ownership boundary

`world/lore/` stays read-only: the declarations are consumed by later changes
(cost charging, local-map projection, settlement/wilderness rescaling) but this
change neither relocates persistent rooms nor wires the declarations into
movement, rendering, map knowledge or the lore codex. Declaring an anchor cell
also reveals nothing: knowledge and visibility rules remain authoritative, and
`ANCHOR_GEOGRAPHY_REGISTRY` is not a lore-codex category.

The earlier two-entry `ANCHOR_PLACEMENT_REGISTRY` continues to describe exactly
the anchors with a built grid map; all nine geographic cells live in
`ANCHOR_GEOGRAPHY_REGISTRY` instead.

## Verification

```sh
uv run --locked python -m unittest \
  world.lore.tests.test_nations \
  world.lore.tests.test_anchors \
  world.lore.tests.test_wilderness_regions \
  world.lore.tests.test_anchor_placement
uv run --locked python -m tools.spec_traceability check
uv run --locked python -m tools.test_data_lint check
```

Map districts run under the Evennia test runner (`<env>` holds
`MUD_TEST_SETTINGS=1`):

```sh
uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb \
  world.lore.tests.test_map_districts world.lore.tests.test_map_district_content \
  world.rules.tests.test_map_district_lighting
```

The assertions behind `continental-geography` live in those data-contract test
modules; see `openspec/specs/continental-geography/spec.md`.
