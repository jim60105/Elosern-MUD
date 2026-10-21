# Design

## Context

See proposal.md for scope and dependency ordering. Source research located world/maps/bootstrap.py::sync_grid, world/maps/map_data.py::XYMAP_DATA_LIST, typeclasses/rooms.py::GridRoom; sparse graph route adapter replacing dense allocation. Existing runtime dense/grid and pooled wilderness identities must survive this pre-release cutover.

## Goals / Non-Goals

Implement the owning delta with deterministic single-writer boundaries and bounded edge-local work. Lore stays frozen/read-only, world/maps owns persistent room lifecycle, deterministic rules own eligibility/resources/time, and WorldClock remains the clock writer. No AI module writes geometry or movement outcomes. Non-goals are listed in proposal.md.

## Decisions

Stable authored node keys are added as the synchronizer’s matching authority; deterministic old-coordinate bindings are one-time in-place convergence input, never runtime aliases.

Prefer stable sparse authored identity and explicit physical segments to dense meter ASCII or uniform coordinate multiplication. Distances use local-to-world anchor transforms; z remains logical. Snapshot intended source-present travellers once and reuse that scope before relocation, cost, followers and compensation. Refusals occur before writes. Runtime activations depend on projection, cost and external physiology integration; declarations/support can land earlier without exposing a mixed-unit runtime.

## Risks / Trade-offs

- Shared bootstrap/exit consumers can retain old assumptions. Mitigation: enumerate consumers in tasks and execute end-to-end owning tests before handoff.
- Persistent coordinates participate in identity. Mitigation: deterministic in-place synchronization, preflight conflict rejection, durable/cache rollback and repeat-start idempotence, never delete/recreate occupied rooms.
- External companion proposal is not yet available. Mitigation: `external:party-fatigue-and-sleep` blocks fatigue integration and dependent runtime activations until its real change/API is bound.

## Migration Plan

No database schema/data migration or compatibility layer. luna uses `feat/implement-sparse-settlement-graphs` in `.worktrees/implement-sparse-settlement-graphs`. Apply prerequisite changes first; synchronization converges owned declarations in place before accepting play. If synchronization fails, restore the whole transaction/cache snapshot and keep the prior authoritative runtime, rather than partially activating coordinates.
