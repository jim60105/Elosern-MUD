## Why

The game's movement layers, movement clock, and WebClient foundation are all live, but the shell's local-map surface is still a placeholder and nothing persists where a player has been. A truthful local minimap is the natural next UI slice: it is fully deterministic, needs no LLM or image service, and can proceed independently of the generative phases. The browser must never receive invented coordinates or duplicate static map truth, so discovery is recorded only at the existing successful-arrival seams and presented only as read-only, bounded payloads.

## What Changes

- Add `world/rules/map_knowledge.py` as the **sole writer** of a versioned, JSON-safe visited-node record on each `PlayerCharacter` (`schema_version` 1, `visited` keyed by node ID with `first_seen_tick`/`last_seen_tick`), with strict node-ID grammar (`grid:<z-map-key>:<x>:<y>`, `wild:<wilderness-name>:<x>:<y>`, `room:<dbref>`), deterministic parsing/validation/ordering, corrupt-record read isolation that never resets or overwrites player history during a read, and a corrupt-record write path that no-ops with a diagnostic instead of raising from the movement hook.
- Record discovery only at existing successful-arrival seams: the shared `MovementCostMixin.at_post_traverse` hook (grid `CostedXYZExit`, ordinary interior exits, and instance-room doorways all use it), the `WildernessGateExit`/`WildernessReturnExit` success branches, and activation relocation to the South Gate (which records the node **without** charging movement time). Failed, locked, vetoed, teleport, spawn, and rolled-back movement records nothing; startup and reconnect change neither first-seen nor last-seen.
- When an ephemeral `InstanceRoom` is reclaimed, remove its `room:<dbref>` from affected players' records **in the same database transaction** as room/entity cleanup: the prune runs before any entity/room mutation, a persistence failure marks the transaction for rollback and yields a deferred event appended only after leaving the atomic block, and attribute caches are snapshotted and restored. A promoted room keeps its dbref and visited identity.
- Add a read-only `local_map` panel (schema version 1) registered beside `status` and `context_actions`, carrying layer kind, stable current node ID, localized title, a bounded list of nodes (ID, label, renderer-local position, visibility state, current/anchor/landmark flags, optional adjacent-action reference), a bounded list of edges (source, destination, direction/label, known state, traversability), a text legend, and the common unavailable form with an explicit unrepresentable-room reason. Every bound (max 64 nodes, 128 edges, 16 legend entries, string/ID/coordinate limits, closed `layer`/`visibility`/`kind` values) is a shared constant in both the Python and JavaScript validators, with a worst-case serialization test proving a structurally maximal realistic payload fits the 65,536-byte envelope and a second test proving the validators enforce the byte budget on serialized size (a payload maximizing every string field at once is rejected).
- Add four layer adapters: grid/anchor (reads the XYMap node/link model and configured `map_visual_range` plus Anchor annotations — never the rendered ANSI string), wilderness (provider bounds, terrain labels, visited coordinate set), instance/interior (coordinate-free local graph from real Exits; current, origin/return, and visited adjacent rooms; every currently visible traversable one-hop Exit also yields a `visible_unvisited` destination labelled `未探索` whose room name is withheld until discovery).
- Replace the desktop-shell local-map placeholder with a read-only minimap renderer whose `current`, `visible_*`, and `remembered` states are distinguishable without color alone; remembered remote nodes focus for name/landmark but carry no travel action; unknown nodes are omitted, never sent as hidden records.
- Wire map movement descriptors into the version-1 payload but register **no** `explore.*` action adapter in this change — movement submission, look, interaction, dialogue, and rest/wait menus remain the `webclient-exploration-menu` delivery unit.
- Extend the Node gate, the managed Playwright suite, and deterministic Evennia fixtures with knowledge round-trips, arrival/no-discovery writers, reclamation pruning, per-layer presenter payloads, keyboard-visible state distinction, and reconnect retention.
- Add no backward-compatibility adapter or persisted-data migration; the project is unreleased and Telnet play remains unchanged.

## Capabilities

### New Capabilities

- `map-knowledge`: The versioned visited-node record, strict node-ID grammar and parsing, arrival writers at the existing successful-arrival seams, activation relocation recording, reclaimed-room pruning inside the instance-reclamation transaction, and the deterministic read parser presenters consume.
- `webclient-local-map`: The read-only version-1 `local_map` panel payload, the grid/anchor, wilderness, and instance/interior layer adapters, visibility states and legend, bounded serialization, the minimap renderer replacing the shell placeholder, and the Node/browser acceptance boundary.

### Modified Capabilities

- `movement-cost-charging`: The shared successful-arrival seam (`MovementCostMixin.at_post_traverse`) additionally records map knowledge for a `PlayerCharacter` after charging; charging semantics are unchanged.
- `wilderness-gateway`: The wilderness gate/return exit success branches additionally record the destination coordinate or grid node after a successful step; routing and clock charging are unchanged.
- `player-character-creation`: Activation relocation to 南門 also records that grid node without advancing the world clock.
- `instance-reclamation`: The reclaim branch also removes the reclaimed room's `room:<dbref>` from affected players' knowledge in the same transaction, with attribute-cache snapshot/restore on rollback.
- `sample-city-altoria`: The sample city's `XYMAP_DATA` declares the `map_visual_range`/`map_mode` options the grid adapter reads, without changing the thirteen-node topology.
- `webclient-desktop-shell`: The local-map placeholder surface becomes a real minimap renderer owned by this change while the art placeholder remains a placeholder.

## Impact

- New files: `world/rules/map_knowledge.py` and its tests; `web/webclient/presentation/local_map.py` plus its layer-adapter module(s) and tests; a DOM-independent map-render model module under `web/static/webclient/js/elosern/` with Node tests.
- Edits to landed implementation files: `typeclasses/exits.py` (`MovementCostMixin.at_post_traverse`, `WildernessGateExit`/`WildernessReturnExit` success branches), `world/rules/onboarding.py::relocate_to_starting_location`, `world/maps/instance.py::reclaim_due_instances`, `world/maps/altoria_capital.py` (map options), `web/webclient/presentation/registry.py`, `web/static/webclient/js/elosern/protocol.js` (panel allowlist + `local_map` validator), `web/static/webclient/js/plugins/goldenlayout.js` (placeholder → renderer).
- Extends `web/tests/browser/` fixtures and journeys; adds no runtime dependency, database migration, LLM call, or image-service call.
- Establishes the persisted-discovery and read-only payload contract consumed by the future `webclient-exploration-menu` unit; that unit and all service/creation/art panels remain outside this change.
