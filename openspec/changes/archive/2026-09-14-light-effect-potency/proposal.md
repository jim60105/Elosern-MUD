## Why

Light spells currently share one damage/healing magnitude despite different authored coefficients. Introduce one reusable per-effect policy boundary rather than branch on spell keys or encode balance numbers in effect strings.

## What Changes

- Add validated immutable policy metadata and named authoring parameters; use LSP references before exported-symbol edits and migrate every constructor/consumer actually affected.
- Bind server-owned effect context at the existing dispatcher and apply potency in damage, heal and self-heal before the specified rounding/defense stages.
- Update the damage formula requirement and authoring guidance; preserve target validation, resource cost, nonlethal projection and no-revival behavior.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-effect-model`: The executable contract changes as specified in this proposal's delta.
- `combat-resolution`: The executable contract changes as specified in this proposal's delta.

## Impact

Implementation surfaces: `world/skills/effects.py`, `world/skills/registry.py`, `world/rules/action.py`, `world/rules/combat.py`, `world/rules/tests/test_damage_effect_handler.py`, `world/rules/tests/test_heal_effect_handler.py`.

Dependencies: None. Estimated bounded implementation: 7 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
