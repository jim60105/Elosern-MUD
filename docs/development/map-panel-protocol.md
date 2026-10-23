# On-demand map panel protocol

The world-map drawer (`docs/superpowers/specs/2026-10-22-world-map-drawer-design.md`
§5) reads two on-demand panels, `area_map` and `world_map`. This page records
their fixed wire forms, how they are stored, and how large bodies travel. The
contract was introduced by the OpenSpec change `define-map-panel-protocol`.

| Concern | Server | Browser |
| --- | --- | --- |
| Logical schemas and bounds | `web/webclient/presentation/map_panels.py` | `web/static/webclient/js/elosern/protocol/panels/map_panels.js` |
| Part codec | `web/webclient/presentation/map_parts.py` | `web/static/webclient/js/elosern/protocol/map_parts.js` |
| On-demand publication and storage | `registry.py` (`PresenterSpec.on_demand`), `coordinator.py` | `protocol/envelope.js`, `protocol/store.js` (`state.maps`) |

A bidirectional parity test
(`web.webclient.presentation.tests.test_map_panel_protocol`) pins every
mirrored constant and decides the same wire text in both languages.

## On-demand semantics

- Only `area_map` and `world_map` may register with `on_demand=True`, and they
  must. `publish-area-map-panel` registers `area_map`; `world_map` stays absent
  from the production registry until `publish-world-map-panel` registers it.
- A full snapshot renders eager panels only. A map presenter runs only when a
  caller names its panel in an update, which is the `map.view` action.
  Movement (`explore.move` publishes a full snapshot) and text-command
  refreshes never name map panels, so they never recompute or push a map.
- The browser keeps maps in `state.maps`, separate from `state.panels`. A
  same-epoch snapshot or eager update leaves the maps unchanged. A new
  transport generation, the establishing snapshot of a new epoch, and a
  `no_puppet` detachment clear both stores and any unfinished transfer.
- A `ui_snapshot` that names a map panel is rejected.

## The `map.view` request

`map.view` is an allowlisted read in the production action registry
(`web/webclient/actions/map_actions.py`). Its payload is exactly
`{"scope": "area"}`; any other key or value is a `malformed_payload`
rejection, and the presenter never runs. `publish-world-map-panel` adds
`"world"` to the same exact union. The adapter changes no location, clock,
knowledge or quest state. It returns `affected_panels: ("area_map",)`, so the
dispatcher publishes only that panel, plus the dialogue panel the coordinator
always adds in dialogue mode, through the delivery rules below. The command
echo declares it a silent presentation control. Nothing pushes a map after a
move: the drawer re-requests its active scope.

## The `area_map` publisher

`web/webclient/presentation/area_map.py` builds the panel from canonical data
only. For every graph layer it reveals the visited nodes of the current map
plus their one-step frontier: known = visited ∪ adjacent(visited). A road is
emitted only when both ends are known and at least one end is visited, so a
road between two seen nodes is never sent. Visits on other maps are ignored,
and the current node always counts as visited. Move actions appear only on
the current node's traversable exits, which are resolved by the minimap
helpers.

| Layer | Graph and identity | Labels and gateways |
| --- | --- | --- |
| `grid` | The settlement's declared sparse graph (the live XYMap for a builder map), never rooms spawned on demand. Roads count in both directions. `x`/`y` are the node's integer metres. | The authored street name, also for seen nodes (the minimap also names them). A registered gate room carries `{leads_to: <wilderness region>}`. Wilderness gate exits are not grid nodes. |
| `instance`, `interior` | The connected rooms of the current family (`InstanceRoom`, or a plain `Room`), walked through exits in both directions. `map_id` is `instance:<lowest dbref>` or `room:<lowest dbref>`, which does not depend on where the player stands or what they know. The walk stops at 4,096 rooms. | A seen room is `未探索` and never shows its name or its exits. An exit from a visited room into another family is one gateway node, `room:<dbref>` with `{leads_to: <room name>}`, and is never traversed further. |
| `wilderness` | The 15 × 15 window centred on the player, clipped to provider-valid ground. `x`/`y` are cell-centre kilometres, and every cell has a `visited` flag. | The region name, or the settlement name for a gate's approach cell (gateway `null`, as on the minimap). A neighbour step that resolves to a grid gate room replaces that cell with the room, carrying `{leads_to: <settlement>}`. `district_name` comes from the frozen district partition. |

Quest markers come from `map_quest_destinations`, with tracking flags taken
from the same quest-log read. A marker carries the node identity when the
destination is on this settlement, or inside the presented wilderness window.
That identity may point into fog, but no fogged node is added to `nodes`.
Otherwise the marker carries a bearing (clockwise from north) and a distance
in kilometres from the player's world cell, rounded to 0.1. A marker is
omitted when the player's world cell is unknown, as in an ordinary interior.
Tracked markers come first, up to 32.

A graph above the area ceilings becomes the `map_unavailable` panel. The
publisher logs `area_map_over_bound` and never truncates the graph.

## Logical wire forms (schema version 1)

Every object below is exact: unknown keys, wrong types, booleans in number
fields and non-finite numbers are rejected. Integer fields accept any JSON
number with an integral value (`3`, `3.0`, `1e2`): JSON cannot tell these
spellings apart and the browser decodes all of them to integers, so the
server normalizes them as well. Text bounds are 256 code points for labels
and names, and 128 code points for titles and the district caption. Text must
not be blank. Node IDs follow the canonical grammar, checked as syntax only:
`grid:<map>:<x>:<y>`, `wild:elosern:<x>:<y>` and `room:<dbref>`, with
non-negative integers that have no leading zeros. Publishers own existence
checks.

### `area_map`

Common fields: `{schema_version, available: true, layer, map_id, frame,
current_node, title, nodes, edges, quest_markers}`. Exactly one node has
`visibility: "current"`, and it equals `current_node`. Node IDs are unique.
Edges `{source, destination}` join two distinct presented nodes and are not
duplicated. `gateway` is `null` or `{leads_to}`. `action` is `null` or
`{kind: "move", exit_ref, destination}`.

| Layer | `map_id` / `frame` | Node fields |
| --- | --- | --- |
| `grid` | the z-map key; `{key: map_id, unit: "m"}` | `{id, label, x, y, visibility, gateway, action}`, integer metres; every node is `grid:<map_id>:…` |
| `instance`, `interior` | the stable instance identity or the enclosing interior root identity; `{key: map_id, unit: "none"}` | `{id, label, visibility, gateway, action}`, no coordinates; every node is `room:…` |
| `wilderness` | `"elosern"`; `{key: "elosern", unit: "km"}` | `{id, label, x, y, visibility, visited, gateway, action}`, cell-centre kilometres; at most 225 nodes (15 × 15); a non-`wild:` node must be a gateway; the current node must be visited |

`visibility` is `current`, `visited` or `seen`. A wilderness payload adds
`district_name` and `cell_km` (positive, at most 1000). Each quest marker is
`{id, title, tracked, destination}`, where `destination` is exactly
`{kind: "node", node_id}` or `{kind: "bearing", bearing_deg, distance_km}`,
with the bearing in `[0, 360)` and the distance at least 0. A node destination
need not be a presented node, since a marker into an unknown branch carries
only its identity.

### `world_map`

`{schema_version, available: true, common, districts, trail, visited_places,
current, quest_markers}`, in continent kilometres with north-positive `y`.

- A point is `[x, y]`. A polyline has at least 2 points. A polygon is closed,
  meaning its first point equals its last, has at least 4 points, and
  encloses a nonzero area.
- **Winding convention:** an outline is a list of closed rings.
  Counter-clockwise rings (positive signed area) are outer boundaries and
  clockwise rings are holes. At least one ring must be outer. Terrain
  `polygons` follow the same rule.
- `common`: `{coastline: polygon, borders: [polyline], nations: [{id, name, x, y}]}`.
- `districts`: discriminated by `lit`. Unlit is exactly `{id, lit: false,
  outline}`. Lit is `{id, lit: true, name, outline, landmark: {name, x, y},
  nations, terrain: [{region, polygons}], rivers, ridge, roads, places}`.
  `nations` names IDs from `common.nations`. A landmark carries no node ID.
- Places and `visited_places` rows: `{id, name, kind, x, y}` with kind
  `capital | settlement | harbour | hidden`.
- `trail`: `{resolution_km: 1 | 5, rows: [[row_index, [[start, length], ...]], ...]}`.
  Rows are strictly increasing and runs are sorted, positive and
  non-overlapping. Everything stays inside the 2700 km frame at that
  resolution (0..2699 at 1 km, 0..539 at 5 km).
- `current`: `{x, y}`.
- Quest markers: `{id, title, tracked, x, y, approximate}`. When `approximate`
  is true, `x` and `y` are integer multiples of 50, and no exact ID, distance
  or bearing field exists.

Either panel may instead be the common unavailable form
`{schema_version, available: false, reason}`.

## Bounded parts

A map update that satisfies the generic frame bounds (65,536 canonical bytes,
320-item lists, depth 12, 2,048-code-point strings) ships as one ordinary
`ui_update`. Otherwise:

1. Any eager companion panels in the same update, including the dialogue
   panel added in dialogue mode, ship first as an ordinary update.
2. Each map body travels as one transfer at its own new revision. Every part
   is a `ui_update` with identical metadata whose `panels` hold only
   `{<map>: {schema_version: 1, available: true, part: {transfer_id, index,
   count, byte_length, chunk}}}`.
3. `chunk` is padded standard base64 of a fixed slice of the canonical UTF-8
   JSON body (sorted keys, no whitespace, non-ASCII kept). Every slice except
   the last is exactly 1,536 bytes, which is 2,048 base64 characters, the
   generic string ceiling. `count = ceil(byte_length / 1536)`. `transfer_id`
   has the epoch form: 22 URL-safe characters. Each frame still passes the
   generic envelope check.

The browser keeps at most one live assembly per map panel. It adopts the body
and the frame metadata (mode, server time, revision) only when all of the
following hold:

- every part arrived;
- the exact byte count decoded;
- the bytes are strict UTF-8 JSON (a BOM is rejected);
- the full logical schema validated;
- the revision is still newer than the committed one.

Partial frames return `{accepted: true, partial: true}` and notify no
subscriber. The store rejects a frame in each of these cases, and nothing
becomes visible:

| Frame | Result |
| --- | --- |
| Not newer than the committed revision | Rejected (`not_newer`). |
| Conflicting metadata or a different chunk for a received index | Discards the assembly. |
| Identical duplicate | Dropped (`duplicate_part`). |
| Frame of a completed or retired transfer | Dropped (`finished_transfer`). |
| Different transfer at the same or a lower revision | Dropped (`superseded_transfer`). |

A different transfer at a higher revision retires the live assembly. Any
committed presentation at or above an assembly's revision frees it. The
logical byte bound is enforced on `byte_length`; the browser never
re-serializes to measure. If a transfer is lost, the next action carries a
stale base revision. The server answers it with a snapshot, which keeps the
last complete maps.

The part rejection reasons are expected under replay and reordering, so they
are not fatal. A transport consumer must not treat `duplicate_part`,
`finished_transfer`, `superseded_transfer`, `conflicting_part`,
`invalid_body` or `not_newer` on a part frame as a protocol error or as a
resync trigger.

The server builds and checks every frame of a parts delivery before it sends
anything or consumes a revision, so an encoding failure never leaves a
half-published update.

A retained map is not invalidated when the player moves. The request owner
(`map.view` and the drawer) re-requests the active scope after each committed
move.

This codec covers map panels only. It is not a general streaming API.

## Bounds ownership

All numeric ceilings are finite and mirrored in both validators:

| Panel | Ceilings | Owner of the measured values |
| --- | --- | --- |
| `area_map` | 512 nodes, 2,048 edges, 32 markers, 393,216 logical bytes (measured) | `publish-area-map-panel` |
| `world_map` | 2,097,152 logical bytes plus the per-collection limits in `map_panels.py` | `transport-world-map-panel` measures the continental payload and the socket path |

The owning change replaces the constants in both files together and records
the measurements here.

`area_map` measurements (publish-area-map-panel):

- The largest shipped settlement is 21 nodes and 26 roads, about 5.1 KB when
  fully explored. The second is 10 nodes and 9 roads, about 2 KB.
- The wilderness window is at most 225 cells. Its edge list is at most the
  eight neighbour steps, so a window usually fits one frame.
- A synthetic grid at the new ceilings (512 nodes with 16-character labels,
  2,048 roads and 32 full-length markers) is 250,184 bytes, or 274,760 bytes
  with 32-character labels. It travels as bounded parts and round-trips
  intact. The 393,216-byte ceiling covers both with room to spare.
- The ceilings leave about 24 times the largest settlement and twice the
  wilderness window for future settlements and builder interiors. Every unrelated panel keeps its generic budget. That
includes `local_map` and its 65,536-byte envelope.
