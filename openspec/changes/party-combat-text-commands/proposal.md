# Proposal: Playable text-client party commands and explicit exit parity

## Why

The deterministic feature must be fully playable without the browser and without possession or memorizing hidden actor capabilities.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../combat-ratio-mitigation/batch.md) assigns every approved behavior.
- Playable text-client party commands and explicit exit parity. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `player-combat-session`: amend the requirements owned by this bounded slice.
- `inventory-item-actions`: amend the requirements owned by this bounded slice.
- `game-command-docs`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `commands/combat.py`, `commands/action.py`, `commands/items.py`, `commands/default_cmdsets.py`, `commands/tests/test_combat_actions.py`, `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **13 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../combat-ratio-mitigation/batch.md). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-command-transport

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-persistent-drafts`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-atomic-rounds`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-opening-routing`: commands/action.py; docs/game/command-reference.md; docs/game/commands.md; shared specs player-combat-session.
- `party-combat-taunt-constraints`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-confirmed-surrender`: commands/action.py; commands/combat.py; docs/game/command-reference.md; docs/game/commands.md; shared specs player-combat-session.
- `party-combat-retreat-resolution`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-command-transport`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `webclient-party-items-tactics`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `party-combat-runtime-acceptance`: commands/tests/test_combat_actions.py.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. The complete batch matrix records transitive coordination.
