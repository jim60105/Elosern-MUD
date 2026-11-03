# Settlement synthesis

`tools/settlement_synthesis/` answers these questions about a settlement:

- **Where does it sit?** `site` derives the rivers, sea, fords, harbour sites,
  relief and neighbour bearings around one location.
- **How big is it?** `budget` turns a population into a built-up area, a
  wilderness footprint, a metre envelope and a gameplay tier.
- **Does the drawn graph fit?** `lint` checks authored nodes, roads and gates
  against the terrain in world metres.
- **What is the coarse street graph?** `generate` grows a footprint, places the
  role nodes and connects them with directed roads, then writes the document.
- **How does an existing map change without losing identity?** `generate
  --replace --bind` regenerates the graph around the node ids that other
  documents still name.
- **What should the prose say, and where is it safe to write?** `brief` prints
  the machine-readable site and node brief, and `prose` applies node names and
  descriptions only.

`site`, `budget`, `lint` and `brief` are read-only. `generate` creates a
settlement source that does not exist yet, or replaces one when every protected
node is bound. `prose` is the second writing command, and it changes only a
node's `key` and `desc`. They live in the game environment because they join
`world.lore.anchors.ANCHOR_LORE` for nation and population; they need no Django
setup. `--lore FILE` replaces that join with a JSON override, which is how the
tests stay off shipped lore.

## Scales

The wilderness is a grid of 1 km cells whose centre lies at
`(1000X + 500, 1000Y + 500)` metres. Settlement streets are integer-metre
graphs, and their polyline lengths drive walking time at 1.25 m/s. The two
scales stay separate and both come from one built-up area:

- the **footprint** is wilderness occupancy, in whole 1 km cells: a cell becomes
  town instead of wilderness;
- the **envelope radius** is the metre extent of the street graph.

Rounding the footprint up to whole cells absorbs walls, suburbs and gardens,
while the street extent stays at the built-up size. A 6,000-person town is about
770 m across, a 10-minute walk; a 600,000-person capital is about 4 km across,
about 45 minutes gate to gate.

The lint links the scales in one direction: a node must stand inside a
footprint cell. A terrain window is clamped to the continent frame, and a window
boundary is not a coastline — an out-of-frame cell is neither land nor sea and
is not walkable. That is why a gate approach outside the frame is an error
rather than an empty neighbourhood.

## Size budget

Built-up area follows the Cesaretti et al. (2016, *PLOS ONE*) population–area
relation over 173 medieval European cities, `area ∝ population^0.714`.

**Density anchor.** The late-medieval walled-town literature describes roughly
100–250 inhabitants per hectare. The default anchors 10,000 people at
150 inhab/ha, which gives about 0.67 km². This is an accepted assumption for
this game, not a measured constant, and it is one tunable
`BudgetConfig` value rather than a scattered number. With exponent 0.714, density
rises as `population^0.286`.

The derivation, in order:

1. reference area = reference population / reference density / 100 (ha per km²);
2. area = reference area × (population / reference population) ^ exponent;
3. footprint cells = `max(2, ceil(area km²))`, so no supported settlement is
   ever a concealed single-cell entry;
4. envelope radius = `round(1000 × sqrt(area / π))`;
5. the tier is chosen from the table below, or the capital tier for a capital.

| Tier (minimum population) | Nodes | Gates | Loop ratio |
| --- | ---: | ---: | ---: |
| capital | 28 | 4 | 0.35 |
| 100,000 | 18 | 3 | 0.30 |
| 50,000 | 12 | 2 | 0.25 |
| 25,000 | 10 | 2 | 0.20 |
| 10,000 | 8 | 2 | 0.15 |
| below 10,000 | 6 | 2 | 0.15 |

The tiers grow log-like rather than linearly, because they budget gameplay
structure, not floor space.

Default output, for review:

| Population | Area km² | Footprint cells | Envelope radius m | Inhabitants/ha |
| ---: | ---: | ---: | ---: | ---: |
| 6,000 | 0.46 | 2 | 384 | 130 |
| 25,000 | 1.28 | 2 | 639 | 195 |
| 55,000 | 2.25 | 3 | 847 | 244 |
| 180,000 | 5.25 | 6 | 1,293 | 343 |
| 400,000 | 9.28 | 10 | 1,719 | 431 |
| 600,000 | 12.40 | 13 | 1,987 | 484 |
| 800,000 | 15.23 | 16 | 2,202 | 525 |

The three fantasy capitals sit at 430–525 inhabitants per hectare, above
historical walled-town norms. That is an explained constraint, not a
recomputation: the magical-era setting has multi-storey building and regional
supply, per the continental-geography "Large fantasy capitals" scenario. The
budget explains their size; it never changes their population.

A kind outside `capital`, `city`, `town` and `port`, or a population that is
missing or not positive, is rejected with an error naming the location. No
budget is produced.

## Site context

`site` reports, for one location and search radius:

- every waterway within the radius, with Euclidean distance in cells, the
  8-way bearing of the body's centroid, its nearest cell and, for a river, the
  downstream bearing of the route segment nearest that cell;
- the sea, when any sea cell is inside the radius, on the same terms;
- every ford and harbour site, with distance and bearing;
- the relief (band range) and uphill bearing over the walkable cells within
  three cells, plus the location cell;
- the nearest four national settlements, nearest first with ties by identifier;
- the bearing to the settlement's own capital, absent for a capital itself.

The search radius is a Chebyshev box; distances are Euclidean over cell
indices. A river's downstream bearing comes from its authored source-to-mouth
route, so flow direction is real data rather than a guess from geometry.

## Terrain-fit lint

Every check runs in world metres, resolving the settlement's local frame
through its location cell and its unique anchor node. A finding names the map
and the object; the lint never edits a coordinate, a direction or an
identifier.

| Code | Severity | Rule |
| --- | --- | --- |
| `fit_missing_anchor` | error | The map has no unique `anchor_room`, so its local frame cannot be placed. This is the only finding reported. |
| `fit_node_in_water` | error | The node's world position falls in an inland-water or sea cell. |
| `fit_water_role_dry` | error | A node whose identifier carries a water-edge word lies more than 600 m from any water in the window. No water in the window also triggers it. |
| `fit_unbridged_crossing` | error | A road's world-metre polyline enters an inland-water or sea cell while neither endpoint identifier carries a crossing word. |
| `fit_node_outside_footprint` | error | For a multi-cell footprint, the node's cell is not one of the footprint cells. |
| `fit_gate_approach_blocked` | error | For a multi-cell footprint, the gate has no approach cell, or the approach cell is not walkable. |
| `fit_gate_side` | warning | For a multi-cell footprint, the gate's destination node lies more than 90 degrees from the gate's outward bearing. |
| `fit_direction_drift` | warning | The authored road direction is more than one octant from the 8-way bearing of the road's first segment. |

The water-edge words are the whole underscore-separated tokens `quay`,
`wharf`, `dock`, `docks`, `pier`, `landing`, `riverbank` and `waterfront`; the
crossing words are `bridge`, `ford` and `ferry`. An identifier such as
`quayside` therefore claims no water-edge role, while `old_ford_lane` is a
crossing. Ford cells never count as water.

The 600 m water-edge limit exists because the wilderness raster is 1 km: a
stream inside a cell cannot be represented, so a water-edge role is allowed a
generous distance rather than an exact shoreline. Road polylines are sampled
every 50 m or less, endpoints included.

The terrain window is sized from every cell the lint reads: the map's nodes,
road bends, footprint cells and gate approaches. A window is a convex square, so
every sampled point of a segment whose endpoints are inside it is inside it too;
the whole of each road polyline is therefore checked, however far a bend
reaches.

Water is only known per 1 km cell, and the sampler tests points rather than
cell entries: a road that clips the corner of a water cell for less than the
50 m sample spacing can pass between two samples. That is a limit of the
approved sampling rule; the fix for a reported crossing is the same either way,
so it is documented rather than papered over.

Errors mean the graph contradicts its terrain. Warnings are review prompts:
they name a gate that faces inward or a road whose authored exit name drifts
from its drawn shape.

## Commands

Run from the repository root:

```console
uv run --locked python -m tools.settlement_synthesis site LOCATION_ID [--root DIR] [--lore FILE] [--radius N]
uv run --locked python -m tools.settlement_synthesis budget LOCATION_ID [--root DIR] [--lore FILE]
uv run --locked python -m tools.settlement_synthesis lint [MAP_ID ...] [--root DIR]
uv run --locked python -m tools.settlement_synthesis generate LOCATION_ID [--root DIR] [--lore FILE] [--gates OCTANT[,OCTANT...]] [--plan-only]
uv run --locked python -m tools.settlement_synthesis generate --missing --nation NATION [--root DIR] [--lore FILE] [--plan-only]
uv run --locked python -m tools.settlement_synthesis generate LOCATION_ID --replace --bind FILE [--root DIR] [--lore FILE] [--gates OCTANT[,OCTANT...]] [--plan-only]
uv run --locked python -m tools.settlement_synthesis brief MAP_ID [--root DIR] [--lore FILE]
uv run --locked python -m tools.settlement_synthesis prose MAP_ID FILE [--root DIR]
```

- `site` prints the `SiteContext` as JSON and exits 0. `--radius` is the water
  search radius in wilderness cells and defaults to 20 (a 20 km box); the
  relief neighbourhood is always three cells.
- `budget` prints the `SizeBudget` as JSON and exits 0. A location with no
  budget prints its reason to stderr and exits 1.
- `lint` prints one line per finding, `SEVERITY code map_id object_id:
  message`, then `fit: N errors, M warnings`. It exits 0 when no error-severity
  finding exists, 1 when any does, and 2 when the map sources do not load or a
  requested map id is unknown. Warnings alone still exit 0.
- `generate` prints a report per generated map, `{"map_id",
  "settlement_class", "morphology", "footprint_cells", "warnings", "slots":
  [{"id", "role", "key", "x_m", "y_m"}]}`, and writes
  `content/maps/settlements/<location_id>.yaml` unless `--plan-only`. It exits
  1 when the location has no size budget, already has a settlement document
  (printing `exists: <relative path>`), or cannot be generated, and 2 when the
  workspace does not load. `--missing` targets the roster rows of one nation
  that are national kinds without a settlement source, largest population
  first, reloading the workspace before each map so later footprints see the
  earlier ones; per-location errors do not stop the batch.
- `generate --replace` rewrites the settlement already bound to `LOCATION_ID`
  and prints the same report plus `bound`, `dropped`, `renamed_slots` and
  `index_present`. `--bind FILE` is required and `--missing` is refused. A
  missing source prints `missing: <relative path>` and exits 1; a refused
  binding prints every problem and exits 1. `--plan-only` prints the report and
  writes nothing.
- `brief` prints one settlement's prose brief as JSON, described below, and
  exits 0. It exits 2 when the workspace does not load or the map is unknown.
- `prose` applies a JSON object of `{"<node_id>": {"key", "desc"}}` and prints
  `prose: N nodes updated`. An unknown node, an empty key or description, or a
  field other than `key` and `desc` is collected, printed and exits 1 with no
  write. An unreadable file exits 1, and an unknown map exits 2.
- `--root` defaults to the current directory. Nothing is written, so a run can
  never change the sources it inspects; `generate` and `prose` are the writing
  exceptions, and `generate` refuses an existing file without `--replace`.

The lint is a workflow tool, not a CI gate over shipped data. Every authored
settlement lints clean as of `altoria-settlement-maps`, so a new finding names
the map and the object that contradicts its terrain.

## Generation

`generate` produces the coarse fit only: a footprint, the role nodes, gates and
the directed roads between them. Bridges, district shape and appearance are
finished by a person in the map editor. Node `key`s are role labels in zh-TW,
`desc` stays empty for the prose pass, and `city_gate` is always empty. The
output goes through the map-core codec, so it matches the editor's bytes.

Generation is deterministic and seeded by the location id: the seed is the first
eight bytes of `sha256("settlement:<id>:v1")`, one `random.Random` is created per
call, and only `random()` is drawn, never `randint`, `choice` or `shuffle`.
Identical inputs therefore produce byte-identical output, and every set whose
iteration could affect the result is sorted.

**Settlement class.** A nation in the configured beast nations is
`beast_capital` for a capital and `beast_town` otherwise. Other nations give
`human_capital` for a capital, `port` for a port, and `human_town` for a city or
town.

**Reach and morphology.** `reach = ceil(sqrt(footprint_cells) / 2) + 1` cells.
The first river within a Chebyshev reach of the location cell, the sea on the
same terms, and the first ford of that river are the site's water facts. The
morphology is the first match: a beast class gives `tribal_ring`; a port gives
`harbour_crescent` with the sea, else `waterside_linear` with a river, else it is
refused with `water_gap`; a river with a ford gives `river_crossing`; a river
alone gives `waterside_linear`; relief of at least two bands gives
`hill_terraces`; anything else gives `crossroads`.

**Footprint growth.** The footprint starts on the location cell. A water target
adds the shortest 4-connected walkable path to the nearest walkable cell that
touches the water, which can overflow the cell budget and reports
`footprint_reach_overflow:<cells>`. The rest grows one cell at a time, preferring
the candidates that keep the bounding-box midpoint on the location cell and then
the one nearest the growth centre, which leans half a cell toward the water. A
footprint that cannot reach its budget is refused (`footprint_short`). The
midpoint must be a footprint cell (`anchor_outside_footprint` otherwise), and an
offset midpoint reports `footprint_location_offset`. The result is always
4-connected, walkable, free of blocked cells and clear of other maps, gate
approaches, location cells, harbour sites and wilderness landmarks.

**Frame and candidates.** Local metre coordinates are measured from the
location cell centre; the world position is `(1000X + 500 + east, 1000Y + 500 +
north)`. Point selection happens inside an ellipse: a circle of the envelope
radius, or for a waterside, harbour or crossing layout an ellipse whose major
axis runs along the water, and for terraces one whose major axis runs across the
uphill direction. The candidate grid has half-spacing steps over the
footprint's metre bounding box, each point jittered by up to 30% of the step.
Spacing is `min(600, max(60, round(0.8 * R * sqrt(pi / nodes))))` metres; a role
or approach point keeps 0.6 of it, a filler the whole of it. Water-edge
candidates clamp the neighbouring water cell's centre into the footprint cell's
square, inset 50 m, and must stay within the 600 m water-edge limit.

**Placement order.** Anchor `central_plaza` on the location cell; a
`ford_crossing` for a river crossing; gates; approach streets; catalogue roles;
fillers. Gate bearings are taken in priority order — forced octants, the own
capital, the neighbours nearest first, the fords, then `s, n, e, w, se, sw, ne,
nw` — and a bearing is accepted only when its approach cell (walking from the
footprint midpoint until the mask ends) is walkable, unblocked and unused. Fewer
gates than the tier allows reports `gate_shortfall:<missing>`; none is refused
(`no_gate`). Approach streets step from each gate toward the plaza, capped by the
tier and by a third of the remaining nodes; a target with no fitting candidate is
skipped. Catalogue roles are taken by class, minimum node count and water
requirement, in priority order: `near_anchor`, `high_ground` (elevation band,
then uphill), `periphery`, `ring`, `water_edge` and `water_downstream` (the most
downstream water position); a role with no fitting candidate reports
`role_unplaced:<slot>`. Fillers are lane slots that maximise their distance from
every placed node.

**Roads and directions.** The undirected candidates are the Gabriel graph over
the placed nodes, minus any edge whose sampled polyline enters water unless one
endpoint's identifier carries `bridge`, `ford` or `ferry`. Each gate's chain to
the plaza is forced when it does not cross water. A Kruskal spanning tree runs
over the forced edges first and then the shortest candidates, never raising a
degree above six; a disconnected forest is joined by the shortest remaining
candidates, and a graph that still cannot connect is refused. The tier's loop
target adds the shortest non-tree candidates that keep both endpoints below six
roads, and a shortfall reports `loop_shortfall:<deficit>`.

Each node's incident roads are assigned to distinct compass directions by
minimising the total octant deviation; a road that still deviates by more than
67.5° costs the longest removable loop edge, and a node with no removable edge
reports `direction_deviation:<node>`. A road `A → B` carries A's direction and
`B → A` carries B's. Directions are assigned from the emitted integer
coordinates, so rounding or a collision shift cannot leave a road pointing away
from its drawn segment.

**Warnings.** Every warning is a review prompt, never a silent change:
`footprint_reach_overflow`, `footprint_location_offset`, `gate_shortfall`,
`role_unplaced`, `loop_shortfall` and `direction_deviation`, reported sorted and
deduplicated. Refusals are `water_gap`, `footprint_short`,
`anchor_outside_footprint`, `no_gate`, `envelope_full`, `graph_disconnected`,
`degree_overflow`, `water_unreachable` (a waterside, harbour or crossing layout
whose water lies within reach but no walkable path reaches it) and any
terrain-fit lint error; none of them writes a file. An existing settlement is
never overwritten, and a run that finds one exits with `exists: <relative path>`
and changes nothing.

## Rework with bindings

`--replace` regenerates the graph of one existing settlement without losing a
node id that something else joins on. The command finds the document bound to
`LOCATION_ID` by its `location_ref`, not by its file name, and generates the
new plan under that document's own identity. The seed, the document `id` and
the exclusion of the map's own footprint therefore stay stable.

The bind file is JSON whose object order is the resolution order:

```json
{
  "bindings": {
    "gate": "central_plaza",
    "yard": "nearest:central_plaza"
  }
}
```

- A direct value names one plan slot id.
- `nearest:<slot>` takes the closest **unbound** `approach` or `filler` slot to
  `<slot>`, measured in local metres. Ties resolve by plan order.

**Protected nodes.** A replace requires a binding for every node that another
source names:

- an interior `exterior.node` whose `exterior.settlement` is this map;
- a district landmark with `domain: settlement_node` and this `map_id`;
- an incoming external reference keyed `settlement_node:<map>:<node>` in
  `content/map-reference-context.json`;
- the map's `city_gate.node`;
- the anchor node.

When the reference index is absent, every existing node is protected, because
an absent index cannot prove that an external declaration does not name one.
An index that is stale or incompatible with the current external sources proves
no more, so it is treated the same way: every existing node is protected and
the report says `index_present` is false.

**Refusals.** Every problem is collected before one error is raised, and a
refused run writes nothing:

| Problem | Meaning |
| --- | --- |
| `unknown_node:<id>` | The bind file names a node the document does not have. |
| `unknown_slot:<id>-><slot>` | The slot does not exist in the generated plan. |
| `duplicate_slot:<slot>` | Two existing nodes resolve to one slot. |
| `no_nearest:<id>` | No unbound approach or filler slot is left to take. |
| `anchor_mismatch:<slot>` | The existing anchor is bound to something other than `central_plaza`. |
| `unbound_protected:<id>` | A protected node has no binding. |

**The emitted document.** A bound node keeps its id, `key`, `desc`,
`typeclass` and `scene_archetype`. Its position and `prototype_parent` come
from the plan, and every road and wilderness gate that named it follows the
keep. An unbound slot keeps its generated id; when that id collides with a
final id it takes the first free `_2`, `_3`, … suffix, recorded in
`renamed_slots`. An existing node that is neither bound nor protected is
dropped and listed in `dropped`. `options`, `exit_prototype` and `city_gate`
come from the existing document; nodes and roads follow plan order. The write
uses the parsed retained tree, so the file's header comments survive.

**Worked synthetic example.** The test workspace has `synthetic_town` bound to
`synthetic_place`, with the anchor `gate`, the node `yard`, an interior doorway
on `yard` and a district landmark on `yard`. The plan has 28 slots. The
bindings above make `gate` the anchor slot and resolve `yard` to the closest
unbound approach or filler slot; `gate` and `yard` keep their names and
descriptions, and the interior doorway and district landmark still resolve.
A third existing node named by nothing is dropped and appears in `dropped`.
Deleting the reference index protects that node too, so the same binding then
fails with `unbound_protected:<node>` until it is bound.

## Prose pass

Agent writers follow these rules. They are human-reviewed, never tested.

- Write in Traditional Chinese for Taiwan readers, with full-width punctuation. Follow `.agents/skills/chinese-content-writing-guideline`. The setting is JRPG sword and magic. Never use 武俠 vocabulary.
- `key` is 2–8 characters and unique within the map. It names the place a traveller stands in, such as 南門, 河港碼頭 or 鐵砧巷. It does not repeat the settlement's name.
- `desc` is 1–3 sentences and 40–140 characters. It must include one concrete site cue taken from the brief, for example the river side, the uphill direction, the gate's road toward a named neighbour, or the market where approach roads meet. The settlement's `display_name_zh` may appear at most once.
- Write in-world only. Never mention a command, a game mechanic, a UI element, coordinates or an id.
- Follow the archetype's place matrix in `docs/lore/settlement-locations.md`:
  - a beast settlement has no academy, alchemist or church temple; it has a tribal hall and an ancestral altar;
  - only a port has a sea quay;
  - shops stay narrative mentions, because interiors are out of scope.
- For a bound node that already has prose, leave it untouched unless the brief shows that its site cue is now false. An example is a riverbank description on a node that moved away from the river. In that case rewrite only the false clause.

`brief` prints the material those rules need: the settlement's display name,
kind, nation, population, geographic constraint, class, morphology, water
within the generator's reach, uphill bearing, the nearest national neighbours,
and one row per node with its id, current key, role, bearing and distance from
the anchor, whether its description is empty, and its gate return direction.
The role is `anchor`, `gate`, `crossing`, `approach`, `filler`, a catalogue slot
id, or `authored`. Nothing is written.

## Human review

These qualities are reviewed by a person against this page, not tested:

- Does a two-cell town and a thirteen-cell capital look right on the continent
  capture?
- Do the walking times between the gates and the plaza feel right for the tier?
- Is the 150 inhabitants per hectare anchor acceptable for this setting?
- Do the loop ratios produce streets that feel connected rather than maze-like?
- Does every identifier with a water-edge word belong at the water, and every
  gate's outward bearing match the direction a traveller actually approaches
  from?
- Does the layout read as grown, not gridded?
- Do the approach streets converge on the plaza?
- Is the quay on the water side, the temple uphill and the crafts downstream?
- Are the gates plausible toward their neighbours?
- Does the prose read as in-world Traditional Chinese in the settlement's
  register, and does it fit the settlement's archetype and lore?
- After a replace moves a node, does every description whose site cue changed
  still tell the truth?

## Settlement-sensitive test modules

These are the test modules to rerun after any settlement data change. Later
changes reference this section instead of an archived task list. The set was
established by matching
`capital_altoria|south_gate|east_gate|central_plaza|SETTLEMENT_GRAPHS|WILDERNESS_ENTRY_REGISTRY|ANCHOR_PLACEMENT_REGISTRY`,
across the authored-data tree, with browser tests excluded. A module that uses
`central_plaza` or `south_gate` only as a synthetic generator slot constant
does not read authored settlement data and is not a data pin.

```console
commands.tests.test_localized.test_xyz_grid_and_help tests.test_map_core_contract typeclasses.tests.test_exit_movement_cost typeclasses.tests.test_exits typeclasses.tests.test_map_discovery typeclasses.tests.test_npc_dialogue web.webclient.actions.tests.test_exploration_actions.test_move_and_look web.webclient.actions.tests.test_node_ids web.webclient.actions.tests.test_travel_actions web.webclient.presentation.tests.test_area_map web.webclient.presentation.tests.test_exploration_panel.test_presenter web.webclient.presentation.tests.test_exploration_panel.test_wilderness_and_npc_titles web.webclient.presentation.tests.test_local_map.test_gate_capacity web.webclient.presentation.tests.test_local_map.test_gateway_resolution web.webclient.presentation.tests.test_local_map.test_grid_gateways web.webclient.presentation.tests.test_local_map.test_grid_helpers web.webclient.presentation.tests.test_local_map.test_per_gate_footprint web.webclient.presentation.tests.test_local_map.test_presenter web.webclient.presentation.tests.test_local_map.test_wilderness web.webclient.presentation.tests.test_map_quest_destinations web.webclient.presentation.tests.test_world_map world.lore.tests.test_anchor_placement world.lore.tests.test_map_district_content world.lore.tests.test_nations world.lore.tests.test_settlements world.lore.tests.test_sync world.lore.tests.test_wilderness_entry world.maps.tests.test_altoria_capital world.maps.tests.test_bootstrap world.maps.tests.test_city_movement_cost world.maps.tests.test_city_walkthrough world.maps.tests.test_city_wilderness_roundtrip world.maps.tests.test_editor_final_yaml_adoption world.maps.tests.test_geography_source world.maps.tests.test_limbo_room world.maps.tests.test_movement_roundtrip world.maps.tests.test_runtime_adoption world.maps.tests.test_settlement_reload world.maps.tests.test_sparse_graph world.maps.tests.test_static_map_references world.maps.tests.test_village_ciaran world.maps.tests.test_wilderness_destination world.maps.tests.test_wilderness_geography_contract world.maps.tests.test_wilderness_population world.maps.tests.test_wilderness_provider world.quests.tests.test_compile_blueprint world.quests.tests.test_compile_offline world.quests.tests.test_compile_registration world.quests.tests.test_definitions world.quests.tests.test_encounter_activation world.quests.tests.test_encounter_dispatch world.quests.tests.test_generated_dialogue_scenes world.quests.tests.test_package_proposal world.quests.tests.test_quests_observability world.quests.tests.test_room_observation world.quests.tests.test_scene_builder_offline world.quests.tests.test_scene_smoke world.quests.tests.test_story_dialogue world.quests.tests.test_story_effects world.rules.tests.test_dialogue_refresh_lifecycle world.rules.tests.test_guild_config.test_price_scaling world.rules.tests.test_guild_config.test_service_host_roster world.rules.tests.test_map_knowledge_integration world.rules.tests.test_movement world.rules.tests.test_movement_settlement world.rules.tests.test_party_follow world.rules.tests.test_party_follow_possession world.rules.tests.test_party_time_settlement world.rules.tests.test_sight world.rules.tests.test_travel_plan
```

The `tests.` module runs under `uv run --locked python -m unittest`. All others
run under `evennia test --settings settings.py`.

`world.maps.tests.test_editor_final_yaml_adoption` runs with
`--settings test_settings.py` and an env file that contains `MUD_TEST_SETTINGS=1`.

### Residual pin rule

> A failure is a residual pin when the module passes on the pre-change tree (`git stash`, rerun, `git stash pop`) and the cause is a copied settlement value: a literal coordinate, count, duration, node key, cell, roster or gate direction. To fix it:
> - rewrite only that assertion;
> - derive the expected value from `world.maps.map_data.current().settlements[...]`, `world.maps.geography.current().locations` or `elosern_map_core.authoring.gate_approach_cell`, never from a literal;
> - keep the module's `@covers_requirement` IDs and its `Data-contract test:` docstring line;
> - for durations, assert that the charged tick delta `d` satisfies `(d - 1) * 1.25 < metres <= d * 1.25`, where `metres` is the authored polyline length. Never recompute seconds.
>
> Any other failure stops the change.
