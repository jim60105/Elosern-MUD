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

- Only `area_map` and `world_map` may register with `on_demand=True`, and both
  are registered in production.
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
`{"scope": "area" | "world"}`; any other key or value is a `malformed_payload`
rejection, and the presenter never runs. The adapter changes no location, clock,
knowledge or quest state. It names only the requested map in `affected_panels`, so the
dispatcher publishes only that panel, plus the dialogue panel the coordinator
always adds in dialogue mode, through the delivery rules below. The command
echo declares it a silent presentation control. Nothing pushes a map after a
move: the drawer re-requests its active scope.

## The `travel.plan` query

`travel.plan` is the browser's bounded route preview
(`web/webclient/actions/travel_actions.py`, owner
`world/rules/travel_plan.py`). It is a read-only action, not a panel: the
adapter returns one private correlated result (`no_presentation`) and never
re-publishes a map, a status panel or the narrative. Only the current
wilderness exploration actor is admitted; any other location keeps the
existing `not_exploring` refusal.

The payload is exactly
`{"destination": {"x": int, "y": int}, "pace": "cautious" | "standard" | "forced", "stop_at_night": boolean}`.
Any other key, a boolean or non-integer coordinate outside the safe-integer
range, an unknown pace and a non-boolean switch are `malformed_payload`
rejections and the adapter never runs.

Success `data` is exactly:

```json
{
  "origin": {"x": 0, "y": 0},
  "destination": {"x": 0, "y": 0},
  "steps": [{"cell": {"x": 0, "y": 0}, "seconds": 0, "fatigue_stage": "normal"}],
  "total_seconds": 0,
  "nightfall_index": null,
  "stop_index": null,
  "stop_reason": "destination_reached"
}
```

- `steps` holds at most 60 admitted steps; `seconds` is the non-negative
  integer the step would charge (zero for a flight-waived step) and
  `fatigue_stage` is the worst canonical stage among present travellers after
  the step.
- `nightfall_index`, `stop_index` and `stop_reason` are zero-based and
  nullable on an empty plan; `total_seconds` sums the steps through
  `stop_index`. `stop_reason` is one of `member_asleep`, `preflight_refused`,
  `pace_threshold`, `nightfall`, `destination_reached`.

Domain refusals are exactly `plan_destination_outside_window`,
`plan_destination_unrevealed`, `plan_unreachable`, `plan_too_long` and
`plan_party_cannot_travel`. An unexpected read or planning failure is logged
(`travel_plan_failed`) and answered as `plan_unreachable`; nothing raises to
the client. The query writes no location, clock, knowledge, reserve, quest or
party state and never creates the world clock.

Routing is deterministic: A* with a zero heuristic (Dijkstra) over the
revealed cells of the inclusive current±20 window clipped to the frame, eight
neighbours in `n, ne, e, se, s, sw, w, nw` order through the canonical
`wilderness_neighbor` rule (both crossed orthogonals passable *and* revealed),
registered gateway directions excluded (execution diverts them into their grid
room first) and `(cost, steps, y, x)` heap ties. Candidate edges use
`travel_cost.wilderness_step_weight`: the canonical `wilderness_step_cost`
duration with the snapshot's reserves frozen, or -- only when that initial
preflight refuses -- the pure distance/terrain seconds at the frozen party
speed. That weight is never authorization: the sequential replay re-runs the
canonical preflight per step, carries the predicted reserves/postures through
the pure fatigue prediction over each step's rounded charged seconds, and stops
at the design's pace, nightfall, refusal and exact-zero-sleep boundaries.
The whole route is never rounded as one interval.

Travel-plan benchmark (wilderness-travel-planning): a synthetic knowledge
record of 20,000 wilderness visits, one warmed snapshot+plan call excluded
from the samples, then 20 timed snapshot+plan samples: median 85 ms on the
development machine (Intel Core i7-13700, 24 threads, Linux 7.2 / Fedora 44,
Python 3.13.14, SQLite test database), within the 100 ms budget. Run it with
`MUD_TRAVEL_PLAN_BENCHMARK=1` on
`world.rules.tests.test_travel_plan.TravelPlanBenchmarkTests.test_warmed_plan_with_twenty_thousand_visits_is_within_one_hundred_ms`;
the default module run skips only the timing and still covers the same
snapshot, routing and prediction mechanisms.

## The `explore.move` walk context and interrupt result

`explore.move` admits exactly two request shapes: the original
`{exit_ref, current_node}` and that plus
`walk: {"pace": "cautious" | "standard" | "forced", "stop_at_night": boolean}`
(`web/webclient/actions/exploration_actions.py::validate_move_payload`). Any
other key at either level, an unknown pace, a non-boolean switch, a non-object
walk or a missing nested field is `malformed_payload`; the exit/current-node
admission, the stale-location guard, the traversal and the charge are identical
in both forms. The server stores no walking state between requests: the walk
context qualifies exactly the one step it accompanies.

Success is a canonical-coordinate change. A traversal whose canonical location
node is unchanged rejects `move_failed` whatever the room object's identity,
while a pooled wilderness `TerrainRoom` reused at another cell succeeds because
its coordinate node moved.

A successful **wilderness** step (`wild:` destination node) carries one extra
success `data` field:

```json
{"interrupts": ["landmark_reached", "district_lit", "landmark_sighted"]}
```

The list is ordered and duplicate-free: `landmark_reached`, `district_lit`,
`landmark_sighted`, `hostile_in_sight`, `pace_threshold`, `nightfall`,
`member_asleep`. An empty list is legal. The flags compare immutable facts of
the committed step (`world/rules/travel_interrupts.py`):

- `landmark_reached` -- the party stands on a district's exact canonical
  landmark cell (a repeat visit still raises it).
- `district_lit` -- the lit-district set grew across the step.
- `landmark_sighted` -- a distant sight source's internal key is visible after
  the step and was not visible before it.
- `hostile_in_sight` -- a live hostile population-view observation key entered
  the ground disc (the stable prospective/materialized slot key never raises a
  false change).
- `pace_threshold` (walk only) -- a traveller is at or beyond the cautious or
  standard threshold after the step, mirroring `travel.plan`'s first-legal-step
  stop; `forced` has no threshold.
- `nightfall` (`walk.stop_at_night` only) -- a positive charged interval
  crossed a non-night -> night hour boundary; a flight-waived zero-charge step
  cannot cross one.
- `member_asleep` -- a traveller observed awake before became voluntarily or
  forced asleep during the step.

Without `walk` the natural flags still apply and the pace/night flags never
raise. A refused, stale, failed or rolled-back step carries no `data` slot and
keeps its existing code and message, and a non-wilderness success keeps its
exact previous shape. The interrupt result is released through
`on_publication_commit` under the step's captured publication group, so a
caller-owned transaction that rolls back publishes nothing. A capture or
comparison failure logs `travel_interrupts_failed` (`char`, `tick`, `step`) and
answers an otherwise successful step with an empty list; it never fails the
movement.

## The `area_map` publisher

`web/webclient/presentation/area_map.py` builds the panel from canonical data
only. For every graph layer it reveals the visited nodes of the current map
plus their one-step frontier: known = visited ∪ adjacent(visited). A road is
emitted only when both ends are known and at least one end is visited, so a
road between two seen nodes is never sent. Visits on other maps are ignored,
and the current node always counts as visited. Move actions appear only on
the current node's traversable exits, which are resolved by the minimap
helpers.

For settlement graphs, the discovered document's node keys use stable English slugs such as
`south_gate` and `quay`, while the prototype's Chinese `key` supplies the
display label（南門、碼頭埠）. Panel node IDs use the canonical coordinate-based
`grid:<map>:<x>:<y>` grammar. These identities and labels serve separate roles;
the settlement document owns the node and road set without a fixed panel-level count.

## The `world_map` publisher and discovery narrative

`world_map.py` filters every response using the requesting actor's current
visited record. `world_map_geometry.py` caches common geography and static
district geometry without any player state. Final payloads are never cached.
Unlit districts carry a stable nonsemantic wire ID, `lit: false`, and their
outline only. Lighting derives from exact canonical landmark membership.
Ordinary places appear in lit districts or after a visit; elven villages and
dungeons always require an actual visit. Visited places also have an independent
layer, so a hidden place remains represented before its district lights.

Terrain washes are unions of canonical classifier samples on the 5 km display
raster. Rivers and the ridge are clipped to district ownership. Authored public
settlement roads use the canonical local-to-world transform; no overland road
network is fabricated. The deep forest can list both permitted nations without
drawing a national border inside it. Wilderness positions use their cell centre,
grid positions use their canonical world transform, and coordinate-free interiors
use a registered enclosing place or instance origin. Unresolved interiors report
the declared unavailable panel without invented coordinates.

The trail encodes unique visited wilderness cells in sorted row runs. Through
20,000 cells it uses 1 km indices. Larger histories deduplicate floor-divided
5 km indices. The 1 km run cap stays 20,000; the finite 540 by 540 coarse grid
allows 145,800 separated runs. No raw visits, landmark node IDs or district
registry keys appear as alternate trail metadata.

Accepted commissions use the shared canonical destination resolver. Unknown
district destinations are rounded to a 50 km grid before serialization, with
ties toward positive infinity and `approximate: true`. The wire marker whitelist
contains no canonical node identity, exact-derived distance or bearing.

Only explicit exit traversals opt into the shared committed movement narrative.
The settlement captures pre-arrival landmark membership, invokes the unchanged
knowledge writer through the existing completion helper, then confirms the
exact destination node exists after settlement. The single movement message
appends `已探明：<district>` on first arrival. Corrupt knowledge or a swallowed
knowledge write failure cannot announce discovery. Delivery runs after commit;
outer rollbacks discard it, and message-delivery failures log without compensating
committed movement. Nested NPC relocations, direct teleports, reads and reconnects
do not produce discovery.

Knowledge confirmation reads the persisted Attribute value with a values query
and reconciles its in-memory cache before using the unchanged parser. Evennia
assigns a cached Attribute value before saving, so a second cached parse alone
cannot establish persistence after a swallowed save failure. The world presenter
uses the same read boundary and cannot light a district from that dirty cache.
Missing instance origins are read directly from stored Attributes, avoiding the
autocreating `origin_room` descriptor during a read-only request.

## Area publisher layer details

| Layer | Graph and identity | Labels and gateways |
| --- | --- | --- |
| `grid` | The settlement's declared sparse graph (the live XYMap for a builder map), never rooms spawned on demand. Roads count in both directions. `x`/`y` are the node's integer metres. | The authored street name, also for seen nodes (the minimap also names them). A registered gate room carries `{leads_to: <wilderness region>}`. Wilderness gate exits are not grid nodes. |
| `instance`, `interior` | The connected rooms of the current family (`InstanceRoom`, or a plain `Room`), walked through exits in both directions. `map_id` is `instance:<lowest dbref>` or `room:<lowest dbref>`, which does not depend on where the player stands or what they know. The walk stops at 4,096 rooms. | A seen room is `未探索` and never shows its name or its exits. An exit from a visited room into another family is one gateway node, `room:<dbref>` with `{leads_to: <room name>}`, and is never traversed further. |
| `wilderness` | Schema 2 (wilderness-area-map-reveal): the 41 × 41 window centred on the player (`window.min_x/min_y` = current − 20, negative near the frame edge). Terrain is published as run-length rows only for revealed cells (permanent reveal, an actual visit, or the current cell); everything else, including out-of-frame positions, is an exact unknown run. Nodes are sparse: the current cell, every actually visited cell (`visited: true`), and revealed cells that carry a legal step or disclosed location metadata. `x`/`y` are cell-centre kilometres. | The region name, or the settlement name for a disclosed gate's approach cell (gateway `null`, as on the minimap). A revealed neighbour step that resolves to a disclosed grid gate room replaces that cell with the room, carrying `{leads_to: <settlement>}`; a hidden entry needs its gate room's visit. `district_name` comes from the frozen district partition. |

Quest markers come from `map_quest_destinations`, with tracking flags taken
from the same quest-log read. A marker carries the node identity when the
destination is on this settlement, inside the presented wilderness window, or
inside the displayed instance/interior room component (including an accepted
commission's bound `InstanceRoom` beyond the known frontier). That identity may
point into fog, but no fogged node, label or exit is added to `nodes`.
Otherwise the marker carries a bearing (clockwise from north) and a distance
in kilometres from the player's world cell, rounded to 0.1. A marker is
omitted when the player's world cell is unknown, as in an ordinary interior.
Tracked markers come first, up to 32.

## Wilderness disclosure (`local_map` and the exploration move rows)

One server policy, `world/rules/wilderness_disclosure.py`, decides which
wilderness facts a publisher may emit; every wilderness surface reads it, so no
two surfaces can disagree about what one observer knows.

- **Permanent reveal.** A `wild:` destination is disclosed only when
  `world.rules.map_knowledge.revealed_in_bounds` reveals its cell (a lit
  district, or the stored sight disc of a visit). Wilderness adjacency alone
  grants nothing: in a radius-0 woodland night the minimap draws only the
  current cell.
- **Hidden entries need an actual visit.** Elven villages and dungeons publish
  no name or canonical identity until the character has visited the gateway's
  own gate room, even when the surrounding district is lit. Until then the
  gateway node, its label, its `gateway` metadata and its edge are omitted
  entirely; a revealed cell that merely touches such a gateway keeps its
  ordinary region name.
- **Current cell stays current.** `current_node` is always emitted with its
  region label, and every other field set, bound and edge rule is unchanged.

The exploration panel (`webclient-exploration-menu`, schema version 6) applies
the same decision to its `move` rows. A wilderness direction whose destination
is withheld keeps its row — the real Exit's opaque `exit_ref` and its
enabled/lock state are existing control facts — but publishes
`destination: null` and the server's generic direction word (`north`,
`northeast`, ...) as its label. No terrain, settlement, coordinate or target
identity reaches the row, `disabled_reason` never carries the disclosure
decision, and every non-wilderness row keeps a canonical non-null destination.
The compass therefore aims such a direction by its word, submits the unchanged
`{exit_ref, current_node}` payload, and highlights no minimap node; the
dialogue screen's exit list reads the same rows.

The wilderness `area_map` applies the same policy over its whole window: no
terrain, label, identity or entity is published for an unrevealed cell, a
revealed cell that was never walked has no node (absence means remembered
but not visited), and a hidden entry's identity needs the gate room's visit
even in lit terrain. Its reads are bounded: the presenter takes one
request-scoped `map_knowledge.read_snapshot` (one envelope validation) and
decodes only the chunks the window plus the reveal reach needs and the
district landmarks' own chunks; it never parses the whole record.

A graph above the area node/edge ceilings, a wilderness window above its
node, entity or sighting caps, or a schema-valid body above the logical byte
ceiling, becomes the `map_unavailable` panel. The publisher logs
`area_map_over_bound` and never truncates the graph.

## Logical wire forms (`area_map` schema version 2, `world_map` schema version 1)

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
| `wilderness` | `"elosern"`; `{key: "elosern", unit: "km"}` | `{id, label, x, y, visibility, visited, gateway, action}`, cell-centre kilometres; at most 1,681 nodes (41 × 41); a `wild:` node's position is its own cell and lies on a revealed cell inside the window; a non-`wild:` node must be a gateway on a revealed cell one step from the current cell; the current node must be visited |

`visibility` is `current`, `visited` or `seen`. A wilderness payload adds
`district_name`, `cell_km` (positive, at most 1000) and:

- `window`: exactly `{min_x, min_y, width: 41, height: 41}`, centred on the
  current cell.
- `rows`: exactly 41 rows, south to north; each row is 1..41 runs west to
  east whose positive integer lengths sum to 41, and two adjacent runs with
  equal facts are always merged. An unknown run is exactly
  `{length, kind: "unknown"}`. A revealed run is exactly
  `{length, kind: "terrain", terrain, passable, band, tier, road, ford}`:
  `terrain` is one of `open_ground`, `hills`, `mountain`, `woodland` (the
  sight rulebook rows), `water`, `ridge`, `sea`, `settlement`; `band` is
  0..15, `tier` 0..3, and the three flags are booleans. Blocked, water and
  footprint terrain stays present with `passable: false`; a hidden anchor's
  footprint keeps its underlying terrain class. `road` is always `false`
  (no wilderness road exists in the published geography or pricing).
- `light_phase` (`day`, `dusk`, `night`, `dawn`) and `ground_radius` (0..8).
- `entities`: at most 4,096 exact `{id, cell: {x, y}, kind, hostile, label}`
  with a 16-hex-digit keyed, non-semantic `id`, `kind` `hostile`, `npc` or
  `character`, standing on a revealed cell inside the current ground disc
  (`dx² + dy² ≤ (r + 0.5)²`). Only the current disc is published; remembered
  ground carries no entity.
- `sightings`: at most 256 exact `{bearing, distance_km, silhouette_zh,
  name}`: one of the sixteen Traditional Chinese compass words, a distance
  rounded to a multiple of 5 km, the silhouette, and the landmark name only
  when its district is lit (else `null`). No source cell or key is sent. Each quest marker is
`{id, title, tracked, destination}`, where `destination` is exactly
`{kind: "node", node_id}` or `{kind: "bearing", bearing_deg, distance_km}`,
with the bearing in `[0, 360)` and the distance at least 0. A node destination
need not be a presented node, since a marker into an unknown branch carries
only its identity.

The client renderer is `web/webclient-app/components/AreaMapView.vue`
(render-area-map-view), backed by `web/webclient-app/lib/area_map_view.js`.
It draws only the validated body. `grid` nodes are projected from their
metres at one uniform scale. `instance` and `interior` rooms reuse the
minimap's radial placement and are labelled `示意圖 · 不依實際距離`.
`wilderness` rows decode into ephemeral display cells over a fog wash
(`decodeWindow`): a cell with a visited node draws as walked, a revealed cell
without one is dimmed as remembered. The live-sight ring uses the server's
`ground_radius`, entities draw at their cells and sightings sit on the frame
rim along their compass word; the client derives no sight, eligibility,
route or clock. Nodes are placed by each cell-centre kilometre divided by
`cell_km`. Metric views draw a dot field on round world multiples. Its
`格距` caption and the scale bar use one formatter, so they always state the
same distance.

A quest marker is pinned only when its `node_id` is a presented node, and
bearing markers are never pinned. `前往` appears only when a node's `action`
leads to that same node and the node is one edge from `current_node`. It
emits `{exit_ref, destination, current_node}` and never derives a route.

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

The world client renderer is `web/webclient-app/components/WorldMapView.vue`
(render-world-map-view), backed by `web/webclient-app/lib/world_map_view.js`.
It draws only the validated body, in these layers from bottom to top: sea,
land, lit terrain (wash, terrain tints, rivers, ridge and roads of lit
districts), unlit hatching, district borders, national borders, coastline,
trail, approximate-commission circles, places and landmarks, commission
markers, current position, labels, and chrome. World-unit geometry sits
inside one transform with non-scaling strokes, so panning and zooming never
rebuild a path. Labels are screen-space text of at least 16 CSS px times
the UI scale, and a colliding lower-priority label is hidden, never shrunk.

- An unlit district is drawn from its outline only, as hatching with a
  dotted border and the label `未探明`. No landmark, place, nation or name is
  drawn, hit-tested or read out for it.
- Level of detail is inclusive. Nation names show at spans of 400 km and
  wider（大陸 and 國）. Lit district and place names show up to 1,000 km, and
  `未探明` up to 450 km. The trail is a line until the 近郊 view (spans up to
  about 89 km). There it becomes cells of the payload's own
  `resolution_km`, so a downsampled history never implies 1 km precision.
- An approximate commission is a dashed 36 km circle on its supplied 50 km
  grid point, labelled `大致方位`, with no centre pin. Exact commissions are
  pins.
- Selecting a district, place or commission emits its key
  (`district:<id>`, `place:<id>` or `quest:<id>`) and a text reading. A lit
  district lists every nation its `nations` ids resolve to, so the deep
  forest lists both. Keyboard focus stays in a list of real buttons.
- Discovery is session view memory only. A district that was unlit in the
  previous payload and is lit in the next, observed while the view is
  mounted, spreads its ink from its landmark for `--motion-district-reveal`
  (600 ms, 0 ms at reduced or off motion). It announces `已探明：<district>`
  once. The first payload, a repeat, a remount, a new `epoch`, and a payload
  in which a lit district went dark all re-baseline silently.

## The map drawer

`web/webclient-app/components/MapDrawer.vue` (redesign-map-drawer, layout
option A) is the only consumer of both panels. It mounts inside the shared
`OverlayHost` (which keeps the modal dialog, focus trap, opener restoration
and final Escape) and draws one header: the 區域 / 世界 tabs (keys `1` /
`2`), the place caption and the close control. The active view fills the
body; over it float the commission list (top left), the control pill
`－ <stop> ＋ │ ⌖ 全圖 │ ?` with the legend popover (top right), the view's
scale bar (bottom left) and, only while something is selected, the view's
~360 px detail card on the right, which the pill and the edge pointers step
around. `MapEdgePointers.vue` (`lib/map_edge_pointers.js`) draws at most
three off-screen commission pointers, nearest first, and collapses the rest
into `＋n`; the commission list always mirrors every accepted commission as
text. A radial (coordinate-free) area and a commission into fog get text
only, never a pointer.

`composables/use-map-drawer.js` owns the session workflow:

- Opening chooses the scope from the `local_map` layer every time: the
  world tab in the wilderness, the area tab everywhere else.
- Each tab keeps its `view` and `selection` for the session. The memory is
  scoped to the transport generation and presentation epoch; the area half
  is also keyed by `map_id|frame.key|frame.unit` and resets synchronously
  when another map or coordinate frame arrives.
- It sends `map.view {scope}` when the drawer opens, when the tab changes and
  once after each committed move while open (the move's own success result
  with its presentation revision committed). It sends nothing on input, on a
  rejected or earlier move, or while closed. Requests ride the store's single
  in-flight lock: one pending scope waits for it and is dropped on close, on
  disconnect or on a new epoch. `前往` waits while a request is unsettled.
- `前往` forwards the area body's own descriptor and canonical
  `current_node` through the same `explore.move` seam as the minimap.

An area commission outside the current map opens the world tab with an
epoch-bound identity-only selection intent. The drawer clears any unrelated
world selection and resolves that intent against the received world markers,
then the real world view reveals the selected destination beside its detail
card. A new response that omits the destination or declares the map
unavailable retires the intent; an epoch change also retires it. No area
bearing is converted into invented world coordinates.

Keys inside the drawer: arrows pan, `＋`／`－` jump zoom stops, `C`
recentres, `0` shows the whole map, `1`／`2` switch tabs. Escape closes an
open popover, then the selection, then the map. `OverlayHost` stops every
key at the dialog, so background commands never see them.

## The world-map frame allowance

`world_map` is the one panel exempt from the generic frame budget
(transport-world-map-panel). A `ui_update` whose `panels` object holds an
intact `world_map` object (one without `part`) is checked in two pieces:

- The rest of the envelope, with the world map replaced by `null`, passes the
  unchanged generic check. Metadata and every sibling panel keep the
  65,536-byte, 320-item, depth and string bounds. That includes `local_map`,
  `area_map` and the dialogue companion (the dialogue allowance applies only
  to pure dialogue publications without the world-map exemption).
- The world map passes the generic scalar rules, its exact schema and its
  logical ceiling of 2,097,152 canonical bytes.

An intact world-map frame is therefore at most 65,536 + 2,097,152 canonical
bytes. Snapshots, part frames and every other panel take the generic check
only. Both languages use the same routing predicate
(`carries_intact_world_map` / `carriesIntactWorldMap`) and the same check
(`check_world_map_envelope` / `checkWorldMapEnvelope`). The browser copies
the envelope into plain data properties before the generic walk, so a
JSON-parsed `"__proto__"` sibling cannot hide from it. The browser measures
the world map once, by canonically re-serializing the decoded body. The
server measures the validated body. The two counts can differ slightly for
some float spellings: Python writes `1250.0` where JavaScript writes `1250`,
and `1e-05` where JavaScript writes `0.00001`. Publishers emit integral
values as integers, and `tools/world_map_payload.py` does so, which keeps the
two counts equal for the measured payloads. The ceiling check is therefore not byte-exact across
languages, by design; the ceiling's headroom is far larger than any such
difference.

The coordinator publishes a world map as one intact frame whenever the whole
update fits the generic bounds or the allowance. If a companion pushes the
update outside the allowance, the companions ship first and the world map
follows alone at its own revision, still intact. A world map above its
ceiling never reaches the wire: it becomes the `map_unavailable` panel and
logs `map_panel_invalid`. Each intact world-map frame logs the debug event
`world_map_frame_sent` with its canonical byte count.

## Bounded parts

A map update that satisfies the generic frame bounds (65,536 canonical bytes,
320-item lists, depth 12, 2,048-code-point strings), or the world-map
allowance above, ships as one ordinary `ui_update`. Otherwise:

1. Any eager companion panels in the same update, including the dialogue
   panel added in dialogue mode, ship first as an ordinary update.
2. Each `area_map` body travels as one transfer at its own new revision. (A
   validated `world_map` always fits its allowance alone, so it ships as one
   intact frame at its own revision instead.) Every part
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
| `area_map` | 512 graph nodes, 2,048 edges, 32 markers, 393,216 logical bytes (measured); wilderness: 1,681 nodes, 4,096 entities, 256 sightings | `publish-area-map-panel`; wilderness caps `wilderness-area-map-reveal` |
| `world_map` | 2,097,152 logical bytes (measured) plus the per-collection limits in `map_panels.py` | `publish-world-map-panel` |

The owning change replaces the constants in both files together and records
the measurements here.

`area_map` measurements (publish-area-map-panel):

- Shipped settlement membership and road counts follow their authored modules.
  Payload size depends on that data and the player's explored set; it is not
  a fixed settlement contract.
- The wilderness window (schema 2) is 41 × 41 cells. Its edge list is at
  most the eight neighbour steps. Its RLE rows hold at most 1,681 runs, and
  a dense window with every cell visited stays well under the byte ceiling;
  larger bodies travel as bounded parts like any map.
- Wilderness benchmark (wilderness-area-map-reveal): a synthetic record of
  20,000 wilderness visits (a dense block around the window plus a frame-wide
  scatter), warmed presenter, 20 timed samples with setup excluded: median
  23 ms on the development machine (Intel Core i7-13700, 24 threads, Linux
  7.2 / Fedora 44, Python 3.13.14, SQLite test database),
  within the 50 ms budget. Run it with `MUD_AREA_MAP_BENCHMARK=1` on
  `test_area_map.WildernessAreaTests.test_warmed_window_with_twenty_thousand_visits_is_within_fifty_ms`;
  the chunk-bounded read assertion runs by default.
- A synthetic grid at the new ceilings (512 nodes with 16-character labels,
  2,048 roads and 32 full-length markers) is 250,184 bytes, or 274,760 bytes
  with 32-character labels. It travels as bounded parts and round-trips
  intact. The 393,216-byte ceiling covers both with room to spare.
- The graph node ceiling leaves room for settlements and builder interiors;
  the wilderness window has its own exact caps. Every unrelated panel keeps its generic budget. That
includes `local_map` and its 65,536-byte envelope.

`world_map` measurements (publish-world-map-panel). The measurement tool uses
the production assembly, geometry caches, privacy filter and trail encoder.
It supplies exploration histories and full-length marker records without
maintaining a second geometry builder. Run
`uv run --locked python -m tools.world_map_payload` to reproduce the table.

| Case | Canonical bytes |
| --- | --- |
| Common layer only | 1,267 |
| Every district unlit (outlines only) | 195,220 |
| Representative: the 12 districts nearest the Altoria start lit | 213,117 |
| All content, exactly 20,000 wilderness visits at 1 km, full markers | 575,844 |
| All content, maximal separated 5 km coverage across the frame, full markers | 1,535,088 |

The original measurement omitted coarse histories with more than 20,000 runs.
The 2 MiB world-only ceiling covers the measured large history with more than
25% headroom. Other panel limits stay unchanged. On the socket the portal writes
`json.dumps` with `ensure_ascii=True`, so each CJK code point costs six bytes;
the managed socket test compares server and browser canonical UTF-8 digests.

Transport limits on the delivery path:

- Server to portal (AMP): Twisted caps one AMP value at 65,535 bytes.
  Evennia's `Compressed` argument splits the pickled message into chunks of
  that size and compresses each one with zlib at level 9. JSON compresses
  far below the cap.
- Portal to browser (WebSocket): autobahn 20.12.3 `WebSocketServerFactory`
  defaults to `maxFramePayloadSize = 0`, `maxMessagePayloadSize = 0` and
  `autoFragmentSize = 0`, which means no limit and one frame per message.
  Evennia's portal factory overrides none of them.
- The repository ships no reverse proxy (`compose.yaml` publishes port 4002
  directly). A deployment that adds one must allow messages of at least the
  frame bound above.

Decision: the world map travels intact, and parts are not used for it. The
managed browser class
`web.tests.browser.test_map_transport.WorldMapTransportTests` publishes the
representative and the worst-case payload through the live coordinator,
Evennia's AMP, the portal and the WebSocket. For each payload it asserts
three things:

- exactly one `ui_update` WebSocket frame carried the world map, with no
  `part`, and that frame was larger than 65,536 bytes;
- the production browser store adopted it into `state.maps`;
- the canonical UTF-8 bytes of the adopted map have the same length and
  SHA-256 as the server's validated body.

The part codec stays available, unchanged, for `area_map`.
