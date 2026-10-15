# Proposal: Complete companion item use and tactical menus in the shared card

## Why

Items and tactical rows must become usable actor-local round choices rather than placeholder root entries or puppet-bound inventory actions.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Complete companion item use and tactical menus in the shared card. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `webclient-combat-menu`: extend or amend the behavior owned by this bounded slice.
- `inventory-item-actions`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `web/static/webclient/js/elosern/combat_menu.js`, `web/webclient-app/stores/elosern/frames.js`, `web/webclient-app/stores/elosern/combat.js`, `web/webclient-app/stores/elosern/cross_side.js`, `web/webclient-app/stores/elosern/stage_targets.js`, `web/webclient-app/components/ActionDock.vue`, `web/webclient-app/components/InventoryPanel.vue`, `web/webclient-app/stories/Core/AppShell.stories.js`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **14 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

- depends-on: webclient-party-command-selection

### Code and spec conflicts within the new batch

- `party-combat-protocol-v7`: No exact code-file overlap identified; shared specs inventory-item-actions, webclient-combat-menu.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `webclient-party-command-selection`: web/static/webclient/js/elosern/combat_menu.js; web/webclient-app/components/ActionDock.vue; web/webclient-app/stores/elosern/combat.js; web/webclient-app/stores/elosern/cross_side.js; web/webclient-app/stores/elosern/frames.js; web/webclient-app/stores/elosern/stage_targets.js; web/webclient-app/stories/Core/AppShell.stories.js; shared specs webclient-combat-menu.
- `webclient-party-exit-confirmation`: web/static/webclient/js/elosern/combat_menu.js; web/webclient-app/stores/elosern/combat.js; web/webclient-app/stores/elosern/frames.js; web/webclient-app/stories/Core/AppShell.stories.js; shared specs webclient-combat-menu.

### Active UI coordination

- `webclient-combat-formation`: AppClient.vue; stories; browser methods; no formation geometry ownership transfer; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-command-card-centred`: ActionDock.vue; AppClient.vue; stories; fixed card geometry unchanged; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-stage-target-picking`: stage_targets.js; interaction/combat/view stores; ActionDock.vue; AppClient.vue; stories and browser tests; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-cross-side-confirm`: cross_side.js; frames/view/interaction/combat stores; QuestionCard.vue; AppClient.vue; stories; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
