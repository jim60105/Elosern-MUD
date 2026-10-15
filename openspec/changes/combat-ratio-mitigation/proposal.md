# Proposal: Shared ratio damage and independent arithmetic evidence

## Why

Flat subtraction masks meaningful physical upgrades at high defense. The approved design replaces it for both physical and magic damage on both sides.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](batch.md).
- Shared ratio damage and independent arithmetic evidence. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `combat-resolution`: extend or amend the behavior owned by this bounded slice.
- `damage-effect-handlers`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/combat/scalars.py`, `world/rules/combat/damage.py`, `world/rules/combat/battlefield.py`, `world/rules/rulebook/combat.yaml`, `world/rules/monster_ai/estimation.py`, `world/rules/tests/test_golden_combat.py`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**5.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **1 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: none

### Code and spec conflicts within the new batch

- `equipment-weapon-damage-factor`: world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; shared specs combat-resolution.
- `party-combat-defend-dodge`: world/rules/combat/battlefield.py; world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/rulebook/combat.yaml; shared specs combat-resolution.
- `party-combat-taunt-constraints`: world/rules/monster_ai/estimation.py.
- `party-combat-encounter-calibration`: world/rules/rulebook/combat.yaml.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. See the complete matrix for downstream and transitive coordination.
