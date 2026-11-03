# Proposal

## Why

Coordinate slots cannot retain ownership separately from position or count manual visitors against a regional budget. A dedicated map owner must commit complete seeded births without replacing living individuals.

## What Changes

- Add a map-owned durable zone state and deterministic legal wave planner/committer with local, cell and home-owned individual ceilings.
- Provide one-time constrained initialization, separate home ownership and actual coordinate registration, and complete transaction/cache compensation.
- This change supplies callable owner operations; startup/clock production registration switches only in the runtime-cutover change.

## Capabilities

### New Capabilities

- `regional-population`: Persistent individual-based regional birth ownership.

### Modified Capabilities

None.

## Impact

Species-backed construction is already authoritative in `construct_species_individual`. Wilderness position lives in `itemcoordinates`, independent of materialized room presence. Existing `monster_sites` and clock SurfaceSnapshot/rollback helpers demonstrate whole-value Attributes, registration and cache compensation; database rollback alone leaves mutable SaverDict and room surfaces stale.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: regional-ecology-authoring

Code conflicts:
- regional-population-recovery extends the same new owner module and snapshots; land this first.
- manual-monster-compositions reuses pure composition planning; serialize shared helper edits.
- actual-live-population-view consumes individual ownership/registration; no view contract is activated here.
