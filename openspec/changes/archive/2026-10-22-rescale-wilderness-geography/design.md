# Design

## Context

See proposal.md for scope and dependency ordering. Source research located world/maps/wilderness_provider.py::ElosernWildernessMapProvider/region_for_coordinates, world/maps/wilderness_destination.py, world/lore/wilderness_entry.py::validate_wilderness_entries/_iter_map_extents, world/maps/bootstrap.py::sync_wilderness. Existing runtime dense/grid and pooled wilderness identities must survive this pre-release cutover.

## Goals / Non-Goals

Implement the owning delta with deterministic single-writer boundaries and bounded edge-local work. Lore stays frozen/read-only, world/maps owns persistent room lifecycle, deterministic rules own eligibility/resources/time, and WorldClock remains the clock writer. No AI module writes geometry or movement outcomes. Non-goals are listed in proposal.md.

## Decisions

The approved design fixes approximate footprint area and entrance positions, not a unique polygon. Author a deterministic irregular footprint from the physical city envelope with approximately 40km² area and validate external gate approaches; exact non-gate boundary vertices are authoring discretion. Meter gate geometry can be declared before settlement coordinate activation; resolving its current logical target uses stable node identity, never a coordinate alias.

Prefer stable sparse authored identity and explicit physical segments to dense meter ASCII or uniform coordinate multiplication. Distances use local-to-world anchor transforms; z remains logical. Snapshot intended source-present travellers once and reuse that scope before relocation, cost, followers and compensation. Refusals occur before writes. Runtime activations depend on projection, cost and external physiology integration; declarations/support can land earlier without exposing a mixed-unit runtime.

## Risks / Trade-offs

- Shared bootstrap/exit consumers can retain old assumptions. Mitigation: enumerate consumers in tasks and execute end-to-end owning tests before handoff.
- Persistent coordinates participate in identity. Mitigation: deterministic in-place synchronization, preflight conflict rejection, durable/cache rollback and repeat-start idempotence, never delete/recreate occupied rooms.
- The companion fatigue batch is now implemented. Mitigation: the dependency is bound to `settle-terminal-combat-fatigue`, which transitively requires every fatigue component, so this change integrates against the complete physiology contract rather than a partial one.

## Migration Plan

No database schema/data migration or compatibility layer. luna uses `feat/rescale-wilderness-geography` in `.worktrees/rescale-wilderness-geography`. Apply prerequisite changes first; synchronization converges owned declarations in place before accepting play. If synchronization fails, restore the whole transaction/cache snapshot and keep the prior authoritative runtime, rather than partially activating coordinates.

Pre-release cutover policy: ordinary wilderness rooms and monster-site individuals
created under the old 224-cell frame are not migrated. A fresh world (or a
GM-driven reclamation of the old wilderness rooms/sites) is the prerequisite;
`--keepdb` is not a migration strategy.

Spec-sync procedure: this change pre-syncs its ADDED requirements (and the
MODIFIED requirement text) into `openspec/specs/` so `covers_requirement` IDs are
valid during implementation. Archiving therefore moves the change directory and
must not re-apply the delta (`openspec archive --skip-specs`, or the repository's
equivalent directory move), because the ADDED headers already exist in the main
specs. This mirrors how `establish-continental-geography` was archived.
