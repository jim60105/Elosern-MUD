## Why

The light tree requires target-dependent bonuses, conditional defense bypass and a maximum-HP damage component. These belong to reusable damage policies and explicit target facts, not name matching or a light-only combat routine.

## What Changes

- Add the pure canonical target-fact reader and deterministic combat_traits writer; validate and carry the optional field through each real import/spawn path without modifying age semantics.
- Extend the same EffectPolicy with typed conditional damage and max-HP parameters; evaluate predicates without materializing handlers or accepting request-provided facts.
- Update damage computation and source attribution through existing staging, nonlethal, EventLog and rollback paths; verify neutral policy equals ordinary damage.
- **BREAKING** where authored policy or removed light data replaces old behavior; no compatibility aliases, migrations, or interim fake effects.
- Verification uses synthetic behavior tests and targeted runtime scenarios, never light catalog key/count/value contracts.

## Capabilities

### New Capabilities
- `combat-target-traits`: The light tree requires target-dependent bonuses, conditional defense bypass and a maximum-HP damage component. These belong to reusable damage policies and explicit target facts, not name matching or a light-only combat routine.

### Modified Capabilities
- `skill-effect-model`: The executable contract changes as specified in this proposal's delta.
- `combat-resolution`: The executable contract changes as specified in this proposal's delta.

## Impact

Implementation surfaces: `world/skills/effects.py`, `world/rules/combat.py`, `world/rules/target_facts.py`, `world/rules/traits.py`, `typeclasses/entities.py`, `world/imports`, `world/quests/scene_builder.py`, `world/quests/compile.py`, `world/maps/wilderness_population.py`.

Dependencies: `light-effect-potency`. Estimated bounded implementation: 8 engineer-hours including focused tests and integration, no project-wide suite. This is one independently reviewable workday slice; it does not ship incomplete catalog entries.

This turn creates planning artifacts and authorized lore corrections only. Do not apply, archive, sync main specs, create feature branches or merge until the user requests it. The complete dependency/conflict schedule and shared interface ownership are in `../light-spell-catalog/design.md`.
