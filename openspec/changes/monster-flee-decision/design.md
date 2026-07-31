## Context

Roadmap item 10b (`monster-behaviour`) resolves a monster's YAML-backed `BehaviourProfile` and
returns attack `ActionRequest`s. Item 10c (`combat-disengage`) deliberately owns only the universal
mechanism: it registers the innate `flee` skill, resolves the agility contest, and atomically adds a
successful actor to `Battlefield.fled`. Its D-7 names a later policy branch as the remaining seam.

This change is roadmap item 10d and depends on both. It completes the sequence without moving
responsibility across boundaries: 10b still owns attack decisions, 10c still owns action execution,
and 10d decides when a monster asks the resolver to use the mechanism.

## Goals / Non-Goals

**Goals:**

- Make voluntary monster flight differ by the same YAML-defined archetype already selected by 10b.
- Evaluate one deterministic, current-to-maximum HP threshold before attack selection.
- Return the exact self-targeted `flee` request shape and battlefield event context required by 10c.
- Preserve the resolver and deterministic-core single-writer boundaries.
- Validate all new rulebook values and cover tier defaults, overrides, boundary behavior, and
  end-to-end resolution with deterministic tests.

**Non-Goals:**

- Changing the flee success formula, `Battlefield.fled` semantics, or player command UX from 10c.
- Adding morale, surrender, group coordination, threat comparison, cooldown state, buffs, or a
  failed-flee penalty beyond losing the turn.
- Changing 10b's existing target and damage-skill selection behavior above the threshold.
- Calling an LLM/network service, mutating state inside the policy, adding persistence, migrations,
  or backward-compatibility handling.

## Decisions

### D-1. Add one nullable `flee_hp_fraction` leaf to every behaviour archetype

`monster_behaviour.yaml["archetypes"][key]` gains `flee_hp_fraction`, represented as either a
number in the inclusive range `[0.0, 1.0]` or YAML `null`. `null` means the archetype never
voluntarily flees. Numeric values are the inclusive current-to-maximum HP boundary at which it
attempts to flee.

The field is added to frozen `BehaviourProfile` and therefore follows 10b's existing
instance-override and tier-default lookup without a second mapping. Concrete values, including
which archetypes never flee, are balance data and belong only in YAML under design decision D9.

The initial rulebook values are provisional balance assumptions:

| Archetype | `flee_hp_fraction` | Intent |
|---|---:|---|
| `instinctive` | `0.35` | Self-preserving low-tier creatures flee readily. |
| `pack_hunter` | `0.20` | Coordinated hunters hold longer but retreat when badly hurt. |
| `brute` | `0.10` | Brutes withdraw only when near defeat. |
| `tactical_caster` | `0.25` | Tactical creatures preserve themselves earlier than brutes. |
| `apex_predator` | `null` | Calamity-tier apex creatures do not voluntarily flee. |

They preserve the intended ordering (`instinctive` flees earliest, then `tactical_caster`,
`pack_hunter`, and `brute`, while `apex_predator` does not voluntarily flee) but are not derived
constants. Change 16's deterministic combat-balance playtesting may tune the YAML values without
changing the policy structure.

Alternative considered: a `can_flee` boolean plus a threshold. A nullable threshold expresses both
facts without redundant states such as `can_flee: false` paired with a non-null threshold.

### D-2. Compute the ratio from stored gauge values without advancing trait timers

The predicate reads current HP through `combat._stored_hp(entity)` and maximum HP through
`combat._max_hp(entity)`, the accessors already used by the combat core. It does not read display
traits, call `effective_value("hp")`, or touch the gauge's time-aware public value accessor. The
branch is true exactly when:

```python
profile.flee_hp_fraction is not None
and combat._max_hp(entity) > 0
and combat._stored_hp(entity) / combat._max_hp(entity) <= profile.flee_hp_fraction
```

The inclusive comparison makes the configured boundary directly testable. An impossible or corrupt
non-positive maximum does not trigger voluntary flight; normal combat construction already provides
positive HP gauges, while rulebook validation handles only configuration data.

Alternative considered: absolute HP. It would make one value mean radically different things across
the setting's three-order-of-magnitude stat scale and violate the archetype-level tuning intent.

### D-3. Flee selection precedes attack selection but follows the no-enemy check

`monster_behaviour_policy()` first preserves its existing non-monster delegation and living-enemy
lookup. If no living, non-fled enemy exists, it returns `None`; there is no encounter to flee.
Otherwise it resolves the profile and checks D-2 before enumerating affordable damage skills or
consuming any seeded tie-break roll.

This order guarantees a threshold-triggered monster can flee even if it owns no damage skill, and
that adding the branch cannot shift attack dice or tie-break sequences on turns above the threshold.
A failed attempt still consumes that monster's action because the provider returns exactly one
request per turn; it may try again on a later turn while the predicate remains true.

Alternative considered: attempt an attack when no damage skill is affordable, then flee as a
fallback. That makes flight depend accidentally on skill loadout rather than the explicit archetype
threshold.

### D-4. The policy constructs a complete resolver-ready request and never executes it

`monster_behaviour.py` imports `FLEE_SKILL_KEY` from `world.rules.disengage` and uses that constant
instead of spelling `"flee"` locally. Importing the owner module guarantees 10c's `SkillDef` and
effect-handler registration side effects have run before a request can be resolved; behavior does
not depend on an incidental import by a command or test.

When D-2 is true, the policy returns:

```python
ActionRequest(
    actor=entity,
    skill_key=FLEE_SKILL_KEY,
    targets=[entity],
    context=BattlefieldActionContext(
        battlefield,
        event_context={"battlefield": battlefield},
    ),
)
```

The event-context entry is required by 10c's registered `disengage` handler. The policy does not call
that handler, roll flee success, add to `Battlefield.fled`, or alter any entity surface.
`run_round()` or `resolve_overwhelm()` remains responsible for passing the request to
`ActionResolver.resolve()`, which is the only route to the atomic writer.

Alternative considered: call a helper in `disengage.py` directly. That would bypass ownership,
targeting, capability, EventLog, time-cost, and rollback steps and violate the single-writer design.

### D-5. Validate the expanded profile table at module load

A focused loader/validator SHALL reject a non-mapping archetype table, missing or extra profile
fields, unknown tier-default references, invalid existing strategy values, non-boolean area
preferences, and `flee_hp_fraction` values that are neither `null` nor real numbers in `[0, 1]`.
Boolean values are rejected as fractions even though Python treats `bool` as an `int`.
Every such failure raises `MonsterBehaviourConfigError`, a `ValueError` subclass defined in
`monster_behaviour.py`, with a stable `invalid monster behaviour rulebook:` message prefix.

Validation happens before `BEHAVIOUR_PROFILES` is constructed, so malformed tuning fails loudly and
deterministically rather than producing a mid-combat branch error. This extends 10b's configuration
contract rather than creating a second config file.

## Risks / Trade-offs

- **[Risk] A monster below its threshold can repeatedly spend turns on failed attempts.** → This is
  the intended stateless policy and gives failure the same opportunity cost as a missed attack.
  Cooldowns or escalating morale would require new mutable state and are deferred to playtesting.
- **[Risk] Current HP fraction alone cannot represent allies dying or overwhelming opposition.** →
  Accepted for the narrow follow-up; it is stable across the setting's stat scale and keeps all
  tuning understandable. Later morale work can be proposed independently.
- **[Risk] Adding a required profile field makes incomplete YAML fail at import time.** → Intentional
  for an unreleased project: all shipped archetypes are updated atomically and no compatibility
  default conceals missing balance data.
- **[Risk] Importing 10c's owner module from 10b's module introduces a dependency that did not exist
  in the original 10b change.** → This is why 10d explicitly depends on both 10b and 10c. Importing
  `FLEE_SKILL_KEY` makes the order deterministic, keeps registration owned by 10c, and avoids a
  second bootstrap or duplicated key.
- **[Risk] Initial flee fractions are uncalibrated.** → They are explicitly provisional YAML balance
  data with an intentional relative ordering; change 16's deterministic combat-balance pass can tune
  them without changing code or the decision contract.
