# Proposal: Combined player/enemy encounter and skill-budget calibration

## Why

Selected weapons, ratio mitigation and tactical choices require real encounter evidence rather than isolated favorable arithmetic.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../combat-ratio-mitigation/batch.md) assigns every approved behavior.
- Combined player/enemy encounter and skill-budget calibration. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `human-combat-calibration`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/tests/test_human_combat_calibration.py`, `world/rules/rulebook/combat.yaml`, `world/rules/rulebook/equipment_effects.yaml`, `world/skills/registry/`, `docs/development/human-combat-calibration-evidence.md`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **19 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../combat-ratio-mitigation/batch.md). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-factor-budget-calibration
- depends-on: party-combat-text-commands

### Code and spec conflicts within the new batch

- `combat-ratio-mitigation`: world/rules/rulebook/combat.yaml.
- `equipment-weapon-damage-factor`: world/rules/rulebook/equipment_effects.yaml.
- `party-combat-defend-dodge`: world/rules/rulebook/combat.yaml.
- `equipment-growth-runtime-calibration`: docs/development/human-combat-calibration-evidence.md; world/rules/rulebook/equipment_effects.yaml; world/rules/tests/test_human_combat_calibration.py; shared specs human-combat-calibration.
- `party-combat-factor-budget-calibration`: docs/development/human-combat-calibration-evidence.md; world/rules/tests/test_human_combat_calibration.py; shared specs human-combat-calibration.
- `party-combat-runtime-acceptance`: docs/development/human-combat-calibration-evidence.md.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
