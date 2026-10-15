# Spec Delta

## MODIFIED Requirements

### Requirement: Damage multiplier is banded by margin of success, with a magnitude-only critical on a
natural 100
Damage SHALL be
`int(max(round(effective_attack_stat * roll_multiplier * effect_potency * matched_multiplier) * K / (K + max(0, effective_defense)) + rider, floor))`
followed by the authored scale and final floor, where `K` is the rulebook's finite positive
`damage.mitigation_k`. `roll_multiplier` is `crit_multiplier` on a raw `roll_d100()` of 100, else
`solid_hit_multiplier` at margin >= `solid_hit_margin`, else `base_multiplier`.

#### Scenario: The damage rulebook declares every band constant
- **WHEN** the combat rulebook is loaded
- **THEN** its `damage` section declares `crit_multiplier`, `solid_hit_margin`,
  `solid_hit_multiplier`, `base_multiplier`, and `floor`

#### Scenario: A bare hit uses the base multiplier
- **WHEN** an attack hits with a margin of success below `solid_hit_margin` and the raw roll is not 100
- **THEN** damage is computed using `base_multiplier`

#### Scenario: The calculation runs only after a successful to-hit check

- **WHEN** damage computation is reached
- **THEN** it runs only when the to-hit check (above) already succeeded — a natural 100 does not cause a miss to become a hit

#### Scenario: A comfortable hit uses the solid-hit multiplier
- **WHEN** an attack hits with a margin of success at or above `solid_hit_margin`
- **THEN** damage is computed using `solid_hit_multiplier`

#### Scenario: A natural 100 always applies the critical multiplier regardless of margin
- **WHEN** an attack's raw, unmodified `roll_d100()` result is exactly 100 and the attack hits
- **THEN** damage is computed using `crit_multiplier`, even if the margin of success would otherwise
  have qualified only for `base_multiplier`

#### Scenario: Damage never drops below the floor
- **WHEN** `the mitigated attack component plus rider` computes to a value at or
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
- **THEN** both hits use zero defense for ratio mitigation while the identical coefficient without bypass differs by the
  targets' defense, and the multiplier-with-empty-predicate authoring still raises at construction

#### Scenario: Divert runs after the full formula and pays from the named gauge
- **WHEN** a synthetic divert profile (fraction, cap) is active on a target whose authored hit amount
  (post-ratio, post-rider, post-scale) exceeds the fraction's product with the target's budget
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

#### Scenario: effect_potency is the validated per-effect coefficient

- **WHEN** damage is computed for a configured effect
- **THEN** `effect_potency` is the validated per-effect coefficient, defaulting to 1.0

#### Scenario: A conditional policy uses the matched attack multiplier once

- **WHEN** a declared conditional policy's damage is computed
- **THEN** the attack component additionally uses the matched attack multiplier once

#### Scenario: Defense is zero only under a matched or unconditional bypass

- **WHEN** a declared conditional policy resolves defense
- **THEN** defense is zero only when its configured bypass predicate matches or the policy declares the unconditional execution-tier bypass — `bypass_defense=True` with an empty predicate, which validates at construction (an attack multiplier with an empty predicate stays invalid)

#### Scenario: The maximum-HP component is added after defense mitigation

- **WHEN** a declared conditional policy with a maximum-HP fraction hits
- **THEN** floor(max_hp * declared_fraction) is added after ratio mitigation on a successful hit

#### Scenario: Existing ordering rules follow the new components

- **WHEN** damage components are combined
- **THEN** the existing damage floor, freeform magnitude scaling and final floor follow these components, and unconfigured effects retain the ordinary formula

#### Scenario: Divert profiles are validated buff profiles with gauge, fraction, and cap

- **WHEN** the damage stage consults divert handling after the full authored amount pipeline completes
- **THEN** it reads only the target's ACTIVE validated divert profiles — a `modifiers.divert` buff profile naming a gauge, a fraction in (0,1] and a cumulative cap

#### Scenario: Each divert converts a bounded share of the residual

- **WHEN** an active divert profile applies to a residual
- **THEN** it converts `min(round(residual * fraction), cap − consumed, owner's current gauge amount)` of the RESIDUAL into a payment from the owner's gauge through the canonical resource writer, the reduced HP amount is the only HP write staged, and the payment is attributed to the profile's persisted grant-time source

#### Scenario: Diversion never fakes HP loss and never runs on a miss

- **WHEN** damage is diverted, a miss or zero-amount hit lands, or a diverting commit is rolled back
- **THEN** diverted damage is not reported as HP loss to loss-driven feedback, a miss or zero-amount hit neither stages a divert nor consumes budget, and a rolled-back commit restores the gauge payment and consumed budget

#### Scenario: Budget accounting follows the retain-or-replace posture

- **WHEN** consumed-budget accounting is loaded
- **THEN** it follows the loaded retain-or-replace posture: a fresh cast's grant replaces the instance budget, a data-omitting refresh retains it

#### Scenario: Nonlethal projection runs before defeat consumers

- **WHEN** a diverting or rider-bearing hit approaches zero
- **THEN** the existing nonlethal projection applies before defeat/knockout event consumers

## ADDED Requirements

### Requirement: Ratio mitigation clamps negative defense and shares settlement and estimation
Physical and magic damage on both sides SHALL use the same ratio retention K/(K+max(0, adjusted_defense)). Explicit defense bypass SHALL use zero defense. K SHALL be finite and positive; invalid rulebook values SHALL fail load. Attack rounding, post-mitigation rider, pre-scale floor, half-up scale and final hit floor SHALL retain their defined order.

#### Scenario: Independent ratio example
- **WHEN** K is 40, rounded pre-mitigation attack is 60 and defense is 20
- **THEN** both damage schools resolve 40 before riders, scale or tactical reduction, independently of registry magnitudes

#### Scenario: Negative defense and load failures
- **WHEN** defense is negative, or K is zero, negative, bool or nonfinite
- **THEN** negative defense behaves as zero, and every invalid K declaration rejects at load

#### Scenario: Miss and shared expectation
- **WHEN** a strike misses or an estimator evaluates the same successful fixed-roll strike
- **THEN** a miss causes no strike damage and the estimator equals settlement for bypass, conditional multiplier, rider and scale cases

