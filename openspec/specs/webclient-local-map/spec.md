## Purpose

The read-only version-1 `local_map` panel payload, the grid/anchor, wilderness, and
instance/interior layer adapters, the visibility states and legend, the bounded serialization the
server and browser validators share, and the minimap renderer that replaces the desktop-shell
placeholder.

## Requirements

### Requirement: local_map is a read-only version-1 presentation panel
The production presentation registry SHALL register panel name `local_map` at schema version 1. Its
available payload SHALL contain exactly `schema_version`, `available`, `layer`, `current_node`,
`title`, `nodes`, `edges`, and `legend`; `available` SHALL be true. `layer` SHALL be one of `grid`,
`wilderness`, `instance`, or `interior`; `current_node` SHALL be a canonical node ID; `title` SHALL be
a bounded localized map title. `nodes` SHALL be a bounded list where each node contains exactly
`id`, `label`, `x`, `y`, `visibility`, `current`, `anchor`, `landmark`, and nullable `action`; node
`x`/`y` are renderer-local presentation geometry, not canonical world coordinates. `edges` SHALL be a
bounded list where each edge contains exactly `source`, `destination`, `label`, `known`, and
`traversable`. `legend` SHALL be a bounded list of text label entries. The presenter SHALL build the
payload only from canonical room/map/knowledge data, SHALL emit no live object or filesystem
reference, SHALL NOT mutate knowledge, traits, clock, or location, and SHALL use the registered common
unavailable form when the current room cannot be represented.

The exact bounds, shared unchanged by the server and client validators, SHALL be: at most 64 `nodes`,
at most 128 `edges`, at most 16 `legend` entries, node/edge/legend strings of at most 256 Unicode code
points, `title` of at most 128 code points, node IDs of at most 128 characters, renderer-local `x`/`y`
integers within `-1024..1024`, `known`/`traversable`/`current`/`anchor`/`landmark` as booleans,
`visibility` as one of `current`, `visible_unvisited`, `visible_visited`, or `remembered`, and `action`
as `null` or the exact `{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node
id>}` object. Every conforming serialized payload SHALL fit within the 65,536-byte OOB envelope limit.
Conformance is enforced on serialized size: both the Python and JavaScript validators compute the
canonical UTF-8 byte length of the assembled payload and reject a payload that exceeds the envelope,
because the per-field ceilings are independent and a payload that maximizes every string field at once
would otherwise serialize beyond the limit. A worst-case serialization test proves a structurally
maximal realistic payload fits comfortably, and a second test proves a payload at every string ceiling
at once is rejected.

#### Scenario: A grid room produces a grid-layer payload
- **WHEN** the active puppet is in a `GridRoom`/`AnchorRoom` with knowledge and an adjacent traversable
  grid exit
- **THEN** `local_map` reports `layer == "grid"`, the current node's `grid:` ID, bounded nodes and
  edges, and a before/after comparison of canonical game state is unchanged

#### Scenario: A wilderness room produces a wilderness-layer payload
- **WHEN** the active puppet is in a `TerrainRoom`
- **THEN** `local_map` reports `layer == "wilderness"`, the current `wild:` node, legal adjacent
  coordinates bounded by the provider, and terrain labels

#### Scenario: An instance room produces a coordinate-free instance payload
- **WHEN** the active puppet is in an `InstanceRoom`
- **THEN** `local_map` reports `layer == "instance"` with a `room:<dbref>` current node and a small
  graph containing the current node, its origin/return, and known real Exit edges, with no `grid:` or
  `wild:` identity invented for it

#### Scenario: An ordinary interior produces an interior payload
- **WHEN** the active puppet is in a permanent interior `Room` such as the guild hall or general store
- **THEN** `local_map` reports `layer == "interior"` with a coordinate-free graph of real Exits

#### Scenario: An unrepresentable room is unavailable, not fabricated
- **WHEN** the active puppet has no location, the location cannot be represented, or the knowledge
  record is corrupt
- **THEN** `local_map` uses the common schema-valid unavailable form with a stable reason and contains
  no invented nodes, coordinates, or edges

#### Scenario: Presenter failure remains isolated
- **WHEN** the `local_map` presenter raises while status and narrative remain healthy
- **THEN** only `local_map` becomes correlated unavailable and normal text output remains usable

### Requirement: Visibility states are current, visible_unvisited, visible_visited, and remembered
Every node in the version-1 payload SHALL carry exactly one `visibility` value. `current` SHALL mark
the player's current node. `visible_unvisited` SHALL mark a node inside the current field of view
(visual range for grid, legal adjacency for wilderness, a currently visible one-hop Exit for
instance/interior) that has not been entered. `visible_visited` SHALL mark a node inside the current
field of view that was previously entered. `remembered` SHALL mark a previously entered node outside
the current field of view. Unknown nodes SHALL be omitted entirely — never sent as hidden records. The
payload SHALL remain within the OOB envelope limits, with remembered nodes bounded by most-recent
`last_seen` and current/visible nodes always included first.

#### Scenario: Visited interior nodes retain their visited visibility
- **WHEN** a node inside an interior/instance local graph has been entered before
- **THEN** it is `visible_visited` (or `remembered` when no longer adjacent) and carries its canonical
  room name as label

#### Scenario: Unknown nodes are absent from the payload
- **WHEN** a map adapter computes the current view for a room
- **THEN** coordinates or rooms the player has never seen and that are outside the current field of
  view are absent from `nodes` and `edges`

#### Scenario: Remembered nodes are bounded and deterministic
- **WHEN** the remembered set exceeds the configured cap
- **THEN** the payload keeps the most-recent `last_seen` entries in deterministic order and never
  exceeds the bound

### Requirement: Only currently traversable Exits receive movement descriptors
A node's `action` SHALL be null unless that node is associated with a currently present, traversable
`Exit` from the actor's current room. For such a node, `action` SHALL be exactly
`{"kind": "move", "exit_ref": <1..64 ASCII characters>, "destination": <node id>}` where `exit_ref` is
an opaque server-authored identifier and `destination` is the canonical destination node ID. Remembered
remote nodes SHALL carry `action: null` and SHALL provide no travel descriptor. The browser SHALL NOT
be able to submit movement through a node with `action: null`, and an `action` with an unknown `kind`,
an oversized or non-ASCII `exit_ref`, or a missing/invalid `destination` SHALL be rejected by the exact
schema validator.

#### Scenario: Adjacent traversable exits carry a movement descriptor
- **WHEN** the current room has a traversable exit leading to an adjacent node
- **THEN** that destination node's `action` is the exact `move` object and identifies the opaque exit
  reference and destination node

#### Scenario: Remembered remote nodes carry no travel action
- **WHEN** a remembered node outside the current field of view is inspected
- **THEN** its `action` is null and it cannot submit any travel action

#### Scenario: Malformed movement descriptors are rejected
- **WHEN** a payload contains an action with an unknown `kind`, an `exit_ref` outside 1..64 ASCII
  characters, or a non-canonical or missing `destination`
- **THEN** the exact schema validator rejects the panel and the minimap renderer disables only itself
  with the single-sync recovery path

### Requirement: The browser minimap renders states without relying on color alone
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by label/shape/border in addition to color, SHALL render the legend's text labels, SHALL allow focusing a remembered remote node to view its name/landmark without any travel action, and SHALL omit unknown nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's snapshot; no client map cache is authoritative.

The component SHALL render as a bounded HUD island anchored on the stage, not as a card inside a scrolling layout column. Its root element SHALL keep the stable `local-map` component identifier that the shell's mode-gated visibility rules and its focus-rescue path both select on, so re-chroming the surface never silently un-hides it in a mode whose matrix hides it.

Layout SHALL be computed in the DOM-independent render model as a bounded integer lattice, not as a rescaling of payload coordinates into a fixed pixel box. The model SHALL place only current-field-of-view nodes (`current`, `visible_unvisited`, `visible_visited`) on that lattice, deriving each node's column and row from its payload coordinates relative to the minimum in-view coordinate, and SHALL export the lattice's column and row counts. When that span would exceed 64 columns or 64 rows, the model SHALL fall back to rank compression over the distinct sorted coordinate values, which cannot exceed the payload's node bound. The renderer SHALL size the map canvas from the exported lattice so the canvas reserves its own space **within the island's bounded height**, scaling the canvas down rather than requiring the island to scroll a required surface out of view. The canvas's height cap SHALL be derived from the space the hud-right anchor's bounded height budget leaves after the island's other sections (meta line, remembered list, legend, detail line) — not from a fixed constant — so a long remembered list no longer forces the island's `overflow-y` scroll fallback. The renderer SHALL NOT allow map content to overlap the island's title, its orientation legend, the state legend, the remembered-node list, the detail line, or any other island content. Node labels SHALL occupy a single line with an overflow indicator, and each node's full label SHALL remain available as its accessible name.

The renderer's column pitch, row pitch, and marker sizing SHALL be chosen so that, at every lattice size the model can produce, no rendered node marker's visual footprint and no rendered node label's visual footprint intersects the footprint of any other node's marker or label — this holds independently of any uniform scale-down applied to fit the island's bounded height. A connector edge between two node markers SHALL remain visually distinguishable rather than being fully occluded by the markers it connects.

The lattice-rendering logic (node/marker placement, connector edges, per-node labels, and the state legend) SHALL be shared between the minimap island's own rendering and the full-map overlay's rendering, parameterized by scale rather than duplicated: the full-map overlay SHALL render the identical in-view nodes, edges, and legend entries the minimap island renders for the same committed payload, sized to the overlay surface's own available space rather than the minimap island's fixed small canvas, with the same non-overlap guarantee applying at that larger scale. The full-map overlay SHALL NOT render the `remembered` remote-node list or the hovered/selected-node detail line; both remain minimap-island-only, since selection state has no visual effect on the lattice itself and the detail line's content spans both the in-view lattice and the remembered list.

The island SHALL carry the payload's `title`. It MAY additionally state the renderer's own axis orientation as a legend on a layer whose nodes are placed on coordinates, and SHALL omit that legend on a coordinate-free layer rather than assert a direction the payload does not support. It SHALL NOT render a bearing, a compass angle, or a distance in any form: node `x`/`y` are renderer-local presentation geometry, not canonical world coordinates, and no such figure may be derived from them.

`remembered` nodes SHALL be presented as a bounded, focusable list outside the coordinate canvas, retaining their non-color state indicator and their focus-only, no-travel behavior. Their payload coordinates describe locations outside the current field of view and SHALL NOT influence the lattice. Edges SHALL be drawn as connector lines between node centers in a non-interactive layer built through element constructors, SHALL NOT intercept node activation, and SHALL carry their label as an accessible name rather than as positioned visible text; an edge with an endpoint that is not on the canvas SHALL be omitted from the drawn layer. The `local_map` payload contract, the visibility states, the `未探索` unvisited-node rule, the remembered-node no-travel rule, and `explore.move` submission SHALL all remain unchanged.

#### Scenario: Focused remembered node offers no travel action
- **WHEN** the player focuses a remembered remote node in the minimap
- **THEN** its name and landmark are shown and there is no move or travel control for it

#### Scenario: State distinction does not depend on color alone
- **WHEN** the minimap renders current, visible, and remembered nodes
- **THEN** each state is distinguishable by non-color indicators (shape, border, or text label) and the
  legend text is readable

#### Scenario: Reconnect rebuilds from persisted knowledge
- **WHEN** the WebSocket reconnects and a new-epoch snapshot arrives
- **THEN** the minimap is rebuilt from the server-persisted visited record and current location, and no
  client-stored map state is treated as authoritative

#### Scenario: Unknown panel schema disables only the minimap
- **WHEN** a received `local_map` payload fails its exact schema
- **THEN** only the minimap renderer is disabled, the browser requests at most one full
  resynchronization, and narrative and text input remain usable

#### Scenario: In-view nodes occupy distinct lattice cells
- **WHEN** a grid-layer payload places several in-view nodes at distinct coordinates
- **THEN** each node occupies its own lattice cell, no two node markers overlap, and their relative row and column order matches the payload coordinates

#### Scenario: Distant remembered nodes do not distort the local view
- **WHEN** the payload carries remembered nodes many cells away from the current node
- **THEN** the lattice is computed only from the in-view nodes, the local neighbourhood keeps its spacing, and the remembered nodes appear in the bounded list rather than on the canvas

#### Scenario: Map content stays inside its island
- **WHEN** the minimap renders as the stage's minimap island at 1440x900 and at 1280x720
- **THEN** the canvas is sized within the island's bounded height, the title, orientation legend, state legend, remembered list, and detail line remain readable, no node marker or edge overprints other island content, and no required island content has to be scrolled to

#### Scenario: The island keeps the identifier its mode gating selects on
- **WHEN** the minimap island renders after a chrome change
- **THEN** its root element still carries the stable `local-map` component identifier, and the mode whose matrix hides the minimap still removes it from the layout and from the tab order

#### Scenario: The orientation legend states only the drawing convention
- **WHEN** the committed payload's layer places nodes on coordinates
- **THEN** the island may state the renderer's axis orientation as a legend, and no bearing, compass angle, or distance figure is rendered anywhere in the island

#### Scenario: A coordinate-free layer asserts no orientation
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation legend, and the map title, legend, and detail line render exactly as on a coordinate-bearing layer

#### Scenario: A geometrically sparse payload stays bounded
- **WHEN** a schema-valid payload places in-view nodes at coordinates whose span exceeds the lattice bound
- **THEN** the model falls back to rank compression, the lattice stays within its bound, and every node is still rendered exactly once

#### Scenario: Adjacent node markers, labels, and connector edges never visually collide
- **WHEN** a grid-layer payload places two or more nodes in adjacent lattice cells (sharing a row or a
  column), each carrying a label at the renderer's normal truncation length
- **THEN** the rendered bounding box of each node's marker and label does not intersect the bounding box
  of any other node's marker or label, and the connector edge between two adjacent nodes remains visually
  distinguishable rather than being fully covered by their markers

#### Scenario: A densely populated lattice scales down without reintroducing overlap
- **WHEN** the in-view lattice is wide or tall enough that the island's `max-width` or `max-height`
  cap scales the whole SVG canvas down proportionally
- **THEN** the pre-scale geometry already satisfies the non-overlap invariant, so the uniformly scaled
  render remains free of marker/label collisions

#### Scenario: A long remembered list keeps required island content in view
- **WHEN** the payload combines a tall in-view lattice with a long remembered-node list (up to the
  model's 64-node bound)
- **THEN** the canvas's max-height cap shrinks to the space the hud-right anchor's height budget leaves
  after the meta line, remembered list, legend, and detail line, so no required island content has to
  be scrolled out of view

#### Scenario: A single-node room states orientation without any collision risk
- **WHEN** the in-view lattice contains exactly one node
- **THEN** its marker and label render with no neighboring node to collide with, and the fix's pitch and
  sizing changes produce no regression versus the single-node case

#### Scenario: The full-map overlay renders the same lattice at a larger scale
- **WHEN** the player opens the full-map overlay while a committed `local_map` payload is available
- **THEN** the overlay renders the identical in-view nodes, edges, and legend entries the minimap island
  renders, sized to the overlay surface's own available width and height, with no marker or label collisions
  at that larger scale

#### Scenario: The full-map overlay omits the remembered-node list and the detail line
- **WHEN** the full-map overlay is open with an available `local_map` payload
- **THEN** the overlay body shows only the lattice canvas and its state legend, and does not render the
  minimap island's remembered-node list or hovered/selected-node detail line

### Requirement: Adjacent traversable map nodes submit explore.move through their move descriptor
The WebClient `local-map` component SHALL make a currently traversable adjacent node with an exact `move` action descriptor actionable: activating it (click or Enter on the focused node) SHALL submit the `explore.move` UI action carrying that node's opaque `exit_ref` and the canonical `current_node` identity. A node with `action: null`, a remembered remote node, or a node whose `visibility` is not a current-field-of-view state SHALL NOT submit any travel action and SHALL remain inert or focus-only exactly as before. The component SHALL derive the submitted `exit_ref` and `current_node` only from the validated `local_map` payload, SHALL NOT construct an exit reference, destination, or room identity from entity data or prose, and SHALL leave the `local_map` panel payload contract, the `未探索` unvisited-node rule, and the remembered-node no-travel rule unchanged. On a successful or rejected submission the refreshed `local_map` payload at the newer revision SHALL replace the rendered minimap; the component SHALL NOT keep a client-side canonical map cache. The corrected node-pitch geometry (this change) SHALL NOT alter which node an activation targets: the enlarged marker's clickable/focusable area SHALL remain centered on the same lattice coordinate the payload assigned it. This activation behavior SHALL be identical whether the lattice renders inside the minimap island or inside the full-map overlay, since both consume the same shared lattice-rendering logic.

#### Scenario: Activating an adjacent traversable node submits explore.move
- **WHEN** the player focuses an adjacent traversable node whose `action` is the exact `move` object and confirms it
- **THEN** the browser submits exactly one `explore.move` envelope with that node's `exit_ref` and the panel's `current_node`, and the refreshed `local_map` payload replaces the rendered map

#### Scenario: A remembered remote node still offers no travel action
- **WHEN** the player focuses a remembered remote node (which carries `action: null`)
- **THEN** its name/landmark is shown and no `explore.move` or other travel submission is possible, matching the pre-existing rule

#### Scenario: A map node never invents a destination
- **WHEN** a node's `action` is missing, malformed, or not the exact `move` object, or the payload is rejected by its validator
- **THEN** no travel action is submitted, only the minimap renderer disables itself with the single-sync recovery path, and narrative and text input remain usable

#### Scenario: The wider marker geometry still targets the correct node
- **WHEN** the player activates a node marker after the pitch/sizing fix has been applied
- **THEN** the `explore.move` submission carries the same node's `exit_ref` and destination as before the
  fix, unaffected by the marker's new visual size or position within its (now larger) cell

#### Scenario: Move submission works identically from the full-map overlay
- **WHEN** the player activates a traversable adjacent node while the full-map overlay is open
- **THEN** the browser submits exactly one `explore.move` envelope — the same submission the minimap island
  produces for the same payload, since both surfaces share the same lattice-rendering logic

### Requirement: Wilderness minimap nodes are actionable
Every traversable adjacent wilderness node in the local map SHALL carry an `explore.move` action descriptor with the canonical destination node, matching the grid/interior layers' behavior.

#### Scenario: Adjacent wilderness node can be moved to
- **WHEN** the player opens the local map while in wilderness terrain
- **THEN** each traversable adjacent node has a move action whose destination is the canonical node, and activating it moves the player there

#### Scenario: Non-traversable or unreachable nodes stay inert
- **WHEN** a wilderness node is outside the traversable set (e.g. out of bounds)
- **THEN** the node carries no move action
