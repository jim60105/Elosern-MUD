# Proposal: Persistent editable party draft and authoritative completeness

## Why

Command selection must survive interruption and remain free until every eligible member has a valid command.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Persistent editable party draft and authoritative completeness. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `player-combat-session`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/combat_session/records.py`, `world/rules/combat_session/lifecycle.py`, `world/rules/combat_session/rounds.py`, `world/rules/combat_session/settlement.py`, `world/rules/equipment.py`, `world/rules/tests/test_combat_session_persistence.py`, `world/rules/tests/test_combat_session_recovery.py`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **4 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: party-combat-actor-commands

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-atomic-rounds`: world/rules/combat_session/records.py; world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-opening-routing`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-taunt-constraints`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-confirmed-surrender`: world/rules/combat_session/records.py; world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-retreat-resolution`: world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs player-combat-session.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. See the complete matrix for downstream and transitive coordination.
