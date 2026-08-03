## ADDED Requirements

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
The WebClient `local-map` component SHALL render the validated `local_map` panel, replacing the
foundation placeholder. It SHALL distinguish `current`, `visible_*`, and `remembered` states by
label/shape/border in addition to color, SHALL render the legend's text labels, SHALL allow focusing a
remembered remote node to view its name/landmark without any travel action, and SHALL omit unknown
nodes. On reconnect it SHALL rebuild the map from the server-persisted knowledge in the new epoch's
snapshot; no client map cache is authoritative.

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
