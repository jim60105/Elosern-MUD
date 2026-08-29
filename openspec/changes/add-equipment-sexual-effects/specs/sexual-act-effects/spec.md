## ADDED Requirements

### Requirement: The pleasure funnel applies the equipment pleasure percent

`compute_pleasure_gain()` SHALL accept one signed `pleasure_percent`
contributed by the caller from the pure equipment accessor
(`equipment_pleasure_gain`, malformed storage → 0 — never the combat
evaluator, whose output key-set SHALL remain unchanged) and compute exactly
`max(round(base × ratio × sensitivity × shame × crowd × (1 +
pleasure_percent / 100)), 0)` with a single final rounding. The sensitivity
ladder, shame ladder, virginity, and the eleven lifetime counters SHALL be
unchanged by this fold, and `pleasure_percent = 0` SHALL reproduce the
pre-change results exactly.

#### Scenario: Lace lingerie amplifies gain

- **WHEN** a participant with an unamplified product of 40 wears 誘蠱蕾絲內衣
  (`pleasure_gain` +15%)
- **THEN** the gain is `round(40 × 1.15)` = 46

#### Scenario: Silk collar amplifies further

- **WHEN** the same participant instead wears 迷情絲頸環 (+25%)
- **THEN** the gain is 50

#### Scenario: Negative percent floors at zero, never below

- **WHEN** a hypothetical `pleasure_gain` of −100% applies to any product
- **THEN** the gain is 0 and no negative pleasure is ever added

#### Scenario: Golden numbers survive unchanged

- **WHEN** existing pleasure tests run with no equipment
- **THEN** every previously asserted gain value is unchanged

#### Scenario: Combat evaluator key-set stays combat-only

- **WHEN** any entity's no-create combat bundle is evaluated while
  pleasure-bearing equipment is worn
- **THEN** the bundle contains no `pleasure_gain` key and resist/overwhelm
  consumers behave exactly as before
