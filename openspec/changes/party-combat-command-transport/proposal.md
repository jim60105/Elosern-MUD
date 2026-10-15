# Proposal: Guarded command adapters results and canonical publication

## Why

Party command schemas need a complete dispatcher cutover, token/result adapters and canonical publication without any actorless or retired-action bypass.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../combat-ratio-mitigation/batch.md) assigns every approved behavior.
- Guarded command adapters results and canonical publication. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `webclient-combat-menu`: amend the requirements owned by this bounded slice.
- `inventory-item-actions`: amend the requirements owned by this bounded slice.
- `webclient-action-dispatch`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `web/webclient/actions/combat_actions.py`, `web/webclient/actions/registry.py`, `web/webclient/actions/service_actions.py`, `web/webclient/actions/dispatcher.py`, `web/webclient/presentation/skill_use_selection.py`, `web/webclient/actions/tests/test_combat_actions.py`, `web/webclient/actions/tests/test_combat_dispatcher.py`, `web/webclient/presentation/protocol.py`, `web/static/webclient/js/elosern/protocol.js`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **12 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../combat-ratio-mitigation/batch.md). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-protocol-v7

### Code and spec conflicts within the new batch

- `party-combat-protocol-v7`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs inventory-item-actions.
- `webclient-party-command-selection`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `webclient-party-items-tactics`: No exact code-file overlap identified; shared specs inventory-item-actions, webclient-combat-menu.
- `webclient-party-exit-confirmation`: No exact code-file overlap identified; shared specs webclient-combat-menu.

### Active UI coordination

- `webclient-combat-panel-v6`: world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-stage-target-picking`: stage_targets.js; interaction/combat/view stores; ActionDock.vue; AppClient.vue; stories and browser tests; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-cross-side-confirm`: cross_side.js; frames/view/interaction/combat stores; QuestionCard.vue; AppClient.vue; stories; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
