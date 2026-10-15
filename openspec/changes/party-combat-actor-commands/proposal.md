# Proposal: Commander authorization and complete actor-scoped skill/item requests

## Why

Companions currently receive policy actions and puppet-bound previews. Party commands require authoritative actor-local capabilities and resource ownership.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Commander authorization and complete actor-scoped skill/item requests. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `player-combat-session`: extend or amend the behavior owned by this bounded slice.
- `item-use-resolution`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/combat_view.py`, `world/rules/action_preview.py`, `world/rules/combat_session/rounds.py`, `world/rules/combat_session/battlefield.py`, `world/rules/items.py`, `world/rules/targeting.py`, `world/rules/tests/test_combat_view.py`, `world/rules/tests/test_item_combat_turn.py`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **3 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: none

### Code and spec conflicts within the new batch

- `party-combat-persistent-drafts`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-atomic-rounds`: world/rules/combat_session/rounds.py; world/rules/tests/test_item_combat_turn.py; shared specs item-use-resolution, player-combat-session.
- `party-combat-opening-routing`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-taunt-constraints`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-confirmed-surrender`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-retreat-resolution`: world/rules/combat_session/rounds.py; shared specs player-combat-session.
- `party-combat-protocol-v7`: world/rules/combat_view.py.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs player-combat-session.

### Active UI coordination

- `webclient-combat-panel-v6`: world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
