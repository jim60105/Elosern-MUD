# Proposal: Exact v7 actor draft read models and mirrored panel schemas

## Why

Version 6 supplies conditions and polarity only. Clients need authoritative actor choices, persistent progress and guarded submission/exit results.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Exact v7 actor draft read models and mirrored panel schemas. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `webclient-combat-menu`: amend the requirements owned by this bounded slice.
- `webclient-context-actions`: amend the requirements owned by this bounded slice.
- `webclient-context-actions-suggestions`: amend the requirements owned by this bounded slice.
- `webclient-component-showcase`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/combat_view.py`, `web/webclient/presentation/combat_panel.py`, `web/static/webclient/js/elosern/protocol/panels/combat.js`, `web/static/webclient/js/elosern/protocol/constants.js`, `web/static/webclient/js/tests/`, `web/webclient-app/stories/fixtures/`, `tests/test_panel_schema_version_parity_contract.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **11 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: equipment-weapon-damage-factor
- depends-on: party-combat-opening-routing
- depends-on: party-combat-taunt-constraints
- depends-on: party-combat-retreat-resolution
- depends-on: webclient-combat-panel-v6
- depends-on: webclient-combat-cross-side-confirm

### Code and spec conflicts within the new batch

- `party-combat-actor-commands`: world/rules/combat_view.py.
- `party-combat-command-transport`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `webclient-party-command-selection`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `webclient-party-items-tactics`: No exact code-file overlap identified; shared specs webclient-combat-menu.
- `webclient-party-exit-confirmation`: No exact code-file overlap identified; shared specs webclient-combat-menu.

### Active UI coordination

- `webclient-combat-panel-v6`: world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
