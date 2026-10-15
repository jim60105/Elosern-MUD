# Proposal: Round-start Defend and Dodge with shared estimator arithmetic

## Why

Basic tactical choices must protect a slow member before ordinary turns and expire cleanly while preserving existing hit and damage rules.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Round-start Defend and Dodge with shared estimator arithmetic. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `combat-resolution`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/combat/rounds.py`, `world/rules/combat/scalars.py`, `world/rules/combat/damage.py`, `world/rules/rulebook/combat.yaml`, `world/rules/combat/battlefield.py`, `world/rules/monster_ai/snapshot.py`, `world/rules/monster_ai/estimation.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **7 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: combat-ratio-mitigation
- depends-on: party-combat-atomic-rounds

### Code and spec conflicts within the new batch

- `combat-ratio-mitigation`: world/rules/combat/battlefield.py; world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/rulebook/combat.yaml; shared specs combat-resolution.
- `equipment-weapon-damage-factor`: world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py; shared specs combat-resolution.
- `party-combat-atomic-rounds`: world/rules/combat/rounds.py; shared specs combat-resolution.
- `party-combat-taunt-constraints`: world/rules/combat/rounds.py; world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py.
- `party-combat-retreat-resolution`: world/rules/combat/rounds.py.
- `party-combat-encounter-calibration`: world/rules/rulebook/combat.yaml.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
