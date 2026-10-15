# Proposal: Initiative-priority Taunt and legal enemy decision constraints

## Why

Taunt must constrain enemy legal selection before utility scoring without inventing action capabilities or redirecting an already selected effect.

## What Changes

- **BREAKING** pre-release behavior follows the complete approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md`, source commit `8c47578d`. [The batch contract](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract) assigns every approved behavior.
- Initiative-priority Taunt and legal enemy decision constraints. Delta requirements define acceptance; design.md fixes integration decisions and tasks.md includes implementation, focused evidence and required documentation.
- No compatibility layer, stored-data migration, implementation in this proposal or edits to existing active UI proposals.

## Capabilities

### New Capabilities

None. Reuse existing capability ownership.

### Modified Capabilities

- `player-combat-session`: amend the requirements owned by this bounded slice.
- `monster-ai-legal-candidates`: amend the requirements owned by this bounded slice.

## Impact

Planned implementation/test surfaces: `world/rules/combat/rounds.py`, `world/rules/combat_session/policies.py`, `world/rules/monster_ai/candidates.py`, `world/rules/monster_ai/estimation.py`, `world/rules/monster_ai/snapshot.py`, `world/rules/action/gates.py`, `world/skills/effects/polarity.py`.
Canonical traceability annotations, affected test/fixture/shard ownership and existing documentation change with implementation. The assembled acceptance gate forbids missing companion item/tactical flow, real balance evidence or client/text parity.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. Task estimates sum to this total. It reuses the inspected session, preview, scalar, item, client and calibration patterns. Prerequisites must already be landed. Full CI-owned browser/evidence execution is separate from focused local verification; no approved behavior owned here is excluded.

## Batch: party combat and equipment growth

Declared implementation order: **8 of 20** new changes, with the active UI prerequisites interleaved in [the complete order/conflict matrix](../../../docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md#11-batch-planning-contract). This is the post-review bounded split; the matrix records adopted findings. Planning commits remain on primary; later apply work owns implementation branches.

- depends-on: party-combat-defend-dodge
- depends-on: webclient-combat-panel-v6

### Code and spec conflicts within the new batch

- `combat-ratio-mitigation`: world/rules/monster_ai/estimation.py.
- `equipment-weapon-damage-factor`: world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py.
- `party-combat-actor-commands`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-persistent-drafts`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-atomic-rounds`: world/rules/combat/rounds.py; world/rules/combat_session/policies.py; shared specs player-combat-session.
- `party-combat-opening-routing`: world/rules/combat_session/policies.py; shared specs player-combat-session.
- `party-combat-defend-dodge`: world/rules/combat/rounds.py; world/rules/monster_ai/estimation.py; world/rules/monster_ai/snapshot.py.
- `party-combat-confirmed-surrender`: No exact code-file overlap identified; shared specs player-combat-session.
- `party-combat-retreat-resolution`: world/rules/combat/rounds.py; world/rules/combat_session/policies.py; shared specs player-combat-session.
- `party-combat-text-commands`: No exact code-file overlap identified; shared specs player-combat-session.

### Active UI coordination

- `webclient-combat-panel-v6`: world/rules/combat_view.py; web/webclient/presentation/combat_panel.py; protocol validators/fixtures; world/skills/effects/polarity.py; spec coordination `webclient-combat-menu`. Consume its landed contract first; do not edit its proposal.
