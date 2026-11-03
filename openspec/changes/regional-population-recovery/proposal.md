# Proposal

## Why

Player-driven clock settlement must recover regional deficits after a delay without re-entry refills or combat losses borrowing earlier-round time.

## What Changes

- Add durable recovery episodes and chronological due waves through the existing clock event-source and snapshot contracts.
- Record actual defeat occurrences with round offsets, cancel obsolete episodes without births or sequence changes, and retry temporary blockage after the authored interval.
- Preserve equal-time partition outcomes, complete rollback and active encounter protection. Production registration is enabled only at final runtime cutover.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `regional-population`: Dependent extension after regional-population-owner establishes this capability.
- `player-combat-session`: Revise the behavior contract in this change's delta.

## Impact

`WorldClock.advance` snapshots registered owner surfaces before its transaction and restores mutable caches on failure. `register_event_source(kind, source, surfaces, *, next_boundary=None)` is the current seam. Combat time remains terminal-only; `_finalize_resolved_round` knows the completed-round ordinal, while `settle_combat_result` advances all accumulated seconds at battle end. Its regional-population capability is introduced by the required predecessor and becomes the authoritative target before this dependent change archives.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: regional-population-owner
depends-on: combat-individual-identity

Code conflicts:
- whole-cell-field-engagement edits combat_session lifecycle/rounds and previews; serialize shared-file edits without adding a dependency between independent behavior slices.
- regional-population-runtime-cutover owns startup registration and stage activation after this callable source is complete.
- manual-monster-compositions shares site/population snapshot tests; serialize manifests.
