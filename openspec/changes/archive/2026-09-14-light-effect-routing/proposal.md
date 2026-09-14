## Why

Mixed damage/recovery spells need different recipients per effect, but the current dispatcher sends one full validated list to every handler. Add opt-in effect audiences without reintroducing ally-only skill targeting.

## What Changes

- Extend the existing policy validation with audience values and a pure audience planner shared by preflight and final resolution.
- Apply routed subsets at Step 5 and include actor-only recipient state in snapshots, practice semantics and EventLog attribution without adding implicit bystanders.
- Update the targeting-related requirements and relevant cast documentation to separate selection from effect delivery; keep generic friendly fire and enemy healing reachable.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-effect-model`: The executable contract changes as specified in this proposal's delta.
- `skill-registry`: The executable contract changes as specified in this proposal's delta.
- `action-resolution-pipeline`: The executable contract changes as specified in this proposal's delta.
- `heal-effect-handler`: The executable contract changes as specified in this proposal's delta.

## Impact

Implementation surfaces: `world/skills/effects.py`, `world/skills/registry.py`, `world/rules/action.py`, `world/rules/targeting.py`, `world/rules/tests/test_targeting.py`, `world/rules/tests/test_action_resolver.py`.

Dependencies: `light-effect-potency`. Estimated bounded implementation: 7 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
