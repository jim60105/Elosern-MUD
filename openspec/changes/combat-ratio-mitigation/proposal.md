# Proposal: Shared ratio damage and independent arithmetic evidence

## Why

Flat subtraction masks meaningful physical upgrades at high defense. The approved design replaces it for both physical and magic damage on both sides.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Shared ratio damage and independent arithmetic evidence. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `combat-resolution`: amend the requirements owned by this bounded slice.
- `damage-effect-handlers`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/combat/scalars.py`, `world/rules/combat/damage.py`, `world/rules/combat/battlefield.py`, `world/rules/rulebook/combat.yaml`, `world/rules/monster_ai/estimation.py`, `world/rules/tests/test_golden_combat.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**5.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **1 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: none

### Code and spec conflicts within the new batch

- `equipment-weapon-damage-factor`: world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; shared specs combat-resolution.
- `party-combat-atomic-rounds`: No exact code-file overlap identified; shared specs combat-resolution.
- `party-combat-defend-dodge`: world/rules/combat/battlefield.py; world/rules/combat/damage.py; world/rules/combat/scalars.py; world/rules/monster_ai/estimation.py; world/rules/rulebook/combat.yaml; shared specs combat-resolution.
- `party-combat-taunt-constraints`: world/rules/monster_ai/estimation.py.
- `party-combat-encounter-calibration`: world/rules/rulebook/combat.yaml.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
