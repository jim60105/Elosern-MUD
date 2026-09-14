## Why

The documented clergy loop requires damage/debuff feedback and equipment-independent recovery benefits. Bind these through reusable event reactions and recovery adjustments, not profession-name checks or direct writes from skill data.

## What Changes

- Extend typed reaction validation for actual HP-loss and accepted new-debuff events; carry immutable source tier through direct and periodic effects.
- Integrate each real damage/debuff writer once, using LSP/codegraph to enumerate sinks; include item, rulebook and world-clock paths and every reaction-touched rollback surface.
- Add a reusable recovery-only modifier/snapshot path using existing combat rule evaluation, without applying sacramental bonuses twice.
- Prove behavior with synthetic passive declarations and document source-tier and conferral semantics.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
- `damage-state-feedback`: The documented clergy loop requires damage/debuff feedback and equipment-independent recovery benefits. Bind these through reusable event reactions and recovery adjustments, not profession-name checks or direct writes from skill data.

### Modified Capabilities
None.

## Impact

Implementation surfaces: `world/rules/state_reactions.py`, `world/rules/rulebook/state_reactions.yaml`, `world/rules/combat.py`, `world/rules/buffs.py`, `world/rules/items.py`, `world/rules/sexual_transitions.py`, `world/rules/clock.py`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/surfaces.py`.

Dependencies: `light-divinity-tier`, `light-sustained-recovery`, `light-climax-empowerment`. Estimated bounded implementation: 8 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
