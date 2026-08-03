## Context

The four map layers are live (Anchor/Grid from change 12, Wilderness from 13, Instance from 14), every exit lineage charges movement through one shared seam (`MovementCostMixin.at_post_traverse` / the wilderness `at_traverse` success branches → `world.rules.movement.charge_movement()`), and `webclient-oob-foundation` provides the versioned snapshot/update envelope, authenticated presenter registry, allowlisted action dispatch, keyboard router, and a desktop shell whose `local-map` component is still a placeholder. Instance reclamation (`reclaim_due_instances`) already owns the ephemeral-room lifecycle and its typeclass safety net.

This design implements the approved `map-knowledge-minimap` delivery unit from
`docs/superpowers/specs/2026-08-02-webclient-map-exploration-ui-design.md` (roadmap item 23c). It owns persisted discovery and read-only map payloads only. `webclient-exploration-menu` (23d) consumes those payloads and adds movement, look, interaction, dialogue, and rest/wait action adapters; nothing here registers a production action. The browser stays a read-only renderer, Telnet play is unchanged, and the single-writer rule is preserved: map knowledge has exactly one writer, `world/rules/map_knowledge.py`.

## Goals / Non-Goals

**Goals:**

- Persist visited node identity per `PlayerCharacter` without duplicating room names, glyphs, exit keys, coordinates as independent fields, terrain, or map geometry.
- Record discovery only after a successful, committed location change, per layer, including activation relocation to 南門 without charging movement time.
- Prune a reclaimed ephemeral room's `room:<dbref>` from affected players in the same transaction as room cleanup, and retain promoted rooms.
- Emit a read-only version-1 `local_map` panel with a bounded node/edge list, visibility states (`current`, `visible_unvisited`, `visible_visited`, `remembered`), a text legend, and an explicit unrepresentable-room unavailable form.
- Provide four layer adapters — grid/anchor, wilderness, instance/interior — that read canonical map data, never the rendered ANSI string.
- Replace the shell placeholder with a minimap renderer whose states are distinguishable without color alone and whose remote remembered nodes carry no travel action.
- Keep the payload within the OOB envelope limits and the browser from ever receiving unknown-node disclosure.

**Non-Goals:**

- No world atlas, continent overview, quest GPS, shortest-path UI, auto-walk, click-to-travel, or unknown-node disclosure.
- No movement, look, interaction, dialogue, or rest/wait action adapter (`explore.*`) — those belong to `webclient-exploration-menu`.
- No invented coordinates for plain or instance rooms; no nested/multi-room instances.
- No client-side pathfinding, rule calculation, canonical map cache, or authoritative layout.
- No Telnet behavior change, no mobile acceptance, no new runtime dependency, no database migration.
- No art/portrait, service, creation, or combat-menu implementation.

## Decisions

### D1. One versioned knowledge record owned by a single writer module

`world/rules/map_knowledge.py` is the only writer of `character.db.map_knowledge`, a JSON-safe `dict` of shape `{"schema_version": 1, "visited": {<node_id>: {"first_seen_tick": int, "last_seen_tick": int}}}`. It exposes a small public API:

- `record_arrival(character)` — derive the canonical node ID from `character.location` and update first/last-seen; a no-op for a non-`PlayerCharacter`, an unrepresentable location, or a corrupt pre-existing record (logs a safe diagnostic and never overwrites or resets history, and never raises from the traversal hook).
- `prune_reclaimed_room(room_id)` — remove `room:<room_id>` from every player's record, with attribute-cache snapshot/restore on failure (see D4); selects only `PlayerCharacter`s that already carry the knowledge attribute, strictly parses each record, and writes back only records that actually contain the target node.
- `parse_knowledge(character)` — the read parser presenters use; raises on a corrupt record instead of resetting it.
- Node-ID `encode`/`decode`/`validate` helpers used by both the writer and the presenter.

A separate attribute per layer was rejected because a single versioned record keeps the schema migration point in one place and matches the design doc's §4.1 shape exactly. Storing room keys, names, or dbrefs-of-rooms instead of opaque node identities was rejected because it duplicates static map truth and would go stale on rename/reclaim.

### D2. Strict node-ID grammar with bounded, registered components

| Layer | Format | Component rules |
|---|---|---|
| Grid/Anchor | `grid:<z-map-key>:<x>:<y>` | `z-map-key` a registered bounded string (no `:`); `x`/`y` integers within the XYMap's bounds |
| Wilderness | `wild:<wilderness-name>:<x>:<y>` | `wilderness-name` the registered `WILDERNESS_NAME`; `x`/`y` integers within `ElosernWildernessMapProvider` bounds |
| Instance/interior | `room:<dbref>` | positive integer dbref |

Parsing rejects missing, extra, unknown, non-integer, or out-of-bounds components. Components are escaped or restricted so delimiters cannot produce an ambiguous ID. A deleted `room:<dbref>` resolves as unavailable and is eligible for pruning. Grid/wilderness coordinates are never invented for instance or plain rooms — those use `room:<dbref>` exclusively.

### D3. Arrival recording rides the existing successful-arrival seams

Discovery is recorded where a successful player arrival is already known, never from an observer that can fire on failed or non-player movement:

- `MovementCostMixin.at_post_traverse` (grid `CostedXYZExit`, ordinary interior `Exit`, instance doorway `Exit` pair, and the Limbo bridge all use this mixin) — after `charge_movement`, call `record_arrival(traversing_object)`.
- `WildernessGateExit.at_traverse` success branch and both `WildernessReturnExit.at_traverse` success branches — after `charge_movement`, call `record_arrival(traversing_object)`.
- `world/rules/onboarding.py::relocate_to_starting_location` — after a successful relocation move, call `record_arrival(character)` with no movement charge (activation relocation records the South Gate without advancing time, per §4.3).

`record_arrival` derives the node from `character.location`, so grid, wilderness, instance, and interior each produce their canonical identity with no per-seam node computation. Hooking `at_object_receive` on rooms was rejected because `TerrainRoom` deliberately does not adopt a room-entry observer (wilderness rooms are pooled and reused) and because the design explicitly names the successful-arrival seam. Observing `at_post_move` was rejected because it fires for teleports and quiet relocations that must not record.

### D4. Reclamation pruning has an explicit commit protocol and runs before any entity mutation

`reclaim_due_instances` already wraps the reclaim branch in `transaction.atomic()`. This change defines a precise failure contract rather than relying on a silently-swallowed error inside the block, because a pruning failure that merely logs and returns would let the surrounding transaction **commit** the room deletion without the knowledge write — the exact opposite of the required atomicity.

The order inside the atomic block is deliberate. `prune_reclaimed_room(room.id)` runs **before** `_clear_non_player_entities(room)` and `room.delete()`, so a knowledge failure never occurs after entities/room have already been mutated in-memory. Evennia's idmapper does not reliably support "clear entities then roll back" (the existing `instance-reclamation` main spec already rejects that pattern), so the design guarantees that a prune failure is the *only* failure that can require cache restoration, and at that point only knowledge attribute caches have been touched — which `prune_reclaimed_room` snapshots and restores itself. The protocol is:

1. `prune_reclaimed_room(room_id)` selects only `PlayerCharacter`s that already carry a `map_knowledge` attribute, strictly parses each record, and writes back only the records that actually contain the target `room:<room_id>`. It returns a boolean success indicator and raises a dedicated `KnowledgePruneError` only on a genuine persistence failure; on any such failure it restores every snapshot it took, logs a diagnostic, and does not leave a partial write.
2. The reclaim branch treats a `KnowledgePruneError` as the trigger to mark the transaction for rollback (`transaction.set_rollback(True)`), so the room, its exits, and its entities — none of which have been touched yet at that point — stay intact in the database.
3. The deferred `ScheduledEvent` is appended **after** leaving the atomic block, only when rollback is confirmed. `reclaim_due_instances` SHALL NOT emit `"instance_reclaimed"` for a rolled-back transaction, so the returned events always agree with the committed database state.
4. If pruning succeeds, the existing `_clear_non_player_entities(room)` + `room.delete()` steps run unchanged; the existing delete-result defensive branch (unreachable-in-normal-operation per the main spec) is preserved.

A promoted room is never pruned because it is never deleted. The reverse question — whether a deleted dbref could still be re-derived — is handled by the presenter: a `room:<dbref>` that no longer resolves is treated as unavailable and omitted, and the next reclamation attempt re-prunes it idempotently.

### D5. The presenter reads only through the public parser

`web/webclient/presentation/local_map.py` registers panel name `local_map` (schema version 1) in the production registry. It builds a frozen read model from `context.actor`, `world.rules.map_knowledge.parse_knowledge(actor)`, and the actor's current location. It never reads the raw knowledge attribute, never mutates state, never creates a clock, and never enqueues anything. A corrupt knowledge record, an absent location, or an unrepresentable room raises `PanelUnavailableError` so the registry emits the exact common unavailable form with a stable reason; a presenter exception is isolated exactly as every other panel.

### D6. Grid/anchor adapter reads the XYMap topology, not its ANSI render

Given an actor in a `GridRoom`/`AnchorRoom`, the adapter resolves the current `XYMap` through `get_xyzgrid().get_map(z)`, uses the node/link model (`node_index_map`, `get_node_from_coord`, `node.links`) and the configured `map_visual_range` (read from the map's `options`, declared by `sample-city-altoria` in this change), and Anchor annotations from the anchor placement registry. It emits nodes for the current node, every node within visual range, and every known visited node (bounded, see D10), with edges for the links between them, traversable when an in-world `CostedXYZExit`/`Exit` actually exists at that grid link and reachable from the actor. The rendered ANSI map string is never parsed. `map_mode` is restricted to `nodes | scan` and `map_visual_range` to a bounded positive integer; an invalid or unknown `options` value fails closed to the stable unavailable reason rather than guessing a default.

### D7. Wilderness adapter reads provider bounds and terrain labels

Given an actor in a `TerrainRoom`, the adapter uses `location.coordinates` and the wilderness name from `location.wilderness`, the provider's `WILDERNESS_MAX_X`/`WILDERNESS_MAX_Y` bounds, the eight legal adjacent coordinates, `region_for_coordinates`/`WILDERNESS_REGION_REGISTRY` labels, and the visited coordinate set from knowledge. Current and adjacent cells are visible; visited cells outside adjacency are `remembered`. The map remains coarse at the established 10-km cell scale.

### D8. Instance/interior adapter produces a coordinate-free local graph

Given an actor in an `InstanceRoom` or a plain interior `Room`, the adapter resolves the current room and its real `Exit`s. It renders the current node, the origin/return room (for `InstanceRoom`, `origin_room`; for an interior, the return exit's source), and visited adjacent rooms. Every currently visible and traversable one-hop `Exit` also yields a `visible_unvisited` destination node labelled `未探索` whose canonical room name and details are withheld until arrival; the edge may show only the Exit key/direction. The one-room instance yields a deliberately small graph. Positions are renderer-local layout values derived from Exit order — never sent back as movement authority.

### D9. Visibility states and remembered-node bounding

Visibility is derived per layer:

| State | Meaning |
|---|---|
| `current` | Player's current node |
| `visible_unvisited` | In current field of view (visual range / adjacency / one-hop exit) but never entered |
| `visible_visited` | In current field of view and previously entered |
| `remembered` | Previously entered but outside current field of view |

Unknown nodes are omitted entirely — the browser cannot reveal them through DOM inspection. To keep payloads bounded, remembered nodes are capped (most-recent `last_seen` first, deterministic tie-break), while current and visible nodes always fit first. The serialized payload must stay under the 65,536-byte envelope limit, and lists/strings carry explicit bounds below the protocol globals.

### D10. Movement descriptors are payload data, not a registered action

Only a node associated with a currently present, traversable `Exit` receives an adjacent-action descriptor in the payload; the exact nullable form is `action: null` or `{"kind": "move", "exit_ref": <1..64-character opaque ASCII identifier>, "destination": <canonical node id>}`, with `kind` restricted to `move` in this version. Remembered remote nodes carry `action: null`. This change does **not** register `explore.move` or any other production action; the descriptor is the data the `webclient-exploration-menu` unit consumes to submit movement through the dispatcher. Because the production action registry is specified as exactly the three combat actions until another owning change adds one, no `webclient-action-dispatch` delta is needed here — the minimap descriptor must never be mistaken for a dispatcher action. This keeps the minimap read-only and leaves every mutation path to 23d.

### D10a. Exact bounded schema constants shared by server and client validators

The `local_map` version-1 payload SHALL carry explicit, independent bounds below the protocol globals: at most `MAX_NODES = 64` nodes and `MAX_EDGES = 128` edges (the OOB global list cap is 128, so edges are exactly at it while nodes stay under it to leave envelope headroom), at most `MAX_LEGEND = 16` legend entries, node/edge/label strings of at most 256 code points, a title of at most 128 code points, node IDs of at most 128 characters, opaque `exit_ref` identifiers of exactly 1..64 ASCII characters, and renderer-local `x`/`y` integers in `-1024..1024`. `known`, `traversable`, `current`, `anchor`, and `landmark` are booleans; `visibility` is one of the four closed values; `layer` is one of `grid`/`wilderness`/`instance`/`interior`. Python (`web.webclient.presentation.local_map`) and JavaScript (`elosern/protocol.js`) validators use the same constants, guarded by a dual-direction parity test.

The envelope guarantee is enforced on **serialized size**, not just per-field bounds: both validators compute the canonical UTF-8 byte length of the assembled payload and fail closed when it exceeds the 65,536-byte OOB envelope limit. This is necessary because the per-field ceilings are independent — a payload that simultaneously maximizes every string field is schema-legal per-field yet would serialize beyond the envelope, so conformance ("every accepted payload fits") is defined and enforced by the byte budget. A worst-case serialization test proves a structurally maximal realistic payload fits comfortably, and a second test proves a payload at every string ceiling at once is rejected. Both are mirrored in the Node suite.

### D11. The minimap renderer replaces the shell placeholder

A DOM-independent `local_map.js` module reduces the validated `local_map` panel into a render model (nodes, edges, legend, focus targets). The GoldenLayout `local-map` component subscribes to the state controller and draws the model, replacing `registerUnavailable`. States are distinguished by shape/label/border plus color. Remembered remote nodes are focusable for name/landmark and carry no travel action; clicking or Enter on an adjacent node does nothing in this change (the adapter is 23d). Unknown panels still fall to the foundation's single-sync recovery; reconnect rebuilds purely from server-persisted knowledge, with no authoritative client map cache.

## Risks / Trade-offs

- [An unruly wilderness visited set can exceed envelope bounds] → Cap remembered nodes by most-recent `last_seen` with deterministic tie-breaks; current and visible nodes always fit; test worst-case serialization size against the exact constants in D10a.
- [Evennia attribute caching can leak a rolled-back knowledge write] → `prune_reclaimed_room` snapshots and restores affected values on failure, runs before any entity/room mutation in the reclaim block, and signals failure through a rollback of the enclosing transaction (D4).
- [A pruning failure could commit a room deletion without the knowledge write] → The reclaim branch treats the dedicated `KnowledgePruneError` as the rollback trigger, emits the deferred event only after leaving the atomic block, and never returns `instance_reclaimed` for a rolled-back transaction (D4).
- [Node-ID grammar drift between writer and presenter] → Both use the same `encode`/`decode`/`validate` helpers; malformed IDs fail closed on read.
- [A deleted dbref lingers in a player's record] → Presenter omits unresolvable `room:<dbref>` nodes; the next reclamation prunes them idempotently.
- [A corrupt pre-existing record could break ordinary traversal] → `record_arrival` logs a safe diagnostic and no-ops on a corrupt record instead of raising from the movement hook, so moving, charging, and narration still succeed.
- [Grid `options` typos could silently widen/narrow vision] → `map_mode` is restricted to `nodes | scan`, `map_visual_range` to a bounded positive integer, and invalid values fail closed to the stable unavailable reason with a content test (D6).
- [The minimap could drift from the movement reality] → Only real, currently present, traversable `Exit`s get movement descriptors; the payload is rebuilt from canonical state on every snapshot/update.
- [Movement is deferred to 23d, so the minimap is display-only in this change] → Accepted and explicit: the payload carries the descriptor data; registering no action keeps this unit read-only and independently shippable.
- [Placeholder tests assert the local-map surface is unavailable] → This change replaces that surface; the `webclient-desktop-shell` delta and browser fixtures are updated together so no stale placeholder assertion remains.

## Migration Plan

No stored schema changes and no data migration: the project is unreleased with zero users, the knowledge attribute is new, and no existing record shape is being renamed. Implement in dependency order: shared node-ID/knowledge core and seams → reclamation pruning → presenter and layer adapters → registry/panel allowlist → browser renderer → Node and Playwright gates. Rollback is the ordinary code-revision rollback; no dual reader or data restore is needed because the writer owns the only new persistent field.

## Open Questions

None. The observable scope — persisted discovery, four layer adapters, read-only version-1 payload, display-only minimap, no action registration, instance amendment limited to real `Exit` graphs — is fixed by the approved parent and focused designs.
