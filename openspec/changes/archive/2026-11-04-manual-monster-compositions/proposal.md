# Proposal

## Why

Manual sites currently cycle variant_keys until capacity, so a declared mixed or solitary encounter cannot express its complete composition directly.

## What Changes

- **BREAKING** Replace site cycling with an explicit complete composition reference, migrate all site callers and preserve one-shot/game-time lifecycle.
- Keep manual and quest placements as lawful automatic-exclusion/density exceptions; ordinary maintenance never fills or culls them.
- Deliver repeated-variant and mixed groups using current approved species only, without new boss definitions or movement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-site-placement`: Revise the behavior contract in this change's delta.

## Impact

`MonsterSite` has variant_keys/capacity, `_populate` cycles variants over capacity, and `_members` scans only the authored coordinate. `site_living_members` is pure and supplies quest clear-out bindings. Site state currently records populated/cleared and cleared_at_tick; clock settlement owns creation/recovery.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: regional-ecology-authoring
depends-on: regional-population-owner
depends-on: whole-cell-field-engagement

Code conflicts:
- regional-ecology-authoring and regional-population-runtime-cutover share monster_placement.py and reference index; sequence these changes.
- regional-hunt-supply-cutover shares site selector tests and quest clear-out assumptions; serialize overlapping edits.
- regional-population-recovery shares owner snapshots; do not change its episode behavior.
