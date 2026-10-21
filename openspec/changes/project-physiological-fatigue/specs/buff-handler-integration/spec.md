# Spec Delta

## ADDED Requirements

### Requirement: Physiological fatigue projects one authoritative protected status
Reserve/posture SHALL project mutually exclusive fatigue through existing buff and status registries in the same atomic settlement. Projection SHALL not expire independently, stack stages or alter base stats. Ordinary action queries SHALL treat actual sleep as action-forbidden and keep sleepers targetable.

#### Scenario: Exact combat penalties
- **WHEN** light, moderate and severe fatigue are projected
- **THEN** effective agility changes by -5%, -10%, -20% respectively and accuracy adjustments are flat -5, -10, -20; movement does not apply agility again

#### Scenario: Forced-sleep replacement
- **WHEN** a severe member collapses and later wakes at 20%
- **THEN** forced sleep replaces severe, then moderate replaces forced sleep without overlapping stages

#### Scenario: Expiry and reload
- **WHEN** nominal buff duration passes or the member reloads while forced sleep remains latched
- **THEN** the protected projection and sleep action prohibition remain consistent with stored state

#### Scenario: Failure
- **WHEN** projection fails after a reserve/posture write
- **THEN** all physiology, buff/cache state and enclosing clock or terminal effects roll back together

