## MODIFIED Requirements

### Requirement: Target selection differs by archetype and is deterministic under a fixed seed
`world/rules/monster_behaviour.py` SHALL select a single target by the acting monster's `BehaviourProfile.target_strategy` — `"lowest_hp"` (current `hp.value`) or `"highest_effective_power"` (change 9's `effective_power()`) — breaking an exact tie by drawing from `dice.roll_d100()`, never Python's `random` module directly. The SINGLE-target candidate set for STRIKE-class (physical-school damage) selections SHALL exclude enemies holding a live positional-marker instance (state-only, dice-free — the same metric and tie-break machinery applies to the remaining candidates): because skill choice can follow target choice, an acting monster whose owned SINGLE-target damage kit is exclusively strike-class SHALL apply the exclusion at candidate selection, while a monster owning a magic-school SINGLE-target damage skill MAY keep displaced candidates for that magic kit (magic reachability is ratified unaffected; the step-4a resolution gate remains the sole authority for strike-class pairings). When the strike-class candidate set is empty while the actor holds no reachable magic SINGLE kit, the policy SHALL return no action for this round, deterministic and reproducible under a fixed seed exactly like the no-living-enemies case. The AREA shorthand candidate set SHALL keep displaced candidates (area reachability is unaffected). The delegated `default_attack_policy`'s strike-class candidate set SHALL apply the identical positional exclusion.

#### Scenario: lowest_hp strategy selects the enemy with the least current hp
- **WHEN** target selection runs with `target_strategy: lowest_hp` against a set of living enemies with distinct `hp.value`s
- **THEN** the enemy with the smallest `hp.value` is selected

#### Scenario: highest_effective_power strategy selects the enemy with the greatest effective_power
- **WHEN** target selection runs with `target_strategy: highest_effective_power` against a set of living enemies with distinct `effective_power()` values
- **THEN** the enemy with the greatest `combat.effective_power()` value is selected

#### Scenario: An exact tie is broken by a seeded roll, reproducibly
- **WHEN** target selection runs against two enemies with exactly equal values under the active strategy's metric, under a fixed RNG seed
- **THEN** the same enemy is selected every time the identical seed and battlefield state are replayed, and the selection is made via a call to `dice.roll_d100()`, not `random.choice()` or equivalent

#### Scenario: Displaced enemies leave the strike-class candidate set without extra dice
- **WHEN** a strike-class-only monster's target selection runs against one displaced and one undisplaced living enemy under a fixed seed, and separately against a set where every living enemy is displaced, and separately a magic-owning caster monster selects against the same mixed set
- **THEN** the first case selects the undisplaced enemy with no additional randomness draw beyond the shipped tie-break path, the second case yields no action request, and the caster monster's magic-school single-target selection keeps the displaced candidate reachable — replaying the identical seed and state reproduces every outcome

#### Scenario: No target selection call reads combat_modifiers or rolls outside dice.roll_d100
- **WHEN** `_choose_target()`'s implementation is inspected
- **THEN** the only randomness source it references is `world.rules.dice.roll_d100()`
