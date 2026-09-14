## Why

Ward requires exactly three exposure-scaled recovery ticks, and blessing needs a real timed defense rider. Extend the existing buff engine with reusable authored recovery profiles rather than make inert bounds appear implemented.

## What Changes

- Extend buff loading and the existing RulebookBuff tick path with a validated recovery-rate mode and persisted source snapshots; preserve fixed-rate and immunity behavior.
- Implement exact tick/expiry/refresh accounting and no-revival clamping without a second scheduler or wall-clock timer.
- Replace the per-key test-correspondence requirement/check with observable buff mechanics tests; exercise defense marker consumption through the existing combat rule engine.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `buff-handler-integration`: The executable contract changes as specified in this proposal's delta.

## Impact

Implementation surfaces: `world/rules/buffs.py`, `world/rules/action.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/status_display.py`, `world/rules/tests/test_buffs.py`. Recovery-rate metadata stays in the existing buff-definition owner, not `world/skills/effects.py`, so this slice does not conflict with judgment's effect-policy edits.

Dependencies: `light-effect-potency`. Estimated bounded implementation: 7 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
