# `content/maps/settlements/<map_id>.yaml`

Each document is one local map: a capital or a village. The file stem equals
`id`. Adding a new file adds a map, with no registry or Python import to
update.

## Full shape

```yaml
version: 1
kind: settlement
id: village_ciaran
location_ref: village_ciaran          # the location this map belongs to (the only link)
options:                              # optional
  map_visual_range: 2
  map_mode: nodes
exit_prototype:                       # optional; the exit spawned for every road
  prototype_parent: xyz_exit          # only allowed value
  typeclass: typeclasses.exits.CostedXYZExit   # nullable
nodes:
  village_plaza:                      # node id: stable identity, ^[a-z][a-z0-9_]*$
    x_m: 220                          # integer metres east in the local frame
    y_m: 305                          # integer metres north
    prototype_parent: anchor_room     # grid_room | anchor_room
    key: 村中廣場                      # room name shown in game
    desc: 村裡的空地……                 # zh-TW room prose
    anchor_key: village_ciaran        # required exactly for anchor_room (= location_ref), else empty
    typeclass:                        # nullable Python typeclass path
    scene_archetype: city_street      # nullable; a registered scene archetype
roads:                                # DIRECTED: A→B and B→A are two entries
  - source: village_plaza
    destination: hidden_path
    direction: w                      # n ne e se s sw w nw, authored and never inferred
    bends:                            # optional polyline points, local metres
      - {x_m: 100, y_m: 250}
wilderness_entry:                     # nullable (write the key with an empty value)
  shape:                              # footprint mask rows of '#'/'.'
    - '#'
  offset: {dx: 0, dy: 0}              # signed cell delta from the location cell
  gates:                              # ≥ 1
    - return_direction: n
      destination_node: hidden_path
city_gate:                            # nullable: the one-way entry from the starting room
  node: hidden_path
  exit_key: 隱密小徑
  exit_aliases: [祕徑, 幽徑]
```

`wilderness_entry` and `city_gate` are nullable but **required keys**. Write
`city_gate:` with an empty value when a map has none.

There is no `binding`. The world frame is derived from
`locations[location_ref].cell` and the unique `anchor_room` node, so a location
move carries the whole settlement and no document has to repeat a coordinate.

## Nodes

- Every node needs every field. Node coordinates are unique within the map.
- **Exactly one `anchor_room` per settlement**, with `anchor_key:
  <location_ref>`. It is the room that stands on the location's continental
  cell: the game derives the local frame from its `(x_m, y_m)`. Moving the
  anchor node therefore re-frames the graph — the anchor stays on the location
  cell's centre and every untouched node's world position shifts by the
  negative local delta — while the location and the footprint stay fixed. A
  second `anchor_room` is a structure error, and a missing one is saveable
  work in progress. Every other node is `grid_room` with an empty
  `anchor_key`.
- Moving a node only changes `x_m`/`y_m`. Its ID, every road direction, the
  gates, interior exteriors and district landmarks all keep pointing at it.
  The road lengths are recomputed from geometry, and nothing stores them.
- The local frame is **metres**, and the game uses a uniform physical scale.
  Road length is the polyline length source → bends → destination, and it
  drives travel time. A move that doubles a road's length doubles its walking
  time.
- Both `x_m` and `y_m` of every node are **non-negative**: the authored metre
  pair is the node's grid coordinate on its own map, so a negative one is a
  structure diagnostic. The frame origin itself carries no meaning, so keep the
  graph inside it by re-origining the whole document (every node and road
  bend by the same delta) rather than by changing one node's world position.
- To duplicate a node, copy its ordinary fields under a new ID and a new
  position. Copy no relationships. A copy of an `anchor_room` becomes a
  `grid_room` with an empty `anchor_key`.

## Roads

- A road is directed. A two-way street is **two** entries in this file, and
  the editor's "建立雙向" writes both in one save. The return direction is
  normally the opposite compass point, but it is authored, so keep whatever
  the user specifies.
- Structure rules (the file will not load if any is broken):
  - both endpoints exist;
  - no self-loop;
  - no duplicate ordered `(source, destination)` pair;
  - **no node has two outgoing roads with the same direction**;
  - the direction is one of the eight values.
- `direction` is the exit name that the player types. It is never
  recomputed from positions, so a geometrically odd direction is still valid.
  Do not "fix" one unless asked.
- `bends` are optional integer-metre points in order from source to
  destination. They only change the drawn shape and the length.
- Deleting a road needs no reference index: roads are owned only here.

## Wilderness entry (footprint and gates)

The entry is how the continent-scale wilderness connects to this map.

- **The mask runs from south to north.** The mask origin is
  `locations[location_ref].cell + offset`, and cell `(origin_x + column,
  origin_y + row)` is footprint when `shape[row][column] == '#'`. The **first**
  YAML row is therefore the **southern** edge, and higher rows lie further
  north. Rows must all have the same length and use only `#` and `.`.
- The **anchor cell** of the entry is the bounding-box midpoint of the `#`
  cells, using floor division. Keep it equal to the location cell, so the
  world-map marker and the real entrance coincide.
- **Point shape** (exactly one `#`) is a concealed entry such as a cave or a
  hidden village. It has exactly one gate. A traveller standing on the anchor
  cell and stepping in `return_direction` enters at `destination_node`. The
  neighbour cell in that direction must be walkable wilderness outside every
  footprint.
- **Footprint shape** (several `#`): the `#` cells must be 4-connected and
  walkable, and the anchor must be a `#` cell. A gate's approach cell is found
  by walking from the anchor *opposite* to `return_direction` until you leave
  the footprint. A traveller on that approach cell stepping in
  `return_direction` enters the city. Example: in the capital, `n → south_gate`
  means you approach from the south and walk north into the south gate.
- The game also requires:
  - footprints do not overlap, and do not contain another map's point
    anchor or gate approach;
  - no two gates share an `(approach cell, direction)` pair;
  - each gate uses a distinct destination node;
  - each approach cell is walkable;
  - the last gate cannot be deleted without removing the whole entry.
- To move the settlement on the continent, move the location cell only; the
  mask, its midpoint and every gate approach follow it. To move the mask
  within the settlement, change `offset`. The editor's 佔地 tool takes absolute
  cells, grows the mask with `.` padding (at most 64×64) and saves the
  converted offset. Hand edits must keep it rectangular.

## Terrain fit and size

Two scales meet in this file. The wilderness is a 1 km grid whose cell centres
are `(1000X + 500, 1000Y + 500)` m; the map's `x_m`/`y_m` are integer metres in
the settlement's own frame. The footprint is the settlement's wilderness
occupancy in whole cells, and the street graph's extent is the built-up area in
metres — one area seen at two scales, never a second size authority. Rounding
the footprint up to whole cells absorbs walls, suburbs and gardens; the streets
stay at the built-up size. A 6,000-person town is about 770 m across (a
ten-minute walk); a 600,000-person capital is about 4 km across.

Three read-only commands report on that fit, in the game environment:

```console
uv run --locked python -m tools.settlement_synthesis site <location_id>
uv run --locked python -m tools.settlement_synthesis budget <location_id>
uv run --locked python -m tools.settlement_synthesis lint <map_id>
```

- `site` lists the nearby rivers and sea with distance and bearing, each
  river's downstream bearing, fords, harbour sites, relief and uphill bearing,
  the nearest national settlements and the bearing to the location's capital.
- `budget` gives the built-up area, footprint cells, envelope radius and the
  node, gate and loop targets for the population.
- `lint` checks this file against the terrain: a node in water, a water-edge
  identifier (`quay`, `wharf`, `dock`, `docks`, `pier`, `landing`, `riverbank`,
  `waterfront`) more than 600 m from water, a road crossing water with no
  `bridge`, `ford` or `ferry` endpoint, a node outside a multi-cell footprint,
  an unwalkable gate approach, a gate facing inward, and a road whose authored
  direction drifts from its drawn segment. Words are whole underscore-separated
  tokens, and a ford cell never counts as water. Errors must be fixed; warnings
  are review prompts.

The scale rule, the density assumption with its sources, the tier table and the
human-review checklist are in
[`docs/development/settlement-synthesis.md`](../../../../docs/development/settlement-synthesis.md).

## City gate

`city_gate` is the one-way entry from the character-creation starting room
into this map. `exit_key` is the exit name and `exit_aliases` are synonyms.
It has **no** return label, so do not add one. Only the maps that new players
can start in need it.

## Creating a new local map

For a national settlement, generate it:
`uv run --locked python -m tools.settlement_synthesis generate <location_id> --plan-only`,
then without `--plan-only`; the generator never overwrites, and the prose pass is
described in `settlement-rework-and-prose`'s documentation. The steps below are
the hand-authored path.

1. Make sure the location already exists in `locations.yaml`.
2. Create `content/maps/settlements/<new_map_id>.yaml` with these fields:
   - `version`, `kind`, `id`;
   - `location_ref`;
   - optionally `options` and `exit_prototype`; copying them from
     `village_ciaran` is a sensible default;
   - `nodes`, which must include one `anchor_room`;
   - `roads`;
   - `wilderness_entry`, usually a point mask at offset `(0, 0)` (the location
     cell) with one gate to the anchor or a gate node;
   - `city_gate:`, empty unless asked.
3. A map with no nodes loads, but is diagnosed `empty_graph`. That is saveable
   work in progress and not playable.
4. Run the check script, then regenerate the partition. Every settlement file
   is a partition input.

## Deleting nodes

The editor refuses a node delete while any of these still names the node:
- a road in either direction;
- a wilderness gate;
- the city gate;
- an interior `exterior.node`, in any interior file;
- a district landmark;
- an external incoming reference
  (`incoming_references["settlement_node:<map>:<node>"]`).

Remove those first, as separate deliberate steps. Search the interiors with
`grep -rn "node: <node_id>" content/maps/interiors/`.

## Rework or name an existing local map

`generate` never overwrites a settlement. To rework one, bind every node that
other sources still name, then write its prose with the prose command.

1. Get the brief. It lists each node's id, key, role, bearing and distance from
   the anchor, whether its `desc` is empty, and the settlement's site. It
   writes nothing.

   ```console
   uv run --locked python -m tools.settlement_synthesis brief <map_id>
   ```

2. Write the bind file in the scratchpad, for example
   `{"bindings": {"gate": "central_plaza", "yard": "nearest:central_plaza"}}`.
   A direct value names a plan slot; `nearest:<slot>` takes the closest unbound
   approach or filler slot. `--replace` needs a binding for every protected
   node: an interior `exterior.node`, a district landmark, an incoming
   `settlement_node:<map>:<node>` reference, the city gate and the anchor. With
   no reference index, every existing node is protected. A refused run names
   the problem and writes nothing.

3. Replace the graph. Run it with `--plan-only` first and read the report.

   ```console
   uv run --locked python -m tools.settlement_synthesis generate <location_id> --replace --bind <bind.json> --plan-only
   uv run --locked python -m tools.settlement_synthesis generate <location_id> --replace --bind <bind.json>
   ```

   The command rewrites the document bound to the location, keeps the bound
   ids, keys and descriptions, and reports the bound, dropped and renamed
   slots.

4. Write the prose JSON in the scratchpad as
   `{"<node_id>": {"key": "…", "desc": "…"}}`, following § Prose pass in
   `docs/development/settlement-synthesis.md`. Apply it:

   ```console
   uv run --locked python -m tools.settlement_synthesis prose <map_id> <prose.json>
   ```

   Unknown ids, empty text and fields other than `key` and `desc` are refused
   atomically. Never hand-edit prose into the YAML when the prose command can do
   it. The command keeps the codec, the file's comments and the atomic write.

5. Verify and regenerate. Run the terrain-fit lint, the check script and the
   partition regeneration, in that order.

   ```console
   uv run --locked python -m tools.settlement_synthesis lint <map_id>
   uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py
   uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py
   ```

## Editor equivalents

The editor provides these commands:
- `create_settlement`, `set_settlement_field` (`options`, `exit_prototype`);
- `create_node`, `duplicate_node`, `set_node_fields`, `move_nodes`,
  `delete_nodes`;
- `create_road` (with an optional return entry), `set_road`, `delete_road`;
- `insert_bend`, `move_bend`, `remove_bend`;
- entrances: `create_wilderness_gate`, `set_wilderness_gate`,
  `delete_wilderness_gate`, `remove_wilderness_entry`, `set_city_gate`;
- continent tools that write this file: `set_footprint_cell`.

There is no `set_binding` command: it was removed with the duplicated
authorities. Moving a town is one location edit and nothing else.
