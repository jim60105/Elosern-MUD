# Proposal: One command card for actor switching and skill draft progress

## Why

The existing stage/card batch owns presentation. The dependent party interaction needs distinguishable actor selection and stage targeting in that same card.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- One command card for actor switching and skill draft progress. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `webclient-combat-menu`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `web/static/webclient/js/elosern/combat_menu.js`, `web/webclient-app/stores/frame-resolvers.js`, `web/webclient-app/stores/elosern/combat.js`, `web/webclient-app/stores/elosern/frames.js`, `web/webclient-app/stores/elosern/view.js`, `web/webclient-app/stores/elosern/stage_targets.js`, `web/webclient-app/stores/elosern/cross_side.js`, `web/webclient-app/components/ActionDock.vue`, `web/webclient-app/AppClient.vue`, `web/webclient-app/stories/Core/AppShell.stories.js`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **14 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-command-transport
- depends-on: webclient-combat-command-card-centred
- depends-on: webclient-combat-stage-target-picking
- depends-on: webclient-combat-cross-side-confirm

### Code and spec conflicts within the new batch

- `party-combat-protocol-v7`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `party-combat-command-transport`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `webclient-party-items-tactics`: web/static/webclient/js/elosern/combat_menu.js; web/webclient-app/components/ActionDock.vue; web/webclient-app/stores/elosern/combat.js; web/webclient-app/stores/elosern/cross_side.js; web/webclient-app/stores/elosern/frames.js; web/webclient-app/stores/elosern/stage_targets.js; web/webclient-app/stories/Core/AppShell.stories.js; shared specs webclient-combat-menu.
- `webclient-party-exit-confirmation`: web/static/webclient/js/elosern/combat_menu.js; web/webclient-app/AppClient.vue; web/webclient-app/stores/elosern/combat.js; web/webclient-app/stores/elosern/frames.js; web/webclient-app/stores/elosern/view.js; web/webclient-app/stories/Core/AppShell.stories.js; shared specs webclient-combat-menu.

### Active UI coordination

- `webclient-combat-formation`: AppClient.vue; stories; browser methods; no formation geometry ownership transfer; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-figure-plates`: AppClient.vue; stories/focus integration; glyph/plate contract unchanged; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-defeated-foes`: AppClient.vue; stories; fallen/beat target state preserved; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-command-card-centred`: ActionDock.vue; AppClient.vue; stories; fixed card geometry unchanged; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-stage-target-picking`: stage_targets.js; interaction/combat/view stores; ActionDock.vue; AppClient.vue; stories and browser tests; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-cross-side-confirm`: cross_side.js; frames/view/interaction/combat stores; QuestionCard.vue; AppClient.vue; stories; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
