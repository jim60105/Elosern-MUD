## MODIFIED Requirements

### Requirement: Damage multiplier is banded by margin of success, with a magnitude-only critical on a
natural 100
`world/rules/rulebook/combat.yaml`'s `damage` section SHALL declare `crit_multiplier`,
`solid_hit_margin`, `solid_hit_multiplier`, `base_multiplier`, and `floor`. Damage SHALL be computed as
`max(round(effective_attack_stat * roll_multiplier * effect_potency) - effective_defense, floor)`, where
`roll_multiplier` is `crit_multiplier` if the raw, unmodified `roll_d100()` result equals 100,
`solid_hit_multiplier` if the margin of success is at least `solid_hit_margin`, and `base_multiplier`
otherwise. `effect_potency` SHALL be the validated per-effect coefficient, defaulting to 1.0. For a declared conditional policy, the attack component SHALL additionally use the matched attack multiplier once, defense SHALL be zero only when its configured bypass predicate matches, and floor(max_hp * declared_fraction) SHALL be added after defense subtraction on a successful hit. The existing damage floor, freeform magnitude scaling and final floor SHALL follow these components; unconfigured effects retain the ordinary formula. Existing nonlethal projection SHALL apply before defeat/knockout event consumers. This calculation SHALL only run when the to-hit check (above) already succeeded — a natural
100 SHALL NOT cause a miss to become a hit.

#### Scenario: A bare hit uses the base multiplier
- **WHEN** an attack hits with a margin of success below `solid_hit_margin` and the raw roll is not 100
- **THEN** damage is computed using `base_multiplier`

#### Scenario: A comfortable hit uses the solid-hit multiplier
- **WHEN** an attack hits with a margin of success at or above `solid_hit_margin`
- **THEN** damage is computed using `solid_hit_multiplier`

#### Scenario: A natural 100 always applies the critical multiplier regardless of margin
- **WHEN** an attack's raw, unmodified `roll_d100()` result is exactly 100 and the attack hits
- **THEN** damage is computed using `crit_multiplier`, even if the margin of success would otherwise
  have qualified only for `base_multiplier`

#### Scenario: Damage never drops below the floor
- **WHEN** `effective_attack_stat * roll_multiplier - effective_defense` computes to a value at or
  below zero
- **THEN** the applied damage equals `damage.floor`, never zero or negative

#### Scenario: A miss deals no damage and applies no floor
- **WHEN** the to-hit check fails
- **THEN** no damage is applied to the target's `hp`, and the damage floor does not apply (a miss is
  not a "zero-damage hit")

#### Scenario: Conditional damage preserves nonlethal outcome
- **WHEN** a configured defense bypass and maximum-HP component would cross a protected target below zero
- **THEN** final HP is 1 with one knockout outcome and no ordinary defeat

#### Scenario: Freeform scaling follows every damage component
- **WHEN** a freeform-scaled cast of a skill carrying a maximum-HP component hits
- **THEN** the declared freeform magnitude scaling applies after the maximum-HP component is added, so the rider is scaled by the same stage rather than remaining unscaled
