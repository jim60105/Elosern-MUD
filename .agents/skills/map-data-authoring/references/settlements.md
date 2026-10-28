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
binding:                              # how the local frame sits on the continent
  anchor_cell: {cell_x: 1340, cell_y: 1220}   # MUST equal locations.<location_ref>.cell
  local_anchor_m: {east_m: 220, north_m: 305} # MUST equal the anchor_room node's (x_m, y_m)
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
  origin: {cell_x: 1340, cell_y: 1220}
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

## Nodes

- Every node needs every field. Node coordinates are unique within the map.
- **Exactly one `anchor_room` per settlement**, with `anchor_key:
  <location_ref>`. It is the room that stands on the location's continental
  cell, and `binding.local_anchor_m` must equal its position. If you move the
  anchor node, update `local_anchor_m` with it. Every other node is
  `grid_room` with an empty `anchor_key`.
- Moving a node only changes `x_m`/`y_m`. Its ID, every road direction, the
  gates, interior exteriors and district landmarks all keep pointing at it.
  The road lengths are recomputed from geometry, and nothing stores them.
- The local frame is **metres**, and the game uses a uniform physical scale.
  Road length is the polyline length source → bends → destination, and it
  drives travel time. A move that doubles a road's length doubles its walking
  time.
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

- **The mask runs from south to north.** Cell `(origin_x + column,
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
- To move the settlement on the continent, shift `origin` by the same delta
  as the location cell and `binding.anchor_cell`. The editor's 佔地 tool grows
  the mask with `.` padding (at most 64×64). Hand edits must keep it
  rectangular.

## City gate

`city_gate` is the one-way entry from the character-creation starting room
into this map. `exit_key` is the exit name and `exit_aliases` are synonyms.
It has **no** return label, so do not add one. Only the maps that new players
can start in need it.

## Creating a new local map

1. Make sure the location already exists in `locations.yaml`.
2. Create `content/maps/settlements/<new_map_id>.yaml` with these fields:
   - `version`, `kind`, `id`;
   - `location_ref`;
   - `binding`, with `anchor_cell` set to the location cell;
   - optionally `options` and `exit_prototype`; copying them from
     `village_ciaran` is a sensible default;
   - `nodes`, which must include one `anchor_room` at `local_anchor_m`;
   - `roads`;
   - `wilderness_entry`, usually a point mask at the location cell with one
     gate to the anchor or a gate node;
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

## Editor equivalents

The editor provides these commands:
- `create_settlement`, `set_settlement_field` (`options`, `exit_prototype`);
- `create_node`, `duplicate_node`, `set_node_fields`, `move_nodes`,
  `delete_nodes`;
- `create_road` (with an optional return entry), `set_road`, `delete_road`;
- `insert_bend`, `move_bend`, `remove_bend`;
- entrances: `create_wilderness_gate`, `set_wilderness_gate`,
  `delete_wilderness_gate`, `remove_wilderness_entry`, `set_city_gate`;
- continent tools that write this file: `set_footprint_cell`, `set_binding`.

The editor does not cascade `set_binding` into `locations.yaml`, or the
reverse. When you move a town, update both files yourself.
