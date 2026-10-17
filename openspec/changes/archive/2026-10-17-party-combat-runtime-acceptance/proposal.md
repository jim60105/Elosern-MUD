# Proposal: Real assembled browser/text party-combat acceptance

## Why

The complete feature needs exercised multi-actor and recovery/exit paths after every server and client dependency lands.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Real assembled browser/text party-combat acceptance. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `webclient-browser-verification`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `web/tests/browser/test_browser_combat_menu.py`, `web/tests/browser/test_browser_combat_rejection.py`, `web/tests/browser/browser_helpers.py`, `commands/tests/test_combat_actions.py`, `.github/browser-shards.json`, `.github/evennia-shards.json`, `docs/development/human-combat-calibration-evidence.md`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **20 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: webclient-party-exit-confirmation
- depends-on: party-combat-encounter-calibration

### Code and spec conflicts within the new batch

- `party-combat-text-commands`: commands/tests/test_combat_actions.py.
- `equipment-growth-runtime-calibration`: docs/development/human-combat-calibration-evidence.md.
- `party-combat-factor-budget-calibration`: docs/development/human-combat-calibration-evidence.md.
- `party-combat-encounter-calibration`: docs/development/human-combat-calibration-evidence.md.

### Active UI coordination

- `webclient-combat-formation`: AppClient.vue; stories; browser methods; no formation geometry ownership transfer; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-figure-plates`: AppClient.vue; stories/focus integration; glyph/plate contract unchanged; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-defeated-foes`: AppClient.vue; stories; fallen/beat target state preserved; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-command-card-centred`: ActionDock.vue; AppClient.vue; stories; fixed card geometry unchanged; spec coordination `webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-stage-target-picking`: stage_targets.js; interaction/combat/view stores; ActionDock.vue; AppClient.vue; stories and browser tests; spec coordination `webclient-combat-menu; webclient-contextual-hud`. Consume its landed contract first; do not edit its proposal.
- `webclient-combat-cross-side-confirm`: cross_side.js; frames/view/interaction/combat stores; QuestionCard.vue; AppClient.vue; stories; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
