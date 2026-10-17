# Spec Delta

## ADDED Requirements

### Requirement: Real party encounter evidence records selected values and bounded outcomes
Whole-party encounter probes SHALL use explicit selected commands and actual resolver/initiative/cost/upkeep rules with real gear/restrictions, simulation markers, seeds0-3 and a 200-round bound. Evidence SHALL separate historical projections from measured initial/selected balance values and report defeats, retreats, losses, all-standing, unfinished, rejections and round medians.

#### Scenario: Initial versus selected balance
- **WHEN** K40, Defend0.35, Dodge25 and initial weapon values are calibrated
- **THEN** the report records whether each initial value was kept or changed and its observed results, without asserting the starting curve alone establishes balance

#### Scenario: No hidden autonomy or reward drift
- **WHEN** party probe allies lack a selected command or a simulated action resolves
- **THEN** missing commands do not auto-attack and simulation prevents ordinary growth/unlock/reward drift

#### Scenario: No false encounter guarantee
- **WHEN** sampled higher-tier outcomes are recorded
- **THEN** retreat is not kill credit and historical/high/calamity limitations remain explicit; mismatched real-kit restrictions block acceptance until diagnosed

