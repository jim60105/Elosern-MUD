# Proposal: Playable text-client party commands and explicit exit parity

## Why

The deterministic feature must be fully playable without the browser and without possession or memorizing hidden actor capabilities.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Playable text-client party commands and explicit exit parity. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `player-combat-session`: extend or amend the behavior owned by this bounded slice.
- `inventory-item-actions`: extend or amend the behavior owned by this bounded slice.
- `game-command-docs`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `commands/combat.py`, `commands/action.py`, `commands/items.py`, `commands/default_cmdsets.py`, `commands/tests/test_combat_actions.py`, `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **12 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: party-combat-protocol-v7

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-persistent-drafts`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-atomic-rounds`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-opening-routing`: commands/action.py; docs/game/command-reference.md; docs/game/commands.md; shared specs player-combat-session.
- `party-combat-taunt-constraints`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-confirmed-surrender`: commands/action.py; commands/combat.py; docs/game/command-reference.md; docs/game/commands.md; shared specs player-combat-session.
- `party-combat-retreat-resolution`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-protocol-v7`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `webclient-party-items-tactics`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `party-combat-runtime-acceptance`: commands/tests/test_combat_actions.py.

### Active UI coordination

- No direct active-UI code/spec rewrite in this slice. See the complete matrix for downstream and transitive coordination.
