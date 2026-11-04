# Proposal

## Why

Current ambient rows cover entire geographic regions at a fixed per-cell quantity. Sparse population needs bounded authoring and settlement-aware birth geometry before any new population owner is activated.

## What Changes

- Add immutable ecology zones, weighted complete encounter compositions and settlement birth policies with candidate-world validation.
- Compute eligible birth cells and integer density bounds, rejecting overlaps and unobstructed recovery dead ends before publication.
- No new species, live population mutation or runtime cutover in this change.
- Author four bounded pools for the currently placed approved species, without activating new automatic births.

## Capabilities

### New Capabilities

- `regional-ecology`: Bounded immutable ecology authoring and legality.

### Modified Capabilities

None.

## Impact

`monster_placement.py` has frozen AmbientPlacementRule and MonsterSite plus injectable registry validation and reference metadata. Map geography is now YAML-backed through `world/maps/runtime.py` publication; `AnchorKind` distinguishes inhabited settlement categories from DUNGEON. `WILDERNESS_ENTRY_REGISTRY` supplies actual footprint cells; point anchors use `anchor_geography().cell`. `is_valid_wilderness_cell` is shared by provider and destinations.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: none

Code conflicts:
- manual-monster-compositions shares monster_placement.py and registry metadata; land ecology types first.
- regional-population-runtime-cutover authors production declarations later; no new production ambient owner is enabled here.
- scope-test-settlement-sync is already archived in the live checkout, not an active dependency; future settlement source changes require renewed geometry validation.
