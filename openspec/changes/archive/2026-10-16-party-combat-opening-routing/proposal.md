# Proposal: Opening selections seed interactive party rounds without compression

## Why

Exploration opening dispatch currently compresses or starts a round immediately. Party command collection must preserve the initiating choice and wait for companions.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Opening selections seed interactive party rounds without compression. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `player-combat-session`: amend the requirements owned by this bounded slice.
- `field-combat-initiation`: amend the requirements owned by this bounded slice.
- `single-shot-resolution`: amend the dispatch requirement whose only production call site this
  slice removes.

## Impact

Planned implementation/test surfaces: `world/rules/combat_initiation.py`, `world/rules/combat_session/rounds.py`, `world/rules/combat_session/policies.py`, `world/rules/combat_session/records.py`, `world/rules/combat_session/lifecycle.py`, `world/rules/combat_session/writer.py`, `commands/action.py`, `web/webclient/actions/skill_use_actions.py`, `world/rules/tests/`, `docs/game/commands.md`, `docs/game/command-reference.md`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**4.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **6 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-atomic-rounds

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-persistent-drafts`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-atomic-rounds`: world/rules/combat_session/policies.py; world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-taunt-constraints`: world/rules/combat_session/policies.py; shared specs player-combat-session.
- `party-combat-confirmed-surrender`: commands/action.py; docs/game/command-reference.md; docs/game/commands.md; world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-retreat-resolution`: world/rules/combat_session/policies.py; world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-text-commands`: commands/action.py; docs/game/command-reference.md; docs/game/commands.md; shared specs player-combat-session.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
