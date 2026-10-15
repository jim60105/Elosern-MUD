# Proposal: Validated weapon factor and physical consumers

## Why

Equipment needs an authored physical factor that applies consistently without character affinity or proficiency damage growth.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../combat-ratio-mitigation/batch.md) assigns every approved behavior.
- Validated weapon factor and physical consumers. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `equipment-effects`: amend the requirements owned by this bounded slice.
- `combat-resolution`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/equipment_effects.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/skills/equipment.py`, `world/rules/combat/damage.py`, `world/rules/combat/scalars.py`, `world/rules/monster_ai/snapshot.py`, `world/rules/monster_ai/estimation.py`, `world/rules/tests/test_equipment_effect_rulebook.py`, `world/rules/tests/test_equipment_prose.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **2 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../combat-ratio-mitigation/batch.md). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: combat-ratio-mitigation

### Code and spec conflicts within the new batch

- `combat-ratio-mitigation`: world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; shared specs combat-resolution.
- `party-combat-atomic-rounds`: No exact code-file overlap identified; shared specs combat-resolution.
- `party-combat-defend-dodge`: world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py; shared specs combat-resolution.
- `party-combat-taunt-constraints`: world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py.
- `equipment-growth-runtime-calibration`: world/rules/rulebook/equipment_effects.yaml; shared specs equipment-effects.
- `party-combat-encounter-calibration`: world/rules/rulebook/equipment_effects.yaml.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
