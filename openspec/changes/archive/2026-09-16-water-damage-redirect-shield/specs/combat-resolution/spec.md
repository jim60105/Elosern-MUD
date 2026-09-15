## MODIFIED Requirements

### Requirement: Damage multiplier is banded by margin of success, with a magnitude-only critical on a
natural 100
`world/rules/rulebook/combat.yaml`'s `damage` section SHALL declare `crit_multiplier`,
`solid_hit_margin`, `solid_hit_multiplier`, `base_multiplier`, and `floor`. Damage SHALL be computed as
`max(round(effective_attack_stat * roll_multiplier * effect_potency) - effective_defense, floor)`, where
`roll_multiplier` is `crit_multiplier` if the raw, unmodified `roll_d100()` result equals 100,
`solid_hit_multiplier` if the margin of success is at least `solid_hit_margin`, and `base_multiplier`
otherwise. `effect_potency` SHALL be the validated per-effect coefficient, defaulting to 1.0. For a declared conditional policy, the attack component SHALL additionally use the matched attack multiplier once, defense SHALL be zero only when its configured bypass predicate matches **or the policy declares the unconditional execution-tier bypass — `bypass_defense=True` with an empty predicate, which SHALL validate at construction (an attack multiplier with an empty predicate stays invalid)**, and floor(max_hp * declared_fraction) SHALL be added after defense subtraction on a successful hit. The existing damage floor, freeform magnitude scaling and final floor SHALL follow these components; unconfigured effects retain the ordinary formula. After the full authored amount pipeline completes, the damage stage SHALL consult the target's ACTIVE validated divert profiles (a `modifiers.divert` buff profile naming a gauge, a fraction in (0,1] and a cumulative cap): each profile in definition-key-ascending order converts `min(round(residual * fraction), cap − consumed, owner's current gauge amount)` of the RESIDUAL into a payment from the owner's gauge through the canonical resource writer, with the reduced HP amount being the only HP write staged and the payment attributed to the profile's persisted grant-time source. Diverted damage SHALL NOT be reported as HP loss to loss-driven feedback, a miss or zero-amount hit SHALL neither stage a divert nor consume budget, a rolled-back commit SHALL restore the gauge payment and consumed budget, and the consumed-budget accounting SHALL follow the loaded retain-or-replace posture (a fresh cast's grant replaces the instance budget; a data-omitting refresh retains it). Existing nonlethal projection SHALL apply before defeat/knockout event consumers. This calculation SHALL only run when the to-hit check (above) already succeeded — a natural
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

#### Scenario: Unconditional execution bypass ignores any target's defense
- **WHEN** a synthetic policy with `bypass_defense=True` and an empty predicate damages a high-defense
  and a low-defense target, and separately authoring attaches an attack multiplier to an empty predicate
- **THEN** both hits subtract no defense while the identical coefficient without bypass differs by the
  targets' defense, and the multiplier-with-empty-predicate authoring still raises at construction

#### Scenario: Divert runs after the full formula and pays from the named gauge
- **WHEN** a synthetic divert profile (fraction, cap) is active on a target whose authored hit amount
  (post-defense, post-rider, post-scale) exceeds the fraction's product with the target's budget
- **THEN** exactly `round(amount × fraction)` capped by remaining budget and current gauge is paid
  from the gauge through the canonical writer, HP drops only by the residual, and the same roll
  without the profile delivers the full authored HP amount

#### Scenario: Budget, gauge shortage and expiry bound the divert
- **WHEN** successive hits exhaust the cumulative cap, one hit exceeds the holder's remaining gauge,
  and a later hit lands after expiry
- **THEN** each divert equals the minimum of its three bounds, cap exhaustion stops all further
  diversion while the duration lives, an expiry restores full damage, and no stage ever diverts more
  than the incoming residual

#### Scenario: Stacked profiles follow one deterministic residual order
- **WHEN** two synthetic divert profiles with different definition keys are active on one hit
- **THEN** they apply in definition-key-ascending order each against the previous residual, the two
  payments plus final HP loss sum exactly to the incoming amount, and repeated resolution never
  reorders them

#### Scenario: Feedback and defeat see only the HP residual
- **WHEN** a diverting hit would otherwise cross the holder's HP through zero and a loss-driven
  reaction listener is qualified
- **THEN** the listener and any defeat projection observe only `amount − diverted`, the diverted MP
  payment is attributed to the profile's grant-time source, and a commit failure restores HP, gauge
  and consumed budget together
