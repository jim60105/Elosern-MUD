# Spec Delta

## MODIFIED Requirements

### Requirement: compute_pleasure_gain scales base_pleasure by ratio, sensitivity, shame, and participant count
`world/rules/sexual_act_effects.py` SHALL define `compute_pleasure_gain(participant, part,
base_pleasure, ratio, participant_count) -> int`, returning `round(base_pleasure * ratio *
sensitivity_multiplier * shame_multiplier * participant_multiplier)`.

#### Scenario: A neutral participant at 普通 sensitivity and 無 shame receives exactly the ratio-scaled base
- **WHEN** `compute_pleasure_gain(participant, part, base_pleasure=10, ratio=1.0, participant_count=1)`
  is called on a participant whose sensitivity for `part` is `普通` and whose `shame` is `無`
- **THEN** it returns `10` (both multipliers are `1.0` at their floor, per the fixed synthetic
  `sexual_pleasure.yaml`)

#### Scenario: Higher sensitivity increases the gain
- **WHEN** the same call is repeated with the participant's sensitivity for `part` raised to `極高`
- **THEN** the returned value is strictly greater than the 普通 case

#### Scenario: A ratio of zero returns zero regardless of multipliers
- **WHEN** `compute_pleasure_gain(participant, part, base_pleasure=10, ratio=0.0,
  participant_count=1)` is called
- **THEN** it returns `0`

#### Scenario: The multipliers read from their declared tables
- **WHEN** the sensitivity, shame, and participant multipliers are resolved
- **THEN** the sensitivity and shame multipliers are read from `PLEASURE_CONFIG.sensitivity_multipliers`/`.shame_multipliers` (unchanged, `pleasure-gauge`-owned) keyed by `participant.sexual.sensitivity[part].level` and `participant.sexual.shame.level`, and the participant multiplier is read from this change's own `sexual_act_effects.yaml` participant-count table

#### Scenario: Authored tuning is distinct from mechanism examples
- **WHEN** tests exercise exact numerical band, delta, duration, bias or multiplier examples in this requirement
- **THEN** scoped fixed synthetic rulebook rows provide those numbers and independently known outcomes; production rows receive valid-shape/reference/intentional-invariant checks without a copied expected balance table

