# Proposal: Exact v7 party-command presentation and action protocol

## Why

Version 6 supplies conditions and polarity only. Clients need authoritative actor choices, persistent progress and guarded submission/exit results.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Exact v7 party-command presentation and action protocol. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `webclient-combat-menu`: extend or amend the behavior owned by this bounded slice.
- `inventory-item-actions`: extend or amend the behavior owned by this bounded slice.
- `webclient-context-actions`: bump the exact available/unavailable forms from the incoming v6 contract to v7.
- `webclient-context-actions-suggestions`: preserve suggestions semantics while advancing the mirror/parity version contract.
- `webclient-component-showcase`: advance the action-dock protocol reference to v7.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/combat_view.py`, `web/webclient/presentation/combat_panel.py`, `web/webclient/actions/combat_actions.py`, `web/webclient/actions/registry.py`, `web/webclient/actions/inventory.py`, `web/static/webclient/js/elosern/protocol/panels/combat.js`, `web/static/webclient/js/elosern/protocol/constants.js`, `web/static/webclient/js/tests/`, `web/webclient-app/stories/fixtures/`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**7.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **11 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: equipment-weapon-damage-factor
- depends-on: party-combat-opening-routing
- depends-on: party-combat-taunt-constraints
- depends-on: party-combat-retreat-resolution
- depends-on: webclient-combat-panel-v6

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: world/rules/combat_view.py.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `webclient-party-command-selection`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `webclient-party-items-tactics`: No exact code-file overlap identified; shared specs inventory-item-actions, webclient-combat-menu.
- `webclient-party-exit-confirmation`: No exact code-file overlap identified; shared specs webclient-combat-menu.

### Active UI coordination

- `webclient-combat-panel-v6`: world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
