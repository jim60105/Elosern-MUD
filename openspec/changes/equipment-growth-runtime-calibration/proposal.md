# Proposal: Authored shipped weapon values and committed-reload growth evidence

## Why

A neutral field is insufficient equipment growth. Real registry weapons and persistent equipment must demonstrate selected balance values and arithmetic placement.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Authored shipped weapon values and committed-reload growth evidence. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `equipment-effects`: amend the requirements owned by this bounded slice.
- `human-combat-calibration`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/rulebook/equipment_effects.yaml`, `world/rules/tests/test_equipment_combat_wiring.py`, `world/rules/tests/test_human_combat_calibration.py`, `docs/development/human-combat-calibration-evidence.md`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **17 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: equipment-weapon-damage-factor
- depends-on: party-combat-defend-dodge

### Code and spec conflicts within the new batch

- `equipment-weapon-damage-factor`: world/rules/rulebook/equipment_effects.yaml; shared specs equipment-effects.
- `party-combat-factor-budget-calibration`: docs/development/human-combat-calibration-evidence.md; world/rules/tests/test_equipment_combat_wiring.py; world/rules/tests/test_human_combat_calibration.py; shared specs human-combat-calibration.
- `party-combat-encounter-calibration`: docs/development/human-combat-calibration-evidence.md; world/rules/rulebook/equipment_effects.yaml; world/rules/tests/test_human_combat_calibration.py; shared specs human-combat-calibration.
- `party-combat-runtime-acceptance`: docs/development/human-combat-calibration-evidence.md.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
