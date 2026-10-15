# Proposal: Round-start Defend and Dodge with shared estimator arithmetic

## Why

Basic tactical choices must protect a slow member before ordinary turns and expire cleanly while preserving existing hit and damage rules.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Round-start Defend and Dodge with shared estimator arithmetic. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `combat-resolution`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/combat/rounds.py`, `world/rules/combat/scalars.py`, `world/rules/combat/damage.py`, `world/rules/rulebook/combat.yaml`, `world/rules/combat/battlefield.py`, `world/rules/monster_ai/snapshot.py`, `world/rules/monster_ai/estimation.py`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **7 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: combat-ratio-mitigation
- depends-on: party-combat-atomic-rounds

### Code and spec conflicts within the new batch

- `combat-ratio-mitigation`: world/rules/combat/battlefield.py; world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/rulebook/combat.yaml; shared specs combat-resolution.
- `equipment-weapon-damage-factor`: world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py; shared specs combat-resolution.
- `party-combat-atomic-rounds`: world/rules/combat/rounds.py.
- `party-combat-taunt-constraints`: world/rules/combat/rounds.py; world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py.
- `party-combat-retreat-resolution`: world/rules/combat/rounds.py.
- `party-combat-encounter-calibration`: world/rules/rulebook/combat.yaml.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. See the complete matrix for downstream and transitive coordination.
