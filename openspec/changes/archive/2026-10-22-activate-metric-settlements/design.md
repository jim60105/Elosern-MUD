# Design

## Context

See proposal.md for scope and dependency ordering. Source research located world/maps/altoria_capital.py, world/maps/village_ciaran.py, world/maps/map_data.py, world/maps/bootstrap.py::sync_grid/_sync_grid_room_art, world/maps/city_gates.py::CITY_GATE_REGISTRY, world/lore/anchor_placement.py, world/lore/settlements/places.py and place declaration modules, world/maps/room_art.py::grid_scene_identity, world/rules/map_knowledge.py::encode_grid, world/quests/definitions.py::KNOWN_GRID_MAP_KEYS. Existing runtime dense/grid and pooled wilderness identities must survive this pre-release cutover.

## Goals / Non-Goals

Implement the owning delta with deterministic single-writer boundaries and bounded edge-local work. Lore stays frozen/read-only, world/maps owns persistent room lifecycle, deterministic rules own eligibility/resources/time, and WorldClock remains the clock writer. No AI module writes geometry or movement outcomes. Non-goals are listed in proposal.md.

## Decisions

Outdoor node positions are exact; approximate city/village areas describe built-up/living space rather than sums of room squares. Coordinate-free doors remain explicit-duration connectors. Existing sparse path/goto commands remain local; no continent-wide route controller is introduced.

Prefer stable sparse authored identity and explicit physical segments to dense meter ASCII or uniform coordinate multiplication. Distances use local-to-world anchor transforms; z remains logical. Snapshot intended source-present travellers once and reuse that scope before relocation, cost, followers and compensation. Refusals occur before writes. Runtime activations depend on projection, cost and external physiology integration; declarations/support can land earlier without exposing a mixed-unit runtime.

**Road octants are authored, not derived (implementation decision).** The approved metre layout intentionally offsets every node on both axes, so the raw sign of the metre delta would label every cardinal street as a diagonal and destroy the two authored shortcuts. `ROADS` therefore carries `(source identity, destination identity, compass octant)`; `build_sparse_graph()` feeds the third field into `SparseRoad.direction_hint`, and geometry supplies only the length. The octants were verified against the pre-cutover logical layout for all 35 undirected roads, so every existing compass exit — including 工匠巷↔校場外 `ne/sw` and 大神殿前↔東市 `se/nw` — survives unchanged.

## Risks / Trade-offs

- Shared bootstrap/exit consumers can retain old assumptions. Mitigation: enumerate consumers in tasks and execute end-to-end owning tests before handoff.
- Persistent coordinates participate in identity. Mitigation: deterministic in-place synchronization, preflight conflict rejection, durable/cache rollback and repeat-start idempotence, never delete/recreate occupied rooms.
- The companion fatigue batch is now implemented. Mitigation: the dependency is bound to `settle-terminal-combat-fatigue`, which transitively requires every fatigue component, so this change integrates against the complete physiology contract rather than a partial one.

## Migration Plan

No database schema/data migration or compatibility layer. luna uses `feat/activate-metric-settlements` in `.worktrees/activate-metric-settlements`. Apply prerequisite changes first; synchronization converges owned declarations in place before accepting play. If synchronization fails, restore the whole transaction/cache snapshot and keep the prior authoritative runtime, rather than partially activating coordinates.
