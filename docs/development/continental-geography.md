# Continental geography and coordinate units

The authored physical geography of the known continent lives in two map
sources: `content/maps/continent.yaml` (frame, mainland boundary, terrain
regions and prose, classifier parameters, waterways and fords, forest edge,
ridge/passes and the reserved harbour sites) and `content/maps/locations.yaml`
(every static geographic location's kind, name, description, cell and
geographic constraint, including the unbuilt capitals, villages and dungeons).
These declarations are authoring contracts only: they spawn no rooms, floors or
instances and are independent of persistent room lifecycle.

`world/maps/geography.py` is the one game-side adapter. It reads both
canonical documents from an explicit root through `elosern_map_core`,
composes the read-only views (terrain rules, region views, harbour sites,
location identity and cell) and validates every cross-domain join before it
publishes one immutable `GeographySnapshot`. Publication is atomic: a failed
candidate leaves the previously published snapshot untouched. The game
composition root loads and publishes at startup
(`geography_source_publication`, the first startup step); tests and tools
call `load_and_publish()` explicitly. Nothing loads or validates at import.

Political affiliation, population and dungeon floor counts are *not* map
fields: they stay in `world/lore/anchors.py::ANCHOR_LORE` and are joined by the
same stable location identity. Settlement graphs, bindings, districts and
interiors remain their own Python authorities until their own cutover.

The pure classification, waterway rasterization and derivation rules live in
`packages/map-core/elosern_map_core/terrain.py` and run over the snapshot's
explicit `TerrainDefinition`: the runtime provider is the same 2700 by 2700
one-kilometre frame, and `wilderness_provider.WILDERNESS_KM_PER_CELL`
projection reads the authored `cell_size_km = 1`.

## Runtime terrain and validity

One shared cell-validity rule (`is_valid_wilderness_cell`, a
`world/maps/wilderness_provider.py` wrapper binding the live footprint
registry and the published terrain snapshot into the core rule) decides
validity: inside the frame, inside the mainland polygon
evaluated at the cell centre, off the cliff-walled central summit ridge, off
the authored inland waterways, and outside every live anchor footprint. Sea,
ridge and water are impassable on foot; the authored pass windows
(`terrain.ridge.passes`, the principal one near `(1410, 980)`) and the declared
waterway fords are ordinary walkable ground. Every query is bounded local
arithmetic, with no frame scan or room materialization; derived tables belong
to the snapshot, so a reload never reuses another world's results.

`region_for_coordinates` classifies the whole frame into the declared region
views with the authored bending mountain corridor, the meandering northern
deep forest edge (`terrain.forest_edge`, averaging about Y 1920 and covering
about one fifth of the land) and the border river; `terrain_description`
stays the pinned `(x * 92821 + y * 68917) % len(variants)` form. Altoria's
rasterized footprint is a 40 km² irregular mask and Ciaran is a hidden point
entrance with one authored entry direction, so unrelated directions there stay
ordinary wilderness steps.

## Border river, forest edge and nominal claims

界河 (`terrain.waterways["border_river"]` in the continent document) rises at
the mountain corridor's
first cell `(1320, 1410)` and meanders west inside Y 1290..1410 to the west
coast at `(124, 1290)`. Its segments are all shallower than 45 degrees, so the
existing rasterizer lays exactly one water cell per column and
`border_river_row(x)` returns that cell. Corner cutting is forbidden for
diagonal steps, so the one-cell line is a complete barrier; its three fords
(the same waterway's `fords`: upstream `(1150, 1363)`, principal
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
`landmark_name_zh`, `landmark`, `kind` (`voronoi` or `region`) and
`region_key` (set only for a `region` district).

- `landmark` is a qualified authored identity: an existing settlement node
  identity, an authored location, or an explicitly typed wilderness cell. The
  canonical map-knowledge node ID the player's arrival records
  (`wild:elosern:<x>:<y>` or `grid:<map>:<x>:<y>`) is derived from the
  current binding by `world.lore.map_districts.landmark_node_ids`, never stored
  in the row. A settlement landmark is placed on the continent through the
  settlement's local frame (`world_position_m`); Altoria's central plaza lands
  on the centre of cell `(860, 1080)`.
- `region` districts take every cell of one terrain region. The northern deep
  forest is the only one: its single landmark, 古樹之心 at `(1250, 2420)`, lies
  about 500 km beyond the forest edge and covers both nominal claims.
- `voronoi` districts seed the walking-distance partition (see
  [District partition](#district-partition)). Two Voronoi landmarks are never closer than
  `MIN_VORONOI_SPACING_KM` (100 km, below the roughly 200 km district target).

### Authored roster

The current registry holds 120 districts, comprising 119 Voronoi districts and
one deep-forest region district. This is an authoring snapshot, not a required
count; the manually edited registry owns membership. Placement targets roughly
200 km district width and distributes seeds across each nominal nation's
walkable land outside the forest.

- Placement. Seeds sit near the centroids of a relaxed layout computed per
  nation. The original seeds stay fixed at their authored cells. The
  Grandia (`(1970, 1280)`) and Valhalla (`(780, 1910)`) capital anchor cells
  are also fixed, so standing in either capital lights its district. Two
  landmarks were moved onto features: the imperial east-branch ford
  `(2300, 526)` and a bank of the capital river. Pass and border-river fords
  are not landmarks: the border closes the partition there, so a seed on it
  produces a sliver district along the ridge or river. The coordinates are
  ordinary authored values; nothing is generated at runtime, and this
  document does not repeat them.
- Future grid maps. When the Grandia or Valhalla capital gains a settlement
  grid map, move its landmark to the matching `grid:` node (its footprint
  would block the current wilderness cell) and regenerate the partition.
- Names. Each district and landmark has a distinct, hand-authored Traditional
  Chinese name in JRPG sword-and-magic vocabulary that fits its terrain:
  coasts, river reaches, hills and mines for Altoria; plains, orchards,
  canals and magic-crystal fields for Grandia; highland forest, hunting and
  totems for Valhalla; and peaks and passes on the range. A landmark is a
  natural feature, ruin, stone, shrine or similar place. It never names a new
  city, settlement, quest or NPC, and it never sits on an elven village or
  dungeon cell, because those stay hidden until visited. As an authoring
  margin, the roster also keeps every landmark at least 50 km from them.
- Keys are stable. Changing a landmark's node or adding a district changes
  ownership, so regenerate and commit the partition (below) in the same
  change.

### Validation and lighting

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

## District partition

`tools/map_district_partition.py` computes which district owns every land
cell offline (world-map drawer design §4.2) and writes the frozen,
version-controlled result to `world/maps/data/district_partition.json`.
The runtime only reads that file through `world/maps/district_partition.py`
(`district_at((x, y))`, `district_outlines()`); it never imports the generator
or recomputes ownership.

Regenerate after any change to the district registry, the terrain model
(mainland, ridge, passes, waterways, fords, forest edge, nominal claims),
anchor footprints, gateways or the settlement routes to a grid landmark:

```sh
uv run --locked python -m tools.map_district_partition          # rewrite the file
uv run --locked python -m tools.map_district_partition --check  # exit 1 when stale
```

Commit the regenerated file with the change that caused it. The data-contract
test `world.maps.tests.test_map_district_partition` regenerates it from the
shipped inputs and fails on any byte difference, so stale data is never
adopted at runtime. Run `validate_map_districts` (or
`world.lore.tests.test_map_district_content`) first: the 100 km
`MIN_VORONOI_SPACING_KM` spacing, reachability and region-membership rules
belong to the registry validator, not the partitioner.

Datum and units:

- Ownership is exact per one-kilometre cell (`(x, y)`, 0..2699). Walking
  distance runs on 5 km tiles (540 × 540): each tile's walkable cells split
  into fragments by nominal nation and legal steps, and fragments of adjacent
  tiles join at cost 1 (cardinal tile step) or √2 (diagonal tile step) only
  where a legal one-kilometre step crosses between them.
- A legal step joins walkable, non-region cells of the same nominal nation; a
  diagonal step also needs both orthogonal cells legal. Sea, the ridge,
  rivers, footprints and region land block propagation, and national borders
  stay closed even at passes and fords.
- The deep forest region district is reserved first, across both claims.
  Every other walkable cell takes the nearest Voronoi landmark; equal
  distances go to the smaller district key, then the earlier tile/cell in
  row-major order. A grid landmark starts from the routed same-nation gateway
  approach cells of its settlement, and owns its containing footprint plus any
  pocket that footprint encloses. Generation fails, naming a cell, when a
  walkable component has no landmark.
- Ridge, river and other blocked land display the nearest same-nation owner
  (squared centre distance, then key, then cell); sea has no owner.
- Outlines are metres in the east/north frame (`1000 * x` per cell edge).
  Boundary pieces are shared between neighbours and smoothed once (edge
  midpoints, then a 500 m Douglas-Peucker), so no gap or overlap appears;
  pieces along a national border keep their exact cell-edge geometry, and
  junctions stay exact. Outer rings run counter-clockwise, holes clockwise.

The file stores tile ownership as row runs (`-1` marks a tile whose land has
several owners), exact 25-cell runs for those tiles, the outlines and a
SHA-256 fingerprint of the algorithm version, districts and input rasters.
Lookup checks the mainland polygon first, then the exception tile, then the
tile run.

## Declarations

| Owner | Declaration | Contract |
| --- | --- | --- |
| `content/maps/continent.yaml` | `frame_cells`, `cell_size_km`, `mainland_boundary_km` | Ordered mainland boundary vertices in absolute `(east, north)` kilometres; implicitly closed. Shoelace area is exactly 5,000,000 km². Wilderness cells are logical one-kilometre areas; the frame is 2700 × 2700 cells (`0 <= X, Y < 2700`). The cell-centre arithmetic and its `500` metre offset live in `elosern_map_core.geometry`. |
| `content/maps/continent.yaml` | `regions` | The seven terrain regions with their display names, nominal claims, at least two nonblank prose variants and their map-owned `scene_archetype`, validated against the game scene catalog at publication. |
| `content/maps/continent.yaml` | `terrain` | Every classifier input: forest edge, ridge parameters and passes, coastal boundary, waterways with their fords and the border-river key. |
| `content/maps/continent.yaml` | `harbor_sites` | Reserved land-side harbor cells with their intended roles. A functional site is not a named anchor, city, quest or population. |
| `content/maps/locations.yaml` | `locations` | Every static geographic location's kind, name, description, cell and geographic constraint, including locations with no built settlement or interior. |
| `world/maps/geography.py` | `load_geography`, `publish`, `current` | Explicit document load, cross-domain validation and atomic publication of the immutable `GeographySnapshot`; every consumer reads `current()`. |
| `world/lore/wilderness_regions.py` | `regions`, `harbor_sites`, `frame_cells`, `mainland_boundary_km`, `is_wilderness_cell`, `mainland_area_km2`, `is_on_mainland` | Thin read-only accessors over the published snapshot, bound into `elosern_map_core.geometry`; boundary points count as land. |
| `world/lore/anchors.py` | `anchors`, `anchor_geography`, `ANCHOR_LORE` | The composed location views (map-facing fields plus the non-map nation/population/floor lore joined by identity). `LOCAL_FRAME_ANCHOR_REGISTRY` and `world_position_m` stay settlement-local frame declarations; the transform itself is `elosern_map_core.geometry.local_to_world_m`. |
| `world/lore/nations.py` | `CONTINENT_AREA_KM2`, `CONTINENT_POPULATION`, `ELVEN_POPULATION`, `NEUTRAL_LANDS_AREA_KM2`, `NEUTRAL_LANDS_POPULATION`, `CAPITAL_POPULATION_SHARE` | Rounded continental totals. The neutral lands have no separate regional population total. |
| `world/lore/nations.py` | `Nation.territory_km2`, `CapitalSupport`, `CAPITAL_SUPPORT_REGISTRY` | National area targets and the authored regional food/storage/water support (Valhalla additionally declares pastoral production and trade). |

National `territory_share` and `territory_km2` are area targets. They are
neither terrain nor actual control, and the mean inhabitants per square
kilometre they produce is an average, never a per-cell population raster.
Nothing in the declarations creates per-cell population or resource state.

## Coordinate units

- A wilderness cell is an area. Its representative center in absolute metres is
  `E = 1000 * X + 500`, `N = 1000 * Y + 500`
  (`elosern_map_core.geometry.cell_center_m`).
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

The map sources own every map-facing declaration; `world/lore/` owns the
non-map lore joined to them and the read-only view types. The runtime map,
travel-cost and presentation owners consume the published snapshot;
persistent room relocation remains the responsibility of `world/maps`
synchronization. Declaring a location cell reveals nothing; knowledge and
visibility rules remain authoritative, and `anchor_geography()` is not a
lore-codex category.

`ANCHOR_PLACEMENT_REGISTRY` describes exactly
the locations with a built grid map; all geographic cells live in
`anchor_geography()` instead. A placement holds the qualified
settlement-node identity of the anchor room; its current grid address is
derived through `world/maps/static_references.py`.

## Quest destinations on the map

`web/webclient/presentation/map_quest_destinations.py` is the one shared,
read-only interpretation of where an accepted commission points, used by the
area and world map panels (world-map drawer design §5.4). Only in-progress
records resolve, from their current stage's objective:

| Family | Source | `world_cell` | Local identity (`map_key`, `node_id`) |
| --- | --- | --- | --- |
| ANCHOR locator | `anchor_geography()` | the anchor's cell | the built entrance node from `ANCHOR_PLACEMENT_REGISTRY`, when it exists in the settlement graph |
| GRID locator | the placement whose `zcoord` is the locator's map | the settlement's anchor cell | the locator's own `grid:<map>:<x>:<y>` node, when it exists in the settlement graph |
| BOUND_INSTANCE locator | the accepted record's `stage_room_id` | the bound room's origin-room cell, when one resolves | the canonical `room:<dbref>` identity, when the bound room is a live `InstanceRoom` |
| Species hunt | the objective's `region_key` | the legal cell of that region nearest the player | `wild:elosern:<x>:<y>` |
| Monster site | `MONSTER_SITE_REGISTRY` | the site's authored cell | `wild:elosern:<x>:<y>` |

ANCHOR and GRID world positions intentionally use the settlement's anchor cell
instead of applying an arbitrary local offset, while the area map marks the
actual node. When the settlement exists but the named node does not, the world
cell is kept and the local identity is absent.

The nearest hunt cell is the cell of the target region, inside the region's
`region_search_boxes()` window, that passes `is_valid_wilderness_cell` and has the
smallest squared Euclidean cell distance to the player; ties go to the smaller
`x`, then the smaller `y`. The search visits 16-cell tiles in order of their
lower-bound distance and remembers which tiles hold no cell of the region
under the production classifier, so repeated map views do not rescan the
frame. The player's cell is their wilderness cell, their settlement's anchor
cell, or the anchor cell of the room an instance was entered from; elsewhere
it is unknown and a hunt resolves to nothing.

Unbound instance destinations, tier hunts, acquire, deliver and rendezvous objectives, and
any destination whose canonical source is missing, produce no node and no
coordinate. Each quest-log entry is read and validated on its own, which is a
deliberate read-only exception to the strict `read_records` reader: an
unreadable commission is skipped with a `map_quest_destination_unresolved`
warning and the other destinations stay usable. Resolution never writes
quests, knowledge, rooms or the clock and never spawns anything.

The resolved positions are server-internal. This module serializes nothing;
the world map panel owns precision filtering (exact coordinates only for lit
districts, otherwise 50 km rounding), and out-of-area area markers use a
bearing and distance.

## Verification

The source conversion and adapter mechanisms run as plain unit tests; the
game consumer contracts run under the Evennia test runner (`<env>` holds
`MUD_TEST_SETTINGS=1`):

```sh
uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb \
  world.maps.tests.test_geography_source \
  world.lore.tests.test_wilderness_regions \
  world.lore.tests.test_anchors \
  world.lore.tests.test_nations \
  world.lore.tests.test_anchor_placement
uv run --locked python -m unittest tests.test_map_geographic_sources
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

The district partition's synthetic mechanics run as a plain unit test and its
production recomputation under the Evennia runner:

```sh
uv run --locked python -m unittest tests.test_map_district_partition
uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb \
  world.maps.tests.test_map_district_partition
```

The assertions behind `continental-geography` live in those data-contract test
modules; see `openspec/specs/continental-geography/spec.md`.

Quest destination resolution runs under the Evennia runner with synthetic
geography and quests only:

```sh
uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb \
  web.webclient.presentation.tests.test_map_quest_destinations
```
