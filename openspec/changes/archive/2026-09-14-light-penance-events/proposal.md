## Why

Penance needs trustworthy evidence of a recent forced interaction and a second independent strike. Narrative accusations are not game state, so record a bounded committed incident and reuse conditional strike policy.

## What Changes

- Add bounded recent-evidence storage/query and one deterministic planner for existing committed forced-outcome entries, including actor snapshots and outer rollback coverage.
- Implement a policy-controlled extra independent strike with sequential HP projection, one resource/time/practice debit and ordinary nonlethal semantics.
- Verify NPC and player evidence use the same event predicate and document the 60-second world-time window without adding a command or prose classifier.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
- `recent-action-evidence`: Penance needs trustworthy evidence of a recent forced interaction and a second independent strike. Narrative accusations are not game state, so record a bounded committed incident and reuse conditional strike policy.

### Modified Capabilities
- `skill-effect-model`: The executable contract changes as specified in this proposal's delta.

## Impact

Implementation surfaces: `world/rules/action.py`, `world/rules/action_evidence.py`, `world/rules/combat.py`, `world/rules/cast_settlement.py`, `world/rules/combat_session.py`, `world/rules/surfaces.py`, `world/skills/effects.py`.

Dependencies: `light-judgment-traits`. Estimated bounded implementation: 7 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
