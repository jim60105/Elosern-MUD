# Proposal: Initiative-priority Taunt and legal enemy decision constraints

## Why

Taunt must constrain enemy legal selection before utility scoring without inventing action capabilities or redirecting an already selected effect.

## What Changes

- **BREAKING** pre-release behavior follows the approved `docs/superpowers/specs/2026-10-15-party-combat-and-equipment-growth-design.md` (approved source commit `8c47578d`). This change owns design coverage identified in [the batch contract](../combat-ratio-mitigation/batch.md).
- Initiative-priority Taunt and legal enemy decision constraints. The delta requirements define acceptance; `design.md` fixes the integration boundary and `tasks.md` includes implementation, focused verification and documentation.
- No compatibility layer, stored-data migration, implementation in this proposal, or edits to active UI proposals.

## Capabilities

### New Capabilities

None. Reuse the existing capability owners.

### Modified Capabilities

- `player-combat-session`: extend or amend the behavior owned by this bounded slice.
- `monster-ai-legal-candidates`: extend or amend the behavior owned by this bounded slice.

## Impact

Affected implementation/test surfaces (planned only): `world/rules/combat/rounds.py`, `world/rules/combat_session/policies.py`, `world/rules/monster_ai/candidates.py`, `world/rules/monster_ai/estimation.py`, `world/rules/monster_ai/snapshot.py`, `world/rules/action/gates.py`, `world/skills/effects/polarity.py`.
Affected main-spec requirements are supplied as deltas, with canonical traceability IDs and affected test/fixture/shard ownership updated during implementation. The batch completion gate forbids shipping partial companion item flow or missing client/text paths.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, required documentation and integration. The task estimates sum to this total. This estimate reuses the inspected session transaction, preview, scalar, item, client menu and calibration patterns; it excludes no approved behavior owned here. Full CI-owned browser/evidence runs are not local work. Prerequisite contracts must already be landed before this change starts.

## Batch: party combat and equipment growth

Implementation order: **8 of 18** in the new batch, with active UI prerequisites interleaved as declared in [the complete dependency/conflict matrix](../combat-ratio-mitigation/batch.md). All new proposals are context on the primary branch; later apply work owns implementation branches.

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
