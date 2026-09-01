# Design — Fix Wilderness Map Adjacency Truth

## Context

The wilderness contrib builds its eight direction exits as self-loops
(`destination == room`), and the grid-side `WildernessGateExit` is likewise a
self-loop (`destination == gate room`, `world/maps/bootstrap.py:308-315`). The
traversal truth is:

- `WildernessReturnExit.at_traverse` (`typeclasses/exits.py:293+`): at a
  registered entry coordinate, the `south` exit moves the player into the
  anchor's grid room (`_grid_room_for_anchor(entry.anchor_key)`); every other
  step is one cell in the direction's delta.
- `WildernessGateExit.at_traverse` (`typeclasses/exits.py:234+`): at a grid
  room, enters the wilderness at `entry.wilderness_xy`.
- `world/maps/wilderness_destination.resolve_wilderness_destination` already
  mirrors both rules and returns the canonical arrival node id. It is the
  single resolver (pinning test moves through the real exit and compares).

The minimap presenter (`web/webclient/presentation/local_map.py`) consults the
resolver only for the node's `action.destination`, then fabricates the node's
`id`/label/`x`/`y` from raw geometry
(`_wilderness_layer`, lines 558-672). So at the entry cell (60,100) the south
node is `wild:elosern:60:99` labelled with that cell's terrain, while its
action sends the player to `grid:capital_altoria:2:4` — the North Gate. The
gate's `grid:` node is in the player's knowledge (`record_arrival` on
traversal) yet never appears on the wilderness layer. Mirrored: at the North
Gate, `_grid_exit_action` matches exits by `exit_obj.destination is
destination`, which a self-loop gate exit can never satisfy, so the gate's
wild destination never appears on the grid layer either.

## Goals / Non-Goals

**Goals**

- Node identity/label/visibility follow the resolver: same source as traversal.
- The visited gate node (or gate wild cell) appears on the opposite layer with
  correct visibility, label, flags, and move action.
- One direction-delta table shared by resolver and presenter.
- Remove the dead code and per-node duplicate DB queries in `_grid_layer`.

**Non-Goals**

- No payload schema change (exact-field validator + JS parity + Node gate make
  new fields disproportionately expensive; mixed-prefix nodes are already
  legal — only `current_node` gets a prefix↔layer check).
- No traversal/knowledge changes; `resolve_wilderness_destination`'s semantics
  are unchanged (it only gains exported geometry helpers).
- No exploration-menu change (already resolver-driven).

## Decisions

### D1 — Identity follows resolution; geometry follows position (renderer-local)

In `_wilderness_layer`, per direction `d`:

1. `destination = resolve_wilderness_destination(location, d)` (as today).
2. If `destination` is `None` or starts with `wild:` → node as today
   (geometric neighbour id, terrain label, bounds-skipped).
3. If `destination` starts with `grid:` (registered gateway): node id =
   `destination`; label = the grid room's `key` (the same `GridRoom` lookup the
   grid layer uses, via `decode_node(destination)`'s xyz — the room must exist
   since the resolver just resolved it; fall back to the resolver's id string
   if a race deleted it, never fabricate a terrain label);
   `anchor`/`landmark` = whether the room is an `AnchorRoom` (mirrors the grid
   layer's flag rule); `visibility = "visible_visited" if the id is in the
   visited map else "visible_unvisited"` (the player who walked out through the
   gate has the visit recorded; an admin-teleported player honestly sees
   `visible_unvisited`); action as today (already resolver-driven); **`x`/`y` =
   the adjacent wild cell position**, not the grid room's world coordinates.

Why adjacent-cell geometry: node `x`/`y` are already spec-declared
"renderer-local presentation geometry, not canonical world coordinates"
(`webclient-local-map`, panel requirement), and the lattice derives
columns/rows from raw payload coordinates. A `grid:(2,4)` node among
`wild:(59..61, 99..101)` neighbours would produce a ~60-column sparse lattice —
rank compression would draw it due south-west, a *different* lie. Position-in-
view is the honest renderer-local value; the amendment records this rule so it
can't regress. The gold landmark ring + real room label make the gate
visually distinct from wild cells; the action destination equals the node id,
removing the current display/action divergence.

**Rejected**: raw `grid:(2,4)` coordinates (lattice distortion above); a new
`layer_kind`/`gateway` node field (schema bump, JS validator + parity contract
+ Node gate churn for a flag the renderer already gets from `anchor`).

### D2 — Grid layer renders registered gate exits as resolver-driven nodes

In `_grid_layer`, after in-range nodes: for each `WildernessGateExit` at the
current room whose `db.anchor_key` is in `WILDERNESS_ENTRY_REGISTRY`, resolve
the target cell `(entry.wilderness_xy)` → id `wild:elosern:<x>:<y>`, label =
region display name (same registry the wild layer uses), `visibility` from the
visited map, action = `{"kind":"move","exit_ref":_exit_ref(gate),"destination":
wild:...}` when `_traversable(gate, actor)`. Geometry: position at the
direction named by the gate exit's key/aliases normalized through
`normalize_wilderness_direction` (North Gate: key 荒野, aliases include
`north`/`n` → drawn due north of current at `current + delta`); a gate whose
key/aliases name no direction falls back to the first traversable candidate —
deterministic ordering by `dbid`. Two invariants make the gate never silently
disappear (node identity disjointness does NOT protect the geometry slot — an
in-range grid node can legitimately sit at `current + delta`):

1. **Capacity reservation:** registered-gate capacity is accounted for before
   the ordinary nodes are laid down. `_grid_nodes_in_range` is capped at
   `MAX_NODES - len(gate candidates)` by trimming the farthest nodes first
   (deterministic order: descending Chebyshev distance, then Y, then X), so
   `len(nodes) ≤ 64` always holds and the gate is never the thing that breaks
   `validate_local_map`. With the shipped city (nodes mode, range 2) nothing is
   ever trimmed; the rule exists so a pathological 64-node scan map plus a
   gate stays schema-valid.
2. **Slot probing:** if the gate's preferred slot is already occupied by an
   added node, the gate takes the nearest free renderer-local slot in
   deterministic probe order (ring sweep by `(|dx| + |dy|)`, then `dy`, then
   `dx`, within `-1024..1024`). A free slot always exists: the ±8 scan window
   around the current node offers 289 slots while the payload caps at 64
   nodes, so the sweep never needs a drop path; a same-id duplicate is never
   added.

This closes the mirror gap: from the gate, the minimap offers the same
wilderness entry the CLI/exploration menu already offer.

**Rejected**: leaving the grid side alone — the asymmetric map would still
hide one of the two traversal edges of the gateway, i.e. the map would keep
lying by omission, and D1's wilderness-side node would point at a gate room
whose own map doesn't show the return.

### D3 — One delta table, exported from the resolver module

`world/maps/wilderness_destination.py` exports `DIRECTION_DELTAS` (rename the
private table) and a new `wilderness_neighbor(x, y, direction) -> tuple[int,
int] | None` (bounds-checked, same `WILDERNESS_MAX_*` guard the resolver uses
inline). `local_map.py`'s `_wild_neighbor` and its duplicated literal table are
deleted; the loop iterates `DIRECTION_DELTAS` order (unchanged 8-way order).
The resolver stays the pure read helper it is; its pinning test keeps passing
because behavior is identical.

### D4 — Hygiene in the same file

- Delete `_grid_layer`'s `known_visited_ids` (computed, never read).
- Replace the `anchor_coord` loop (which re-derives what
  `get_node_from_coord` already returned and only feeds a `None` guard) with
  the existing `current_node is None → PanelUnavailableError` check; the
  `current_id` stays as-is.
- Collapse `_grid_node_label` + `_grid_coord_label` (identical bodies,
  one `filter_xyz` each) into one `_grid_room_label(coord, z)` used by both
  call sites.
- `_grid_exit_action`: keep its single destination lookup; do NOT also make it
  return the label (signature churn for a few ms) — the label collapse already
  halves the per-node queries; further combining is deferred.

## Risks / Trade-offs

- [Gateway node geometry is adjacency-relative, so a player who knows the grid
  coordinates may misread the gate's drawn position as its world position] →
  The label is the room name, the coordinate figure (sibling change A) shows
  the CURRENT node's coordinates, and the payload already declares x/y
  renderer-local; the drawn position states "one step that way", which is the
  truth of the edge.
- [`_traversable` on the gate exit mis-evaluates and offers a step that later
  fails] → Same semantics as every other move descriptor; the action handler
  re-checks traversal server-side.
- [Tests pin the old behavior] → `web/webclient/presentation/tests/test_local_map.py`
  wilderness-label and adjacent-destination tests are updated to the resolver
  truth in this change; a new pinning test walks the REAL gateway exit and
  asserts the minimap node (id, label source, visibility, action) matches the
  actual arrival — the anti-drift contract.
- [Gate direction guessed from aliases] → Deterministic: registry aliases are
  authored data; normalization is the resolver's own function; no alias match →
  stable dbid order fallback, asserted in a test.

## Migration Plan

Single commit; no shipped users, no persisted payload copies (the panel is
rebuilt every commit tick). Revert = revert commit.

## Open Questions

None blocking. (A future multi-gate world may want per-gate geometry slots;
today one registered entry exists, and the ordering rule is written so a second
gate extends deterministically.)
