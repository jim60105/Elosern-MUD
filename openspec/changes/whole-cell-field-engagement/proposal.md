# Proposal

## Why

Opening casts currently reuse one target list for encounter membership and effects. A single-target action therefore omits other living monsters in the same cell.

## What Changes

- **BREAKING** Ordinary field entry admits every living co-located Monster in persistent-ID order through text, browser, player and companion cast routes.
- Separate the complete enemy roster from opening recipients, retaining targeting, party draft, costs, initiative and atomic admission.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `field-combat-initiation`: Revise the behavior contract in this change's delta.
- `player-combat-session`: Revise the behavior contract in this change's delta.

## Impact

`_room_monsters` already returns living co-located monsters sorted by pk. `_opening_line_up`, `_candidate_record` and `_prepare_opening` pass a skill-dependent target list through candidate reconstruction, validation and engagement. `engage` delegates to `engage_group(actor, [target])`; explicit examinations have a separate mode.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: combat-individual-identity

Code conflicts:
- combat-individual-identity and regional-population-recovery share combat_session files; follow identity and serialize with recovery edits.
- actual-live-population-view shares exploration/presentation tests; merge those assertions carefully.
