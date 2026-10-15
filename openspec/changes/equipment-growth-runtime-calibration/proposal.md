# Proposal: Authored shipped weapon values and committed-reload growth evidence

## Why

A neutral field is insufficient equipment growth. Real registry weapons and persistent equipment must demonstrate selected balance values and arithmetic placement.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Authored shipped weapon values and committed-reload growth evidence. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `equipment-effects`: extend or amend the behavior owned by this bounded slice.
- `human-combat-calibration`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/rulebook/equipment_effects.yaml`, `world/rules/tests/test_equipment_combat_wiring.py`, `world/rules/tests/test_human_combat_calibration.py`, `docs/development/human-combat-calibration-evidence.md`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **16 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: equipment-weapon-damage-factor
- depends-on: party-combat-defend-dodge

### Code and spec conflicts within the new batch

- `equipment-weapon-damage-factor`: world/rules/rulebook/equipment_effects.yaml; shared specs equipment-effects.
- `party-combat-encounter-calibration`: docs/development/human-combat-calibration-evidence.md; world/rules/rulebook/equipment_effects.yaml; world/rules/tests/test_human_combat_calibration.py; shared specs human-combat-calibration.
- `party-combat-runtime-acceptance`: docs/development/human-combat-calibration-evidence.md.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. See the complete matrix for downstream and transitive coordination.
