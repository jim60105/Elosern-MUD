## Why

Change 10b gives monsters deterministic target and attack-skill choices, while change 10c supplies
the universal `flee` action and the sole writer for `Battlefield.fled`; neither change owns the
policy question of when a monster should stop attacking and attempt escape. Without this follow-up,
every monster still fights to death unless an external caller explicitly makes it flee, so the
archetype distinctions introduced by 10b remain incomplete.

## What Changes

- Extend each rulebook-defined monster behaviour archetype with a tunable flee HP-ratio threshold;
  YAML `null` disables voluntary flight for archetypes intended to fight to the death.
- Extend `monster_behaviour_policy()` with a deterministic flee decision evaluated before attack
  selection: a living, non-fled monster at or below its resolved archetype threshold returns an
  `ActionRequest` for change 10c's innate `flee` skill.
- Import 10c's canonical `FLEE_SKILL_KEY` from `world.rules.disengage`, guaranteeing the skill and
  effect-handler registrations are loaded in production and avoiding a duplicated string key.
- Keep action execution entirely within the existing `ActionResolver`: the policy neither decides
  whether the attempt succeeds nor writes `Battlefield.fled` or any entity state.
- Add rulebook validation and deterministic unit, golden, and integration tests covering threshold
  boundaries, tier defaults, per-instance archetype overrides, failed-attempt opportunity cost, and
  successful removal from subsequent combat decisions.
- Add roadmap item 10d after 10c and clarify the ownership chain: 10b owns attack policy, 10c owns
  generic disengage execution, and 10d composes both into monster flee decisions.

## Capabilities

### New Capabilities

- `monster-flee-policy`: archetype-driven flee thresholds and the deterministic policy that emits a
  resolver-ready `flee` `ActionRequest` without mutating state.

### Modified Capabilities

None. The 10b and 10c capability deltas are still active rather than main specifications; this
follow-up composes their public contracts without changing either contract.

## Impact

- **Modified implementation, when applied**: `world/rules/monster_behaviour.py`,
  `world/rules/rulebook/monster_behaviour.yaml`, and focused tests under `world/rules/tests/`.
- **Depends on**: 10b (`monster-behaviour`) for profile resolution and
  `monster_behaviour_policy()`; 10c (`combat-disengage`) for the innate `flee` `SkillDef`, its
  canonical `FLEE_SKILL_KEY`, `disengage` effect handler, atomic `Battlefield.fled` mutation, and
  combat exclusion behavior.
- **Architecture**: remains deterministic and offline-capable. Balance values live in YAML; the
  policy returns an `ActionRequest`, and only `world/rules/` through `ActionResolver` commits state.
- **Excluded**: player flee UX, flee success formulas, new effects or rejection reasons, morale,
  allies influencing thresholds, AI/network calls, migrations, and backward-compatibility layers.
