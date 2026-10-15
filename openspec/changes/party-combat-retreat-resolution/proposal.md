# Proposal: All-party retreat success/failure and exactly-once time

## Why

Individual allied flee cannot represent carrying downed companions or a shared failed retreat round.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- All-party retreat success/failure and exactly-once time. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `player-combat-session`: amend the requirements owned by this bounded slice.
- `disengage-action`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/combat_session/rounds.py`, `world/rules/combat_session/settlement.py`, `world/rules/combat_session/policies.py`, `world/rules/disengage.py`, `world/rules/combat/rounds.py`, `world/rules/tests/test_combat_party.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **10 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-confirmed-surrender
- depends-on: party-combat-defend-dodge

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-persistent-drafts`: world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-atomic-rounds`: world/rules/combat/rounds.py; world/rules/combat_session/policies.py; world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; shared specs player-combat-session.
- `party-combat-opening-routing`: world/rules/combat_session/policies.py; world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-defend-dodge`: world/rules/combat/rounds.py.
- `party-combat-taunt-constraints`: world/rules/combat/rounds.py; world/rules/combat_session/policies.py; shared specs player-combat-session.
- `party-combat-confirmed-surrender`: world/rules/combat_session/rounds.py; world/rules/combat_session/settlement.py; world/rules/disengage.py; shared specs player-combat-session.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs player-combat-session.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
